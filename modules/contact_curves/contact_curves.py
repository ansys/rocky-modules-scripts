import sys
from pathlib import Path
from yapsy.IPlugin import IPlugin
from rocky20.addins.addin_models import data_model
from rocky20.addins.addin_specs import RockyAddinSpecs

NAME = 'Contact Curves'

@data_model(icon=None, caption=NAME)
class Model:
    pass

class Specs(RockyAddinSpecs):
    name = NAME
    model = Model

    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'contact_curves')

class Plugin(IPlugin):
    def get_addin_specs(self):
        return Specs
