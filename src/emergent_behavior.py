from src.intersectionManager import *
import math

class EmergentBehavior(IntersectionManager):

    # override
    def bidSystem(self, crossroad_stop_list, traffic_stop_list):
        hp = [-1, -1]
        for car in crossroad_stop_list:
            log_print('bidSystem: vehicle {} has an Hurry of {}'.format(car.getID(), car.getHurry()))
            hp = ([car, car.getHurry()] if hp[1] < car.getHurry() else [hp[0], hp[1]])
        log_print('Vehicle {} has the higher hurry ({})'.format(hp[0].getID(), hp[1]))
        return [hp[0]]
