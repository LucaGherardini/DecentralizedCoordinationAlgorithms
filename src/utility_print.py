'''
Print utility
'''

# Color ASCII used to change color of prints
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'  # Red
ENDC = '\033[0m'  # De-select the current color
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

def log_file_initialization(chunk_name, settings, model_chosen, listener, time):
    """
        A globally accessible log file is created to record details of simulation
        :param chunk_name: if 'main.py' is called from outside ('main_multi') the an identifier is used to distinct log files, otherwise, it's omitted
    """
    global log_file
    global l
    l = listener
    file_name = f'logs/{chunk_name if chunk_name>0 else ""}[' + time + ']' + model_chosen

    for s in settings.keys():
        file_name += '_' + s + ':' + str(settings[s])
    log_file = open(file_name + '.txt', "w")

    for s in settings.keys():
        log_file.write("{}: {}\n".format(s, settings[s]))
    log_file.write('\n')
    print(OKGREEN + 'Log file will be written in \'{}\''.format(file_name) + ENDC)


def log_print(text):
    """
        Calling this function allows to write inside the log file created
    """
    global log_file
    log_file.write("{}\t{}\n".format(l.getStep(), text))