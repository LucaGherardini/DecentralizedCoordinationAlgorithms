import traci
class Listener(traci.StepListener):

    def __init__(self, step_limit, vehicles, settings):
        # When listener is initialized, vehicles have yet been spawned, with one simulation step for each of them
        self.step_count = len(vehicles)
        self.step_limit = step_limit
        self.simulation_status = True
        self.vehicles = vehicles
        self.settings = settings

    # NOTE: step method wants argument 't'
    def step(self, t):
        """
        At each traci.simulationStep() invocation, this method is invoked to execute a routine to check step limit, apply common operations (i.e. rerouting check of vehicles) and specific operations for models (i.e. 'Hurry' changing in 'Emergent Behavior' model.
        """

        self.step_count += 1
        # '>' is needed because step_count doesn't start by 0. If step_limit is lower than vehicles to spawn, step_count is yet greater than step_limit
        if self.step_limit != 0 and self.step_count >= self.step_limit:
            self.simulation_status = False
            return False

        for v in self.vehicles:
            v.reroute()
            v.setLabel()

        # another for-loop is done to allow simultaneous updates (if 'applyContribution' is invoked in the 'hurryDiffusion' loop, a vehicle is updated before providing its original contribute in that time step (making hurry spreading "order dependent")
        '''
        if self.model_chosen == 'EB':
            for v in self.vehicles:
                v.applyContribution()
                log_print('step: vehicle {} invocation of \'applyContribution\', with new hurry of {}'.format(v.getID(), v.getHurry()))
        '''

        # indicate that the step listener should stay active in the next step
        return True

    def getStep(self):
        return self.step_count

    def getSimulationStatus(self):
        return self.simulation_status

class AutonomousListener(Listener):
    def __init__(self, step_limit, vehicles, settings):
        super().__init__(step_limit, vehicles, settings)

    def step(self, t):
        super().step(t)

        for v in self.vehicles:
            v.action()

        return True