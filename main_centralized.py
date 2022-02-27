'''
OLD SCRIPT TO BE DELETED
'''
from cooperative import *
from competitive import *
from datetime import datetime
from utils import *
from listeners import *

def run(settings, model_chosen, chunk_name=0, sumoBinary="/usr/bin/sumo-gui"):
    sumoCmd = [sumoBinary, "-c", "project.sumocfg", "--threads", "8"]

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
        listener = Listener(settings['Stp'], vehicles, model_chosen, settings)
        traci.addStepListener(listener)

        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file_initialization(chunk_name, settings, model_chosen, listener, time)
        log_print("Simulation starts")

        if model_chosen == 'Coop':
            model = Cooperative(settings, vehicles)
        elif model_chosen == 'Comp':
            model = Competitive(settings, vehicles)
        elif model_chosen == 'EB':
            model = EmergentBehavior(settings, vehicles)

        while True:
            # This method manage crossroads on the map
            dc = {}
            idle_times = {}
            for crossroad in crossroads.keys():
                log_print('Handling crossroad {}'.format(crossroad))
                dc[crossroad], idle_times[crossroad] = model.intersectionControl(crossroads[crossroad], listener)
                if not listener.getSimulationStatus():
                    break

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

if __name__ == '__main__':
    models = ['Coop', 'Comp', 'EB']
    model_chosen = modelSelection(models)
    settings = simulationSettings(model_chosen)
    vehicles, crossroads_names, time = run(settings, model_chosen)
    """
        Collecting Waiting Times
    """

    file_name = '[' + time + ']' + model_chosen
    for s in settings.keys():
        file_name += '_' + s + ':' + str(settings[s])

    file_name += '|{}'

    cross_total, traffic_total, df_waiting_times, crossroads, traffic, crossroad_vehicles, traffic_vehicles = collectWT(vehicles, crossroads_names)

    data_file = 'data/' + file_name
    df_waiting_times.to_csv(data_file.format('global') + '.txt', index_label=False, index=False)
    cross_total.to_csv(data_file.format('cross-total') + '.txt', index_label=False)
    traffic_total.to_csv(data_file.format('traffic-total') + '.txt', index_label=False)
    crossroads.to_csv(data_file.format('crossroads') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    traffic.to_csv(data_file.format('traffic') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    crossroad_vehicles.to_csv(data_file.format('crossroad-vehicles') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    traffic_vehicles.to_csv(data_file.format('traffic-vehicles') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    print(OKGREEN + 'Raw data written in data/[{}]{}|*.txt'.format(time, model_chosen) + ENDC)

    # total are plot in 'modelComparator.py'
    plot(crossroads, 'Crossroads', 'Average crossroad waiting time for each crossroad', file_name.format('crossroads') + '.png')
    plot(traffic, 'Crossroads', 'Average traffic waiting time for each crossroad', file_name.format('traffic') + '.png')
    plot(crossroad_vehicles, 'Cars', 'Average crossroad waiting time of each car', file_name.format('crossroad-vehicles') + '.png')
    plot(traffic_vehicles, 'Cars', 'Average traffic waiting time of each car', file_name.format('traffic-vehicles') + '.png')