from src.utils import *
from src.vehicleAbstract import *
from src.vehicleAuction import VehicleAuction
from src.vehicleAutonomous import VehicleAutonomous
from src.crossroadsDict import CrossroadsDict

class VehicleDA(VehicleAuction, VehicleAutonomous):
    currentBid = 0
    priority = -1
    contenders = []

    def __init__(self, id, settings):
        super().__init__(id, settings)
        traci.vehicle.setParameter(self.id, 'State', self.budget)

    def action(self):
        '''
        Here the decentralized vehicle should look for other cars going to its same crossroad, making bids, choosing a leader for the auction, ...
        '''
        self.setLabel()
        if self.currentBid == 0:
            self.currentBid = self.makeBid()
            traci.vehicle.setParameter(self.getID(), 'currentBid', self.currentBid)

        if traci.vehicle.isStopped(self.getID()):
            target_cr = traci.vehicle.getRoadID(self.getID()).split('-')[-1] # The last letter is the target crossroad (i.e. A)
            self.getTimePassedInTraffic(target_cr)
            self.setCrossroadWaitingTime()
            self.setBudget(self.getBudget() - self.currentBid)
            self.setLabel()
            self.cross(target_cr)
        elif traci.vehicle.getSpeed(self.getID()) < traci.vehicle.getAllowedSpeed(self.getID()) * 0.1:
            self.setTrafficWaitingTime()
        return

    def cross(self, target_cr):
        re_crossroads = re.compile(rf"edge.*-{target_cr}")
        if self.priority < 0:
            self.priority = 0
            for c in CrossroadsDict.getGlobalInEdges():
                if re.match(re_crossroads, c):
                    for v in traci.edge.getLastStepVehicleIDs(c):
                        if traci.vehicle.isStopped(v):
                            self.contenders.append(v)
                            if float(traci.vehicle.getParameter(v, 'currentBid')) > self.currentBid:
                                self.priority += 1 # you lost the comparison, your crossing is postponed
                                continue # (with the next edge)
        
            # This condition is met if you haven't encountered any vehicle with higher bid
            if self.priority < 0:
                self.resetCrossroadWaitingTime()

        elif self.priority == 0:
            if len(self.contenders) > 0:
                split_bid = int(self.currentBid/len(self.contenders))
                for c in self.contenders:
                    budget = int(traci.vehicle.getParameter(c, 'State'))
                    traci.vehicle.setParameter(c, 'State', str(budget+split_bid))
                traci.vehicle.resume(self.getID())
                self.getTimePassedAtCrossroad(target_cr)
                self.currentBid = 0
                self.priority = -1
        else:
            self.priority -= 1

        # if the loop has been broken, it means you lost the comparison and you need to wait
        return
    
    def setLabel(self):
        """
        'State' parameter of traci vehicle is used to label graphically them in the GUI with a custom value
        """
        self.budget = int(traci.vehicle.getParameter(self.id, 'State'))
        return