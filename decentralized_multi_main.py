from datetime import datetime
import yaml 
import multiprocessing
from utils import *
from listeners import *

def run(settings, model_chosen, chunk_name=0, sumoBinary="/usr/bin/sumo-gui"):
    sumoCmd = [sumoBinary, "-c", "sumo_cfg/project.sumocfg", "--threads", "8"]

    """
        Simulation runs
    """
    try:
        traci.start(sumoCmd)

        crossroads_names = retrieveCrossroadsNames()
        crossroads, edges, in_edges = infrastructureRetrieving(crossroads_names)

        # Vehicles are created all at once, then loaded into "vehicles" list of 'Vehicle' class instances
        vehicles = spawnCars(settings['VS'], settings)

        # Add a StepListener to increment step counter at each call of traci.simulationStep()
        listener = AutonomousListener(settings['Stp'], vehicles, settings)
        traci.addStepListener(listener)

        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file_initialization(chunk_name, settings, model_chosen, listener, time)
        log_print("Simulation starts")

        '''
        if model_chosen == 'Coop':
            model = Cooperative(settings, vehicles)
        elif model_chosen == 'Comp':
            model = Competitive(settings, vehicles)
        '''

        while True:
            dc = {}
            idle_times = {}

            # TODO: now write a second listener class that iterates on all vehicles to perform choices independently
            '''
            for crossroad in crossroads.keys():
                log_print('Handling crossroad {}'.format(crossroad))
                dc[crossroad], idle_times[crossroad] = model.intersectionControl(crossroads[crossroad], listener)
                if not listener.getSimulationStatus():
                    break
            '''

            departCars(settings, dc, idle_times, listener)

            if not listener.getSimulationStatus():
                log_print('Simulation finished')
                print("Simulation finished!")

                traci.close()
                break

    except traci.exceptions.FatalTraCIError:
        log_print('Simulation interrupted')
        print("Simulation interrupted")
    
    return vehicles, crossroads_names, time
