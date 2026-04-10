'''
Warning: Changes in this file may not be correctly interpreted later on in the script engine.

Generated script file.

Name for generated for script: Set up a Basic SPH Project

Script description: Script to setup a base SPH case.

@author: Ansys
@script_id:script_setup_up_basic_sph_project
@version: 1.0.0

'''
from pathlib import Path
from enum import Enum


SCRIPTS_OUTPUT_DIR = "Scripts Output"
PROJECT_FILENAME = "case_name.rocky"


class SimulationTarget(Enum):
    CPU = 'CPU'


class PeriodicDirection(Enum):
    X = 'X'


# Creating a new project and saving it on the Scripts Output folder
if sys.platform.startswith("win"):
    out_dir = Path(os.environ["USERPROFILE"]) / "Documents" / "Rocky" / SCRIPTS_OUTPUT_DIR
else:
    out_dir = Path.home() / ".Rocky" / SCRIPTS_OUTPUT_DIR

out_dir.mkdir(parents=True, exist_ok=True)

project = app.CreateProject()
project.SaveProject(str(out_dir / PROJECT_FILENAME))

# Describing the study
study = project.GetStudy()
study.SetName('My Simulation')
study.SetDescription('My SPH Simulation')
study.SetCustomerName('My Customer')

# Setting the physics
physics = study.GetPhysics()
physics.SetEnableThermalModel(True)
physics.SetGravityStartTime(0, 's')
physics.SetGravityStopTime(1000, 's')
physics.SetGravityXDirection(0)
physics.SetGravityYDirection(-9.81, 'm/s2')
physics.SetGravityZDirection(0)

# Setting materials
material_collection = study.GetMaterialCollection()
material = material_collection.AddFluidMaterial()
material.SetName('My Fluid')
material.SetDensity(1000, "kg/m3")
material.SetViscosity(0.001, "Pa.s")
material.SetSpecificHeat(10, 'J/kg.K')
material.SetThermalConductivity(100.0, 'W/m.K')

script_dir = Path(__file__).resolve().parent

# assets/tray.stl inside the same folder as the script
geometry_path = script_dir / "assets" / "tray.stl"

assert geometry_path.exists(), (
    f"The script expects this file to exist at: {geometry_path}"
)

import_geometry = study.ImportWall(
    str(geometry_path), import_scale=0.5, convert_yz=False, custom_name_prefix=None
)

custom_geometry = import_geometry[0]
custom_geometry.SetBoundaryMass(100, 'kg')
custom_geometry.SetTranslation([1.5,-2,0])
custom_geometry.SetMaterial("Default Boundary")
custom_geometry.SetName("my tray")
custom_geometry.SetThermalBoundaryConditionType('prescribed_temperature')
custom_geometry.SetTemperature(20, 'degC')

# Creating and assigning a motion frame
motions_collection = study.GetMotionFrameSource()
motion = motions_collection.NewFrame()
motion.SetName("My frame motion")
motion.SetRelativePosition([1.5, -3.8, 0], 'm')
motion.AddRotationMotion(
    start_time=(0.0, u's'),
    stop_time=(1000.0, u's'),
    angular_velocity=((0.0, 0.5, 0.0), u'rad/s'),
    angular_acceleration=((0.0, 0.0, 0.0), u'rad/s2'),
)  
geometry_to_assign = study.GetGeometry('my tray')
motion.ApplyTo(geometry_to_assign)

# Setting the SPH Settings
sph_settings = study.GetSphSettings()
sph_settings.SetEnabled(True)
sph_settings.SetFluidMaterial('My Fluid')

# Setting the inlet
injecting_surface = study.CreateRectangularSurface()
injecting_surface.SetName("My Inlet")
injecting_surface.SetCenter((1.5, 0 - 2, 0), 'm')
injecting_surface.SetLength(0.75, 'm')
injecting_surface.SetWidth(0.75, 'm')
injecting_surface.SetOrientationFromAngles((0, 0, 0))

# Fluid inlet.
inlets = study.GetInletsOutletsCollection()
inlet_1 = inlets.AddFluidInlet()
inlet_1.SetName('My Fluid Inlet')
inlet_1.SetEntryPoint('My Inlet')
inlet_1.SetStopTime(10.0, 's')
inlet_1.SetBoundaryCondition('velocity')
inlet_1.SetVelocity(1.0, 'm/s')
inlet_1.SetTemperature(150, 'degC')

# Domain Settings.
domain_settings = study.GetDomainSettings()
domain_settings.SetUseBoundaryLimits(False)
domain_settings.SetCoordinateLimitsMinValues([0, -5, -3], 'm')
domain_settings.SetCoordinateLimitsMaxValues([10, 2, 3], 'm')
domain_settings.SetCartesianPeriodicDirections(PeriodicDirection.X.value)
domain_settings.SetPeriodicAtGeometryLimits(True)

# Solver.
solver = study.GetSimulatorRun()
solver.SetSimulationDuration(1, 's')
solver.SetTimeInterval(0.25, 's')
solver.SetUseCompressedFiles(True)
solver.SetSimulationTarget(SimulationTarget.CPU.value)
solver.SetNumberOfProcessors(2)

# save the project and run the simulation
project.SaveProject()
study.StartSimulation(skip_summary=True, delete_results=True)
