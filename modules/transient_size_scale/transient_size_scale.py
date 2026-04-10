import sys
from pathlib import Path

from rocky20.addins.addin_models import data_model, container_model, group
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity, Boolean, String, List, PointCloudName, ParticleName, MassIncrement, VolumeIncrement, ScalarProperties
from yapsy.IPlugin import IPlugin

NAME = "Transient Size Scale"


@data_model(icon=None, caption=NAME)
class TransientScaleModel:
    pass

@container_model()
class TransientScaleParticleInput:
    mass_increment = MassIncrement
    volume_increment = VolumeIncrement

@container_model()
class TransientScaleParticleGroupProperties:
    scale_final_size_scale = Quantity(value=1.0, unit='-', caption='Final Size Scale')
    scale_total_time = Quantity(value=1.0, unit='s', caption='Total time')

class TransientScaleSpecs(RockyAddinSpecs):
    name = NAME
    model = TransientScaleModel
    particle_input_properties = TransientScaleParticleInput
    particle_group_properties = TransientScaleParticleGroupProperties
    
    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'transient_size_scale')

class TransientScalePlugin(IPlugin):
    def get_addin_specs(self):
        return TransientScaleSpecs