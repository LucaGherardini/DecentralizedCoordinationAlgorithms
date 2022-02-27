from intersectionManager import *
import math

class Cooperative(IntersectionManager):

    # override
    def bidSystem(self, crossroad_stop_list, traffic_stop_list):
        bids = []

        for car in crossroad_stop_list:
            car_bid = int(car.makeBid() + 1)
            log_print('bidSystem: vehicle {} made a bid of {}'.format(car.getID(), car_bid))
            if self.settings['E'] == 'y':
                enhance = math.log(len(traffic_stop_list[car.getRoadID()]) + 1) + 1
                log_print('bidSystem: enhancement applied on vehicle {} is {}'.format(car.getID(), enhance))
            else:
                enhance = 1

            total_bid = int(car_bid * enhance)
            bids.append([car, total_bid, car_bid, enhance])
            log_print('bidSystem: vehicle {} has a total bid of {} (bid {}, enhancement {})'.format(car.getID(), total_bid, car_bid, enhance))

        bids, winner, winner_total_bid, winner_bid, winner_enhance = self.sortBids(bids)

        log_print('bidSystem: vehicle {} pays {}'.format(winner.getID(), winner_bid - 1))
        winner.setBudget(winner.getBudget() - winner_bid + 1)
        self.bidPayment(bids, winner_bid)

        departing = []
        for b in bids:
            departing.append(b[0])

        return departing
