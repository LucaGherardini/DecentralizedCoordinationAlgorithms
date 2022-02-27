from utils import *
from vehicleAbstract import *

class VehicleAuction(VehicleAbstract):

    def __init__(self, id, settings, budget=100):
        super().__init__(id, settings)
        self.budget = int(budget)
        self.crossroad_counter = self.countCrossroads()

    def setLabel(self):
        """
        'State' parameter of traci vehicle is used to label graphically them in the GUI with a custom value
        """
        traci.vehicle.setParameter(self.id, 'State', self.budget)
        return

    def reroute(self):
        super().reroute()
        self.setBudget(100)
        return

    def makeBid(self):
        """
        dependently on given bidding policy, returns a random bid or a thoughtful bid partitioned for the crossroads to pass
        :return:
        bid, made from the vehicle for its auction
        """
        if self.settings['Bdn'] == 'b':
            return self.getBudget()/self.crossroad_counter
        else:
            return randint(0, int(self.getBudget()))

    def setBudget(self, budget):
        if budget > 0:
            self.budget = int(budget)

    def getBudget(self):
        return self.budget