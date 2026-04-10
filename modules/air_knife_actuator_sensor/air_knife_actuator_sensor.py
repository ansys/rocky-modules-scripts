from yapsy.IPlugin import IPlugin

from rocky20.addins.addin_models import data_model, container_model, group
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity, PointCloudName, ROIName, Boolean, List

NAME = 'Air Knife Actuator Sensor'

@data_model(caption='ListItem')
class SensorListSpec:
    roi_name = ROIName(caption='Region of interest')
    point_cloud = PointCloudName(caption='Point Cloud')

@data_model(icon=None, caption=NAME)
class Model:
    @group("Fluid Material")
    class FluidMaterial:
        fluid_density   = Quantity(value=1.225, unit='kg/m3', caption='Fluid Density')
        fluid_viscosity = Quantity(value=1.7894e-5, unit='Pa.s', caption='Fluid Dynamic Viscosity')
    @group("Actuator")
    class ActuatorTime:
        activate_total_time = Quantity(value=0.0, unit='s', caption='Activate total time')
        activate_delay_time = Quantity(value=0.0, unit='s', caption='Activate delay time')
        factor = Quantity(value=1.0, unit='-', caption='Drag Multiplier')
        distance_multiplier = Quantity(value=1.0, unit='-', caption='Distance Multiplier')
    sensor_pointcloud_list = List(item_class=SensorListSpec, caption='Sensor-Point Cloud Connection')

@container_model()
class ParticleGroupProperties:
    activate_sensor = Boolean(value=False, caption='Activate Sensor')

class Specs(RockyAddinSpecs):
    name = NAME
    model = Model
    particle_group_properties = ParticleGroupProperties

    @classmethod
    def CreateAddin(cls):
        from pathlib import Path

        return cls.CreateDynamicAddin(Path(__file__).parent, 'air_knife_actuator_sensor')


class Plugin(IPlugin):

    def get_addin_specs(self):
        return Specs
