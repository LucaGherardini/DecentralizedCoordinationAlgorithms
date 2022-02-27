# Vehicles coordination algorithms
# Centralized Auction 

from cooperative import *
from competitive import *
from datetime import datetime
from utils import *
from listeners import *
import multiprocessing

# Vehicles coordination algorithms

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
        listener = Listener(settings['Stp'], vehicles, settings)
        traci.addStepListener(listener)

        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file_initialization(chunk_name, settings, model_chosen, listener, time)
        log_print("Simulation starts")

        if model_chosen == 'Coop':
            model = Cooperative(settings, vehicles)
        elif model_chosen == 'Comp':
            model = Competitive(settings, vehicles)

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

def sim(configs, chunk_name, q):
    vehicles, crossroads_names, time = run(configs, configs['model'], chunk_name, sumoBinary="/usr/bin/sumo")
    cross_total, traffic_total, df_waiting_times, crossroads_wt, traffic_wt, crossroad_vehicles, traffic_vehicles = collectWT(vehicles, crossroads_names)
    
    file_name = '[' + time + ']' + configs['model']
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
    print(OKGREEN + 'Raw data written in data/[{}]{}|*.txt'.format(time, configs['model']) + ENDC)

    # Plots are of the last run finishing
    plot(crossroads_wt, 'Crossroads', 'Average crossroad waiting time for each crossroad', file_name.format('crossroads') + '.png')
    plot(traffic_wt, 'Crossroads', 'Average traffic waiting time for each crossroad', file_name.format('traffic') + '.png')
    plot(crossroad_vehicles, 'Cars', 'Average crossroad waiting time of each car', file_name.format('crossroad-vehicles') + '.png')
    plot(traffic_vehicles, 'Cars', 'Average traffic waiting time of each car', file_name.format('traffic-vehicles') + '.png')

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
        configs = manual_config(['Coop', 'Comp'])

    counter = 0
    q = multiprocessing.Queue()
    for settings in configs:
        all_times = pd.DataFrame(columns=['cwt', 'twt']) 

        file_name = '[' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ']' + settings['model']
        for s in settings.keys():
            file_name += '_' + s + ':' + str(settings[s])

        file_name += '|{}'

        cwt_file = open('data/' + file_name.format('cross-total') + '.txt', 'a')    
        twt_file = open('data/' + file_name.format('traffic-total') + '.txt', 'a')
        
        processes = []

        chunk_name = 1
        for i in range(int(settings["RUNS"])):
            p =multiprocessing.Process(target=sim, args=(settings, chunk_name, q))
            processes.append(p)
            p.start()
            chunk_name += 1

        for p in processes:
            p.join()

        # Note that you have to call Queue.get() for each item you want to return.
        while not q.empty():
            cwt = q.get()
            twt = q.get()
            cwt_file.write(str(cwt)+'\n')
            twt_file.write(str(twt)+'\n')
        cwt_file.close()
        twt_file.close()

        counter += 1
        print(f"Chunk {counter}/{len(configs)} finished")

    print("All done")