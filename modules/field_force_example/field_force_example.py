from yapsy.IPlugin import IPlugin

from rocky20.addins.addin_models import container_model, data_model
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import String

NAME = 'Field Force'


@data_model(icon=None, caption=NAME)
class Model:
    point_cloud = String(value='', caption='Field Force')


class Specs(RockyAddinSpecs):

    name = NAME

    model = Model

    @classmethod
    def CreateAddin(cls):
        from pathlib import Path

        return cls.CreateDynamicAddin(Path(__file__).parent, 'field_force_example')


class Plugin(IPlugin):

    def get_addin_specs(self):
        return Specs
