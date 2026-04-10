from pathlib import Path
from yapsy.IPlugin import IPlugin
from rocky20.addins.addin_models import container_model, data_model, group
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity, GeometryName, Enum

NAME = 'Motion Frame'

@data_model(icon=None, caption=NAME)
class MotionKernel:
    pass

@data_model(icon=None, caption=NAME)
class MotionFrameModel:
    geometry_name = GeometryName(caption='Geometry Name')
    motion_type = Enum(options=[('Translation', 0), ('Rotation', 1)], caption='Motion Type', value=0)

    @group("Translation Velocities")
    class TranslationalVelocities:
        translational_velocity_x = Quantity(value=0, unit='m/s', caption='Translational X-Velocity')
        translational_velocity_y = Quantity(value=0, unit='m/s', caption='Translational Y-Velocity')
        translational_velocity_z = Quantity(value=0, unit='m/s', caption='Translational Z-Velocity')
    
    @group("Rotation Velocities")
    class RotationalVelocities:
        rotational_velocity_x = Quantity(value=0, unit='dega/s', caption='Rotational X-Velocity')
        rotational_velocity_y = Quantity(value=0, unit='dega/s', caption='Rotational Y-Velocity')
        rotational_velocity_z = Quantity(value=0, unit='dega/s', caption='Rotational Z-Velocity')

class MotionFrameSpecs(RockyAddinSpecs):
    name = NAME
    model = MotionFrameModel
    geometries_motion = MotionKernel
    
    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'motion_frame')

class MotionFrameModule(IPlugin):
    def get_addin_specs(self):
        return MotionFrameSpecs
