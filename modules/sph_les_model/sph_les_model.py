import sys
from pathlib import Path
from yapsy.IPlugin import IPlugin
from rocky20.addins.addin_models import container_model, data_model
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity

NAME = "SPH LES Turbulence Model"

@data_model(icon=None, caption=NAME)
class SPHModelAPIModel:
    les_smagorinsky_constant = Quantity(value=0.2, unit='-', caption='Les Smagorinsky Constant')
    les_distance_factor = Quantity(value=2, unit='-', caption='LES Distance Factor')

@data_model(icon=None, caption=NAME)
class SPHForceModel:
    pass
    
class SPHModelAPISpecs(RockyAddinSpecs):

    name = NAME

    model = SPHModelAPIModel
    sph_force_model = SPHForceModel

    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'sph_les_model')

class SPHAPIPlugin(IPlugin):

    def get_addin_specs(self):
        return SPHModelAPISpecs