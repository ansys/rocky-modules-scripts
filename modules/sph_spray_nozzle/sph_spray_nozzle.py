import sys
from pathlib import Path

from yapsy.IPlugin import IPlugin
from rocky20.addins.addin_models import data_model
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import List, Quantity, ROIName

NAME = 'SPH Spray Nozzle'

@data_model(caption='ListItem')
class RoiListSpec:
    roi_name = ROIName(caption='Regions of Interest')
    reference_point_x = Quantity(value=0.0, unit='m', caption="Reference Point : X")
    reference_point_y = Quantity(value=0.0, unit='m', caption="Reference Point : Y")
    reference_point_z = Quantity(value=0.0, unit='m', caption="Reference Point : Z")

@data_model(icon=None, caption=NAME)
class SPHSprayNozzleModel:

    spray_start_time = Quantity(value=0.0, unit='s', caption='Spray Start Time')
    active_regions = List(item_class=RoiListSpec, caption='Active Regions')
    
class SPHModelAPISpecs(RockyAddinSpecs):

    name = NAME

    model = SPHSprayNozzleModel

    is_beta = True

    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'sph_spray_nozzle')
    
class SPHAPIPlugin(IPlugin):

    def get_addin_specs(self):
        return SPHModelAPISpecs