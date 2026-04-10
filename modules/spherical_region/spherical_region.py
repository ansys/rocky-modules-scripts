# Import all required libraries
from pathlib import Path
from yapsy.IPlugin import IPlugin
from rocky20.addins.addin_models import container_model, data_model
from rocky20.addins.addin_specs import RockyAddinSpecs
from rocky20.addins.addin_types import Quantity

# Specify module's name
NAME = 'Spherical Region'


# Specify how the following class will be added on Rocky
@data_model(icon=None, caption=NAME)
class SphericalRegionModel:
    """
    Specify the module parameters that will be added to the main module tab.
    """
    # Module parameters
    center_x = Quantity(value=0.0, unit='m', caption='Center Coordinate X')
    center_y = Quantity(value=0.0, unit='m', caption='Center Coordinate Y')
    center_z = Quantity(value=0.0, unit='m', caption='Center Coordinate Z')
    radius = Quantity(value=1.0, unit='m', caption='Sphere Radius')


# Specify the class used to link the previous classes to Rocky
class SphericalRegionSpecs(RockyAddinSpecs):
    """
    Entity responsible to define module specifications.
    """
    # Create a link for the module name
    name = NAME
    
    # Create a link of the module parameters for the main module tab
    model = SphericalRegionModel
    
    # Create a link for Rocky be aware of the module shared library (.DLL, .so)
    @classmethod
    def CreateAddin(cls):
        return cls.CreateDynamicAddin(Path(__file__).parent, 'spherical_region')


# Class used to call the RockyAddinSpecs and load the custom module
class SphericalRegionModule(IPlugin):
    def get_addin_specs(self):
        return SphericalRegionSpecs
