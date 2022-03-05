from src.utils import *
from src.vehicleAutonomous import VehicleAutonomous
from math import *

class VehicleEB(VehicleAutonomous):

    def __init__(self, id, settings) -> None:
        super().__init__(self, id, settings)
        self.hurry = 0
        self.hurry_contribution = 0

    def action(self):
        '''
        Here, the EB vehicle should invoke changeHurry, spreading its state and comparing its Hurry with those of other vehicles to decide who should pass
        '''
        return 

    def setLabel(self):
        """
        'State' parameter of traci vehicle is used to label graphically them in the GUI with a custom value
        """
        traci.vehicle.setParameter(self.id, 'State', self.hurry)
        return

    def changeHurry(self):
        """
        Hurry is increased for each step in which the vehicle is stationary (speed is 0) and decreased for each step in motion, applying the corresponding function with the given coefficient (increment and decrement are not necessarily symmetric).
        'contribution' stores the step update for the function to be applied
        'function' stores the kind of function to apply
        'polarity' stores the sign of the update (positive if its an increment, negative otherwise)
        :return:
        """
        function = ''
        polarity = 0
        if traci.vehicle.getSpeed(self.id) == 0:
            contribution = self.settings['IC']
            function = 'IF'
            polarity = 1
        else:
            contribution = self.settings['DC']
            function = 'DF'
            polarity = -1

        # if function is 'linear', we've already done
        if self.settings[function] == 'log':
            contribution *= log(self.hurry+2)
        elif self.settings[function] == 'gro':
            contribution = max(contribution * self.hurry/100, contribution)

        contribution = int(contribution * polarity)
        # hurry cannot be negative
        self.hurry = max(self.hurry + contribution, 0)
        return contribution

    def hurrySpreading(self, n, distance):
        """
        Given the neighbor 'n' of current vehicle, in a 'distance' within the specified 'Range', apply the specified 'Spreading' function based on the difference between 'Hurry', restricted dependently by 'Spread Type' ('only-positive' and 'allow-negative').
        Computed 'contribution' is added to 'hurry_contribution', that is a container of the current influences received in that time step, to be applied in 'applyContribution' invocation, at the end of time step routine. Contribution isn't directly applied to allow "symmetric updating" (otherwise, two vehicles with the same 'Hurry' would have different reciprocal contributions dependently to their contribution computation).
        For computing correctly 'contribution', absolute value of 'diff' is considered (log of a negative number doesn't exist) and original sign is stored in 'polarity' parameter (+1 if it is an increment, -1 if it is a decrement).
        :return: 'contribution' computed for the given pair (vehicle, neighbor). It's returned to allow writing in simulation log.
        """
        diff = n.getHurry() - self.hurry

        # if diff is zero, quit now
        if diff == 0:
            return 0
        # if diff is negative, and only positive values are allowed, quit now
        if diff < 0 and self.settings['SP'] == 'op':
            return 0

        if self.settings['SF'] == 'std':
            contribution = diff / (distance * self.settings['DM'])
        elif self.settings['SF'] == 'dbl':
            # copysign is used to apply the original sign of diff to the contribution, otherwise abs(diff) would give only positive values
            contribution = log(abs(diff) + 1) * (distance * self.settings['DM']) * copysign(1, diff)
        elif self.settings['SF'] == 'rbl':
            contribution = log(abs(diff) + 1) * ((self.settings['SR'] * self.settings['DM']) / distance) * copysign(1, diff)

        contribution = int(contribution)
        self.hurry_contribution += contribution

        return contribution

    def applyContribution(self):
        """
        All contributions received in the current time step is applied, ensuring that 'Hurry' won't be negative, and resetting 'hurry_contribution' counter for the next time step
        :return:
        """
        self.hurry = max(self.hurry + self.hurry_contribution, 0)
        self.hurry_contribution = 0

    
    def getHurry(self):
        return self.hurry