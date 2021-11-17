# Vehicles coordination algorithms

from cooperative import *
from competitive import *
from emergent_behavior import *
from datetime import datetime
from utils import *
from listener import *
import yaml
from subprocess import Popen, PIPE, STDOUT
import multiprocessing
import main

def sim(settings, chunk_name, q):
    vehicles, crossroads_names, *_ = main.run(settings, settings['model'], chunk_name, sumoBinary="/usr/bin/sumo")
    cross_total, traffic_total, *_ = collectWT(vehicles, crossroads_names)
    
    q.put(int(cross_total['mean']))
    q.put(int(traffic_total['mean']))

    return

"""
    CONFIGURATION
"""

output = Popen("find configs/ -wholename \'*.yml\'", shell=True, stdout=PIPE)
config_files = str(output.stdout.read()).removeprefix('b\'').removesuffix('\'').removesuffix('\\n').split('\\n')

configs = []
for f in config_files:
    f = f.removeprefix("\"").removeprefix("\'").removesuffix("\"")
    with open(f, "r") as ymlfile:
        configs.append(yaml.load(ymlfile, Loader=yaml.FullLoader))

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
    for i in range(int(settings["RUNS"])):
        cwt = q.get()
        twt = q.get()
        cwt_file.write(str(cwt)+'\n')
        twt_file.write(str(twt)+'\n')
    cwt_file.close()
    twt_file.close()

    counter += 1
    print(f"Chunk {counter}/{len(configs)} finished")

print("All done")