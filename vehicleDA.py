from utils import *
from vehicleAbstract import *
from vehicleAuction import VehicleAuction
from vehicleAutonomous import VehicleAutonomous

class VehicleDA(VehicleAuction, VehicleAutonomous):
    def action(self):
        '''
        Here the decentralized vehicle should look for other cars going to its same crossroad, making bids, choosing a leader for the auction, ...
        '''
        return