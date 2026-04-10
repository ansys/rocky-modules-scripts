import sys
from pathlib import Path

from yapsy.IPlugin import IPlugin

from rocky20.addins.addin_models import data_model, container_model, group, tab
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import List, Quantity, Boolean, String, ROIName, Enum, GeometryName

NAME = 'Compression Motion'

@data_model(icon=None, caption=NAME)
class MotionKernel:
    pass

@data_model(icon=None, caption=NAME)
class MotionModel:
    motion_start_time = Quantity(value=0.0, unit='s', caption='Start time')
    geometry_name = GeometryName(caption='Geometry')
    motion_force_limit = Quantity(value=1.0, unit='N', caption='Force Limit')
    @group("Initial Translational Velocity")
    class MotionType:
        translational_velocity_x = Quantity(value=0, unit='m/s', caption='Velocity-X')
        translational_velocity_y = Quantity(value=0, unit='m/s', caption='Velocity-Y')
        translational_velocity_z = Quantity(value=0, unit='m/s', caption='Velocity-Z')


class MotionModelSpecs(RockyAddinSpecs):
    name = NAME
    model = MotionModel
    geometries_motion = MotionKernel

    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'compression_motion')


class MotionModelPlugin(IPlugin):
    def get_addin_specs(self):
        return MotionModelSpecs