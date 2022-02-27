import abc
from vehicleAbstract import VehicleAbstract
from utils import *

class VehicleAutonomous(VehicleAbstract):
    
    @abc.abstractmethod
    def action(self):
        return