import sys

from utils import *
from random import randint
import math


class Vehicle:

    def __init__(self, id, settings, budget=100):
        self.id = id
        self.settings = settings
        self.route = traci.vehicle.getRoute(id)
        self.budget = int(budget)
        self.hurry = 0
        self.hurry_contribution = 0
        self.position = self.getPosition()

        self.crossroad_counter = self.countCrossroads()
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
            if 'Bdn' in self.settings.keys() and self.settings['Bdn'] == 'b':
                self.setBudget(100)
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
            contribution *= math.log(self.hurry+2)
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

        polarity = math.copysign(1, diff)
        diff = abs(diff)

        if self.settings['SF'] == 'std':
            contribution = diff / (distance * self.settings['DM'])
        elif self.settings['SF'] == 'dbl':
            contribution = math.log(diff + 1) * (distance * self.settings['DM'])
        elif self.settings['SF'] == 'rbl':
            contribution = math.log(diff + 1) * ((self.settings['SR'] * self.settings['DM']) / distance)

        contribution = int(contribution * polarity)
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

    def setLabel(self, model_chosen):
        """
        'State' parameter of traci vehicle is used to label graphically them in the GUI with a custom value, dependently by 'model_chosen'
        """
        if model_chosen == 'EB':
            value = self.hurry
        else:
            value = self.budget

        traci.vehicle.setParameter(self.id, 'State', value)


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

    def makeSponsor(self):
        """
        for 'Competitive' approach, sponsorships consists in a bid participation to help the head of the queue, in order
        to speed traffic flow in that lane
        :return:
        sponsorship randomly picked, according to set sponsorship percentage
        """
        return randint(0, int(self.getBudget() * self.settings['Spn'] * 0.01))

    def getID(self):
        return self.id

    def getRoadID(self):
        return traci.vehicle.getRoadID(self.id)

    def getLaneID(self):
        return traci.vehicle.getLaneID(self.id)

    def getPosition(self):
        return traci.vehicle.getPosition(self.id)

    def setBudget(self, budget):
        if budget > 0:
            self.budget = int(budget)

    def getBudget(self):
        return self.budget

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

    def getTimePassedInTraffic(self, current_crossroad, idle_time):
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
