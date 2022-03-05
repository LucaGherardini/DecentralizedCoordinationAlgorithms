from src.utils import *
from src.vehicleAbstract import *
from src.vehicleAuction import VehicleAuction
from src.vehicleAutonomous import VehicleAutonomous

class VehicleDA(VehicleAuction, VehicleAutonomous):
    def action(self):
        '''
        Here the decentralized vehicle should look for other cars going to its same crossroad, making bids, choosing a leader for the auction, ...
        '''
        return