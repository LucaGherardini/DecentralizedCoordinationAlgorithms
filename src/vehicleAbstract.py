import abc

from src.utils import *
from random import randint

'''
    Abstract class of a generic vehicle, to be expanded and customized for different models
'''
class VehicleAbstract(abc.ABC):

    def __init__(self, id, settings):
        self.id = id
        self.settings = settings
        self.route = traci.vehicle.getRoute(id)
        self.position = self.getPosition()

        self.waitedTimes = defaultdict(list)

        self.traffic_waited_times = defaultdict(list)
        self.traffic_waiting_time = 0

        self.crossroads_waited_times = defaultdict(list)
        self.crossroad_waiting_time = 0

    def __str__(self):
        return "Car " + self.getID()

    def reroute(self):
        """
        reroute check and eventually reassign route to a vehicle dependently on setting chosen (static or dynamic)
        - With 'static' policy, it simply check rewind route (each default route is circular)
        - With 'dynamic' policy, a route with the same length of the original one is created, picking with regular expression
        (and randomly) edges to form a route
        :return:
        """
        current_edge = self.getRoadID()
        rer = -1
        if current_edge == self.route[rer]:

            if self.settings['Rts'] == 'f':
                self.route = self.route[rer::] + self.route[:rer:]
            else:
                route_length = len(self.route)
                self.route = [current_edge]
                for i in range(rer, route_length - rer):
                    nodes = current_edge[4::]  # remove 'edge' from edgeID
                    nodes = nodes.split('-')  # now two nodes' IDs are in nodes list
                    prev_node = nodes[0]
                    next_node = nodes[1]
                    # Choose an edge suitable for the car (edgexy, edgeyz) but it cannot return in the previous lane (x!=z)
                    next_edge_pattern = r"edge" + next_node + "-([^" + prev_node + "]|(1[^" + prev_node + "]+))$"
                    possible_next_edges = []

                    for e in traci.edge.getIDList():
                        if re.match(next_edge_pattern, e):
                            possible_next_edges.append(e)

                    # A random edge is chosen between the suitable
                    assert (len(possible_next_edges) >= 1)
                    chosen_edge = possible_next_edges[randint(0, len(possible_next_edges) - 1)]
                    self.route.append(chosen_edge)
                    current_edge = chosen_edge

            traci.vehicle.setRoute(self.id, list(self.route))
            # When rerouting I count new crossroads to cross
            self.crossroad_counter = self.countCrossroads()
        return

    def countCrossroads(self):
        """
        analyzes current route of the vehicle, identifying edges leading to crossroads and placing a 'Stop' at its
        end. 'counter' parameter memorizes how many crossroads are in the current route, to allow a far sight policy
        :return:
        counter: amount of crossroads to pass for the given route
        """
        counter = 0
        crossroad_pattern = r"^edge.+[ABCDEFGHI]$"
        for e in self.route:
            if re.match(crossroad_pattern, e):
                counter += 1
                edge_length = traci.lane.getLength(e + "_0")
                traci.vehicle.setStop(self.id, e, float(edge_length), duration=1000000.0)
        return counter
    

    @abc.abstractmethod
    def setLabel(self):
        return

    def getID(self):
        return self.id

    def getRoadID(self):
        return traci.vehicle.getRoadID(self.id)

    def getLaneID(self):
        return traci.vehicle.getLaneID(self.id)

    def getPosition(self):
        return traci.vehicle.getPosition(self.id)

    

    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    CrossroadWaitingTime section
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
    def getTimePassedAtCrossroad(self, current_crossroad, idle_time):
        """
        If 'crossroad_waiting_time' is set (!= 0), then time spent still at the crossroad is memorized in the corresponding
        dict 'crossroads_waited_times', for the given crossroad. 'crossroad_counter' is not decreased to allow homogeneous
        bidding on all the crossroads of the route.
        :param current_crossroad: is the crossroad where the vehicle is currently passing
        :param idle_time: is a fraction of time spent awaiting vehicles to have the auction (excluded from the statistics)
        :return: time passed at the crossroad, 0 if there is not awaiting
        """
        if self.crossroad_waiting_time != 0:
            time_passed = max((traci.simulation.getTime() - self.crossroad_waiting_time - idle_time), 0)
            self.crossroads_waited_times[current_crossroad].append(time_passed)  # memorize in seconds
            # if getTimePassedAtCrossroad is invoked, then a crossroad has been crossed, so crossroad_counter has to be decreased by 1
            #self.crossroad_counter -= 1
            return time_passed
        return 0

    def setCrossroadWaitingTime(self):
        """
        If 'crossroad_waiting_time' timer has not yet been set, it's set with the current time in simulation
        :return:
        """
        if self.crossroad_waiting_time == 0:
            self.crossroad_waiting_time = traci.simulation.getTime()

    def resetCrossroadWaitingTime(self):
        self.crossroad_waiting_time = 0

    def getCrossroadWaitedTimes(self):
        return self.crossroads_waited_times

    """
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    TrafficWaitingTime section
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    """
    def getTimePassedInTraffic(self, current_crossroad, idle_time=0):
        """
        As for 'getTimePassedAtCrossroad', 'idle_time' is removed from statistics
        :param current_crossroad: String containing name of crossroad where vehicles was awaiting
        :param idle_time: time spent awaiting for other vehicles to start auction
        :return:
        """
        if self.traffic_waiting_time != 0:
            time_passed = max((traci.simulation.getTime() - self.traffic_waiting_time - idle_time), 0)
            self.traffic_waiting_time = 0
            # ignore null waiting times, they are not important for statistics (unlike crossroad waiting times)
            if time_passed != 0:
                self.traffic_waited_times[current_crossroad].append(time_passed)

            return time_passed
        return 0

    def setTrafficWaitingTime(self):
        if self.traffic_waiting_time == 0:
            self.traffic_waiting_time = traci.simulation.getTime()

    def getTrafficWaitedTimes(self):
        return self.traffic_waited_times
