import sys
from pathlib import Path

from yapsy.IPlugin import IPlugin

from rocky20.addins.addin_models import data_model, container_model, group, tab
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import List, Quantity, Boolean, String, ROIName, Enum, GeometryName

NAME = 'Geometry Actuator Sensor'

@data_model(icon=None, caption=NAME)
class MotionKernel:
    pass
    
@container_model()
class ParticleGroupProperties:
    activate_sensor = Boolean(value=False, caption='Activate Sensor')

@data_model(caption='ListItem')
class SensorListSpec:
    roi_name = ROIName(caption='Region of interest')
    geometry_name = GeometryName(caption='Geometry')

@data_model(icon=None, caption=NAME)
class MotionModel:
    @tab("Actuator Parameters")
    class ActuatorParameters:
        @group("Motion Type")
        class MotionType:
            motion_type = Enum(options=[('Translation', 0), ('Rotation', 1)], caption='Motion Type', value=0)
            translational_velocity = Quantity(value=0, unit='m/s', caption='Translational velocity')
            rotation_velocity = Quantity(value=0, unit='dega/s', caption='Rotational velocity')
            @group("Relative Orientation Vector")
            class RelativeOrientationVector:
                relative_orientation_vector_x = Quantity(value=1, unit='-', caption='Unit Vector-X')
                relative_orientation_vector_y = Quantity(value=0, unit='-', caption='Unit Vector-Y')
                relative_orientation_vector_z = Quantity(value=0, unit='-', caption='Unit Vector-Z')
        @group("Actuator Time")
        class ActuatorTime:
            activate_total_time = Quantity(value=0.0, unit='s', caption='Activate total time')
            activate_delay_time = Quantity(value=0.0, unit='s', caption='Activate delay time')

    @tab("Sensor-Geometry Connection")
    class SensorGeometryConnection:
        sensor_geometry_list = List(item_class=SensorListSpec, caption='Sensor-Geometry Connection')


class MotionModelSpecs(RockyAddinSpecs):
    name = NAME
    model = MotionModel
    particle_group_properties = ParticleGroupProperties
    geometries_motion = MotionKernel

    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'geometry_actuator_sensor')


class MotionModelPlugin(IPlugin):
    def get_addin_specs(self):
        return MotionModelSpecs