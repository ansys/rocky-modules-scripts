'''
Warning: Changes in this file may not be correctly interpreted later on in the script engine.

Generated script file.

Name for generated for script: Set up a Basic Rocky Project

Script description: Script to setup a base case.

@author: Ansys
@version: 1.0.0
@script_id:script_setup_up_basic_rocky_project
'''
import os
import sys
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
study.SetDescription('My DEM Simulation')
study.SetCustomerName('My Customer')

# Setting the physics
physics = study.GetPhysics()
physics.SetAdhesionModel('constant')
physics.SetEnableThermalModel(True)
physics.SetGravityStartTime(0, 's')
physics.SetGravityStopTime(1000, 's')
physics.SetGravityXDirection(0)
physics.SetGravityYDirection(-9.81, 'm/s2')
physics.SetGravityZDirection(0)
physics.SetRollingResistanceModel('type_3')
physics.SetNormalForceModel('linear_hysteresis')
physics.SetNumericalSofteningFactor(0.1)
physics.SetRestitutionModel('constant')
physics.SetTangentialForceModel('elastic_coulomb')

# Setting materials
material_collection = study.GetMaterialCollection()
material = material_collection.AddSolidMaterial()
material.SetUseBulkDensity(False)
material.SetName('My Material')
material.SetDensity(1000, "kg/m3")
material.SetPoissonRatio(0.3)
material.SetSpecificHeat(10, 'J/kg.K')
material.SetThermalConductivity(100.0, 'W/m.K')
material.SetYoungsModulus(1e08, 'N/m2')
particle_material = material_collection.GetSolidMaterial('Default Particles')
particle_material.SetCurrentDensity(1500, "kg/m3")

# Setting interactions.
interactions = study.GetMaterialsInteractionCollection()
inter_1 = interactions.GetMaterialsInteraction('Default Particles', 'My Material')
inter_1.SetDynamicFriction(0.5)
inter_1.SetStaticFriction(0.5)
inter_1.SetTangentialStiffnessRatio(0.25)
inter_1.SetAdhesiveFraction(0.5)
inter_1.SetAdhesiveDistance(2.0, 'cm')
inter_1.SetRestitutionCoefficient(0.2)

# Setting the conveyor.
conveyor = study.CreateReceivingConveyor()
conveyor.SetLength(4, 'm')
conveyor.SetBeltWidth(1.5, 'm')
conveyor.SetThermalBoundaryConditionType('prescribed_temperature')
conveyor.SetTemperature(20, 'degC')
conveyor.SetBeltSpeed(2, 'm/s')

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
custom_geometry.SetTranslation([5.7,-2,0])
custom_geometry.SetMaterial("Default Boundary")
custom_geometry.SetName("my tray")
custom_geometry.SetThermalBoundaryConditionType('prescribed_temperature')
custom_geometry.SetTemperature(20, 'degC')

# Creating and assigning a motion frame
motions_collection = study.GetMotionFrameSource()
motion = motions_collection.NewFrame()
motion.SetName("My frame motion")
motion.SetRelativePosition([5.7, -3.8, 0], 'm')
motion.AddRotationMotion(
    start_time=(0.0, u's'),
    stop_time=(1000.0, u's'),
    angular_velocity=((0.0, 0.5, 0.0), u'rad/s'),
    angular_acceleration=((0.0, 0.0, 0.0), u'rad/s2'),
)  
geometry_to_assign = study.GetGeometry('my tray')
motion.ApplyTo(geometry_to_assign)

# Setting the inlet
injecting_surface = study.CreateRectangularSurface()
injecting_surface.SetName("My Inlet")
injecting_surface.SetCenter((1.5, 0 - 2, 0), 'm')
injecting_surface.SetLength(0.75, 'm')
injecting_surface.SetWidth(0.75, 'm')
injecting_surface.SetOrientationFromAngles((0, 0, 0))

# Creating a particle
particle_collection = study.GetParticleCollection()
particle = particle_collection.New()
particle.SetName('My Particle')
particle.SetShape('polyhedron')
particle.SetNumberOfCorners(14)
particle.SetHorizontalAspectRatio(0.5)
particle.SetVerticalAspectRatio(1.5)
particle.SetMaterial('My Material')
particle.SetRollingResistance(0.1)
particle.SetSizeType('equivalent_diameter')
particle.SetEnableRandomAngle(True)
particle.SetRandomAnglesHalfRange([30, 30, 30], 'dega')

# setting the particle size distribution
distribution_list = particle.GetSizeDistributionList()
distribution_list.New()
distribution_list.New()
first = distribution_list[0]
first.SetSize(0.1, 'm')
first.SetCumulativePercentage(100)
second = distribution_list[1]
second.SetSize(0.05, 'm')
second.SetCumulativePercentage(75)
third = distribution_list[2]
third.SetSize(0.025, 'm')
third.SetCumulativePercentage(20)

# Particle inlet.
inputs = study.GetInletsOutletsCollection()
input_1 = inputs.AddParticleInlet()
input_1.SetName('My Particle Inlet')
input_1.SetEntryPoint('My Inlet')
input_1.SetStopTime(10.0, 's')
input_1.SetUseTargetNormalVelocity(True)
input_1.SetTargetNormalVelocity(1.0, 'm/s')

entries = input_1.GetInputPropertiesList()
entry = entries.New()
entry.SetParticle('My Particle')
entry.SetMassFlowRate(10, 'kg/s')
entry.SetTemperature(150, 'degC')

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
