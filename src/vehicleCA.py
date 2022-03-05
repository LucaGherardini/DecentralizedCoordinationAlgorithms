from src.vehicleAuction import VehicleAuction
from random import randint

class VehicleCA(VehicleAuction):
    def makeSponsor(self):
        """
        for 'Competitive' approach, sponsorships consists in a bid participation to help the head of the queue, in order
        to speed traffic flow in that lane
        :return:
        sponsorship randomly picked, according to set sponsorship percentage
        """
        return randint(0, int(self.getBudget() * self.settings['Spn'] * 0.01))
