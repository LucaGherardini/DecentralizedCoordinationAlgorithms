from src.utils import *
from operator import itemgetter

from src.vehiclesDict import VehiclesDict

class IntersectionManager:

    def __init__(self, settings):
        self.settings = settings

    def intersectionControl(self, crossroad):
        """
        Method inherited from any class that expands 'IntersectionManager' class.
        Vehicles near the crossroad are collected and stored in two separated lists, one for vehicles participating
        auction, one for the vehicles stationary for traffic conditions.
        A vehicle that is about to participate in an auction has its traffic waiting time collected and stored (if any), then
        it starts clocking time spent for auction. To notice that crossroads are managed sequentially, but idle time is
        set simultaneously with traffic waiting time of vehicles, so there is no need to start it in advance.
        :param crossroad: instance of 'Crossroad' representing the crossroad to be managed
        :param listener: instance of 'StepListener' used to control the simulation status (if step limit is reached)
        :return:
        """

        crossroad_stop_list, traffic_stop_list = self.collectWaitingVehicles(crossroad)

        if len(crossroad_stop_list) >= self.settings['MCA']:
            log_print('intersectionControl: enough cars in crossroad_stop_list, auction starts...')
            assert len(crossroad_stop_list) <= 4

            idle_time = crossroad.getIdleTime()
            for v in crossroad_stop_list:
                log_print('intersectionControl: vehicle {} invocation of \'getTimePassedInTraffic\' at crossroad {} with idle time {}'.format(v.getID(), crossroad.getName(), idle_time))
                v.getTimePassedInTraffic(crossroad.getName(), idle_time)
                log_print('intersectionControl: vehicle {} invocation of \'setCrossroadWaitingTime\''.format(v.getID()))
                v.setCrossroadWaitingTime()

            # bidSystem is declared only in sub-models (to avoid use of this generic model instead of specialized ones).
            departing_cars = self.bidSystem(crossroad_stop_list, traffic_stop_list)
            log_print('intersectionControl: idle_time set at {}'.format(idle_time))
            crossroad.resetIdleTime()
            log_print('intersectionControl: \'resetIdleTime\' invocation for crossroad {}'.format(crossroad.getName()))

            return departing_cars, idle_time

        elif 0 < len(crossroad_stop_list) < self.settings['MCA']:
            crossroad.setIdleTime()
            log_print('intersectionControl: crossroad {} \'setIdleTime\' invocation'.format(crossroad.getName()))
            for c in traffic_stop_list.keys():
                for veh in traffic_stop_list[c]:
                    log_print('intersectionControl: vehicle {} invocation of \'getTimePassedInTraffic\' with time_passed of {}'.format(veh.getID(), veh.getTimePassedInTraffic(crossroad.getName(), crossroad.getIdleTime())))
        elif len(crossroad_stop_list) == 0:
            log_print('intersectionControl: crossroad {} \'resetIdleTime\' invocation'.format(crossroad.getName()))
            crossroad.resetIdleTime()
        return [], 0

    def collectWaitingVehicles(self, crossroad):
        crossroad_stop_list = []
        traffic_stop_list = defaultdict(list)
        for v in VehiclesDict.vd.values():
            road = traci.vehicle.getRoadID(v.getID())
            if traci.vehicle.isStopped(v.getID()) and road in crossroad.getInEdges():
                log_print('collectWaitingVehicles: vehicle {} (on road {}) is added to {} crossroad stop list'.format(v.getID(), road, crossroad.getName()))
                crossroad_stop_list.append(v)
            # if vehicles is stationary (NOT stopped) and near the considered crossroad, it is considered "in traffic"
            elif traci.vehicle.getSpeed(v.getID()) < traci.vehicle.getAllowedSpeed(v.getID()) and traci.vehicle.getRoadID(v.getID()) in crossroad.getInEdges():
                log_print('collectWaitingVehicles: vehicle {} added to traffic stop list'.format(v.getID()))
                traffic_stop_list[v.getRoadID()].append(v)
                log_print('collectWaitingVehicles: vehicle {} invocation of \'setTrafficWaitingTime\''.format(v.getID()))
                v.setTrafficWaitingTime()
        assert (len(crossroad_stop_list) <= 4)
        return crossroad_stop_list, traffic_stop_list

    def sortBids(self, bids):
        bids = list(reversed(sorted(bids, key=itemgetter(1))))

        winner = bids[0][0]
        winner_total_bid = bids[0][1]
        winner_bid = bids[0][2]
        winner_enhance = bids[0][3]
        log_print('sortBids: winner is vehicle {} with a \'total bid\' of {}'.format(winner.getID(), winner_total_bid))
        return bids, winner, winner_total_bid, winner_bid, winner_enhance

    def bidPayment(self, bids, winner_bid):
        for i in range(1, len(bids)):
            bids[i][0].setBudget(bids[i][0].getBudget() + round(winner_bid / (len(bids) - 1)))
            log_print('bidPayment: vehicle {} receives {} (new budget {})'.format(bids[i][0].getID(), round(winner_bid / (len(bids) - 1)), bids[i][0].getBudget()))

        if self.settings['CP'] == 'avp':
            # range starts from '1' to skip first position (whom is the winner, always charged of its bid)
            for i in range(1, len(bids)):
                # +1 is added to avoid a vehicle to completely exhaust its budget
                bids[i][0].setBudget(bids[i][0].getBudget() - bids[i][1] + 1)
                log_print('bigPayment: vehicle {} pays {} (new budget {})'.format(bids[i][0].getID(), bids[i][1] - 1, bids[i][0].getBudget()))

    def bidSystem(self, crossroad_stop_list, traffic_stop_list):
        pass
