import sys
from pathlib import Path

from rocky20.addins.addin_models import data_model
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity
from yapsy.IPlugin import IPlugin

NAME = "Transient Adhesive Force"


@data_model(icon=None, caption=NAME)
class TransientAdhesiveForceModel:
    pass



@data_model(icon=None, caption=NAME)
class TransientAdhesiveForce:
    adhesive_distance = Quantity(value=0.01, unit="m", caption="Adhesive Distance")
    adhesive_initial_force_fraction = Quantity(value=0.0, unit="-", caption="Initial Force Fraction")
    adhesive_final_force_fraction = Quantity(value=1.0, unit="-", caption="Final Force Fraction")
    adhesive_time_coefficient = Quantity(value=0.5, unit="1/s", caption="Time Coefficient")
    adhesion_start_time = Quantity(value=0.0, unit='s', caption='Start Time')



class TransientAdhesiveForceSpecs(RockyAddinSpecs):
    name = NAME
    model = TransientAdhesiveForce
    adhesion_model = TransientAdhesiveForceModel
 
    
    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'transient_adhesive_force')

class TransientAdhesiveForcePlugin(IPlugin):
    def get_addin_specs(self):
        return TransientAdhesiveForceSpecs