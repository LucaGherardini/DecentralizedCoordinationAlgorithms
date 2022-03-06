# Vehicles coordination algorithms

from audioop import cross
from datetime import datetime
import multiprocessing
import math

from src.utility_print import *
from src.cooperative import Cooperative
from src.competitive import Competitive
from src.utils import *
from src.listeners import *

def run(settings, model_chosen, chunk_name=0, time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), sumoBinary="/usr/bin/sumo"):
    sumoCmd = [sumoBinary, "-c", "sumo_cfg/project.sumocfg", "--threads", "8"]

    """
        Simulation runs
    """
    try:
        traci.start(sumoCmd)

        crossroads_names = retrieveCrossroadsNames()
        crossroads, edges, in_edges = infrastructureRetrieving(crossroads_names)

        # Vehicles are created all at once, then loaded into "vehicles" list of 'Vehicle' class instances
        spawnCars(settings['VS'], settings)

        if model_chosen == 'Coop' or model_chosen == 'Comp':
            # Add a StepListener to increment step counter at each call of traci.simulationStep()
            listener = Listener(settings['Stp'], settings)
        else:
            listener = AutonomousListener(settings['Stp'], settings)
        traci.addStepListener(listener)

        log_file_initialization(chunk_name, settings, model_chosen, listener, time)
        log_print("Simulation starts")

        if model_chosen == 'Coop':
            model = Cooperative(settings)
        elif model_chosen == 'Comp':
            model = Competitive(settings)

        # NOTE: EB and DA don't need a dedicated class, the specific vehicles 'are' the classes

        while True:
            if model_chosen == 'EB' or model_chosen == 'DA':
                traci.simulationStep()
            else:
                # This method manage crossroads on the map
                dc = {}
                idle_times = {}
                for crossroad in crossroads.keys():
                    log_print('Handling crossroad {}'.format(crossroad))
                    dc[crossroad], idle_times[crossroad] = model.intersectionControl(crossroads[crossroad])
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
    
    return crossroads_names

def sim(configs, chunk_name=0, time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), sumoBinary="/usr/bin/sumo-gui", lock=None, q=None):
    crossroads_names = run(configs, configs['model'], chunk_name, time, sumoBinary)

    cross_total, traffic_total, df_waiting_times, crossroads_wt, traffic_wt, crossroad_vehicles, traffic_vehicles = collectWT(crossroads_names)
    
    file_name = f'{chunk_name}[' + time + ']' + configs['model']
    for s in configs.keys():
        file_name += '_' + s + ':' + str(configs[s])

    file_name += '|{}'

    data_file = 'data/' + file_name
    df_waiting_times.to_csv(data_file.format('global') + '.txt', index_label=False, index=False)
    cross_total.to_csv(data_file.format('cross-total') + '.txt', index_label=False)
    traffic_total.to_csv(data_file.format('traffic-total') + '.txt', index_label=False)
    crossroads_wt.to_csv(data_file.format('crossroads') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    traffic_wt.to_csv(data_file.format('traffic') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    crossroad_vehicles.to_csv(data_file.format('crossroad-vehicles') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    traffic_vehicles.to_csv(data_file.format('traffic-vehicles') + '.txt', header=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
    print(OKGREEN + f'Raw data written in data/{chunk_name}[{time}]{configs["model"]}|*.txt' + ENDC)

    if chunk_name == 0:
        # NOTE: there is a problem for subsequent processes trying to plot theirs results, they quit from 'sim' and don't put results in queue
        # Plots are of the first run
        plot(crossroads_wt, 'Crossroads', 'Average crossroad waiting time for each crossroad', file_name.format('crossroads') + '.png')
        plot(traffic_wt, 'Crossroads', 'Average traffic waiting time for each crossroad', file_name.format('traffic') + '.png')
        plot(crossroad_vehicles, 'Cars', 'Average crossroad waiting time of each car', file_name.format('crossroad-vehicles') + '.png')
        plot(traffic_vehicles, 'Cars', 'Average traffic waiting time of each car', file_name.format('traffic-vehicles') + '.png')

    '''
    cross_total['mean'] = 0 if math.isnan(cross_total['mean']) else cross_total['mean']
    traffic_total['mean'] = 0 if math.isnan(traffic_total['mean']) else traffic_total['mean']
    '''

    if q is not None:
        q.put(int(cross_total['mean']))
        q.put(int(traffic_total['mean']))

    return

if __name__ == '__main__':
    # models = ['EB', 'DA']
    choice_pt = PrettyTable()
    choice_pt.field_names = ['#', 'Configuration']
    choice_pt.add_row(['1', 'Read configuration files in folder \'configs\' [default]'])
    choice_pt.add_row(['2', 'Insert configuration parameters manually'])
    try:
        print(choice_pt.get_string())
        choice = int(input('Choice: '))
    except Exception as e:
        print(e)
        choice = 1

    if choice == 1:
        configs = read_config()
    else:
        configs = manual_config(['Coop', 'Comp', 'EB', 'DA'])

    sumo = input('Graphical Interface [y/N]: ')
    sumo = 'sumo-gui' if sumo == 'y' or sumo == 'Y' else 'sumo' 

    counter = 0

    q = multiprocessing.Queue()
    lock = multiprocessing.Lock()
    for settings in configs:
            
        processes = []
        time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        for i in range(int(settings["RUNS"])):
            p =multiprocessing.Process(target=sim, args=(settings, i, time, f'/usr/bin/{sumo}', lock, q))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()

        if int(settings['RUNS']) > 1:
            #all_times = pd.DataFrame(columns=['cwt', 'twt']) 
            file_name = f'[MULTIRUN_{time}]' + settings['model']
            for s in settings.keys():
                file_name += '_' + s + ':' + str(settings[s])
            file_name += '|{}'
            cwt_file = open('data/' + file_name.format('cross-total') + '.txt', 'w')    
            twt_file = open('data/' + file_name.format('traffic-total') + '.txt', 'w')
            # Note that you have to call Queue.get() for each item you want to return.
            while not q.empty():
                cwt = q.get()
                twt = q.get()
                cwt_file.write(str(cwt)+'\n')
                twt_file.write(str(twt)+'\n')
            cwt_file.close()
            twt_file.close()
            print(f'Cumulative results of runs saved as {file_name}')
            counter += 1
            print(f"Chunk {counter}/{len(configs)} finished")

    print("All done")