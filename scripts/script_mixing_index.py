'''
Name for generated for script: 
    Compute Mixing Index

Script description: 
    Calculates the Mixing Index for multi-particle systems using cell-wise mass ratios and averaging.

Warning: 
    Changes in this file may not be correctly interpreted later on in the macro engine.

@author: Ansys
@script_id:script_compute_mixing_index
@date: 2025-09
@version: 1.0.0

'''

import numpy as np
import os
from enum import Enum

NO_GUI = os.environ.get("ROCKY_SCRIPTS_AUTOFILL", "0") == "1"

# Change only these lines
# -----------------------------

GEOMETRY_NAME = "mixer"
PROPERTY_FILTER_NAME = "pf_compute_mixing_index"
CUBE_PROCESS_NAME = "cube_compute_mixing_index"
EULERIAN_STATS_NAME = "es_compute_mixing_index"
BIN_SCALE_FACTOR = 2.0


class FilterType(Enum):
    RANGE = "Range"
    VALUE = "Value"

# -----------------------------

project = app.GetProject()
study = app.GetStudy()

# Let the user pick the mixer geometry when a GUI is available.
selected_geometry_name = GEOMETRY_NAME

if not NO_GUI:
    try:
        from PyQt6 import QtWidgets
        geometry_collection = study.GetGeometryCollection()
        geometry_names = geometry_collection.GetGeometryNames()
        if geometry_names:
            qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            item, ok = QtWidgets.QInputDialog.getItem(
                None, "Select Mixer Geometry", "Available geometries:",
                geometry_names, 0, False
            )
            if ok and item:
                selected_geometry_name = item
    except Exception:
        selected_geometry_name = GEOMETRY_NAME


# First thing is to check whether the selected geometry exists
try:
    mixer_geometry = study.GetGeometryCollection().GetGeometry(selected_geometry_name)
except:
    msg = f"A geometry named \"{selected_geometry_name}\" was not found! Please select a valid geometry in the dialog or change the GEOMETRY_NAME parameter in the script source code."
    raise NameError(msg)

# Checking available particle groups
# We do it at the latest output in case there are continuous injections
particles = study.GetParticles()
prt_group = particles.GetGridFunction("Particle Group").GetArray(time_step=-1)
available_prt_groups, inverse_indices = np.unique(prt_group, return_inverse=True)

indexes_dict = {val: np.where(inverse_indices == idx)[0] for idx, val in enumerate(available_prt_groups)}

# Evaluate the mass of each particle group
prt_mass = particles.GetGridFunction("Particle Mass").GetArray(time_step=-1)
prt_group_mass = [prt_mass[indexes].sum() for _,indexes in indexes_dict.items()]

prt_target_ratio = [i / np.sum(np.array(prt_group_mass)) for i in prt_group_mass]
prt_group_factor = np.array([np.max(np.array(prt_target_ratio)) / i for i in prt_target_ratio])

# Computing domain dimensions from mixer geometry
bounding_box = mixer_geometry.GetBoundingBox()
cube_center = np.average(bounding_box, axis=0).reshape(-1,)
cube_size = np.diff(bounding_box, axis=0).reshape(-1,)

# Computing the relative mass ratio
user_process_collection = project.GetUserProcessCollection()
user_process_names = user_process_collection.GetProcessNames()

property_filter = user_process_collection.CreatePropertyProcess(particles) if PROPERTY_FILTER_NAME not in user_process_names else user_process_collection.GetProcess(PROPERTY_FILTER_NAME)
property_filter.SetName(PROPERTY_FILTER_NAME)

# Cube process
# It is only created or modified if not found among the available user processes.
# This gives the user the ability to change the cube dimensions
if CUBE_PROCESS_NAME not in user_process_names:
    cube_process = user_process_collection.CreateCubeProcess(property_filter) 
    cube_process.SetName(CUBE_PROCESS_NAME)
    cube_process.SetCenter(*cube_center)
    cube_process.SetSize(*cube_size)
else: 
    cube_process = user_process_collection.GetProcess(CUBE_PROCESS_NAME)

# Eulerian Statistics
# Number of divisions is computed from 2 x max particle size
if EULERIAN_STATS_NAME not in user_process_names:
    prt_size = particles.GetGridFunction("Particle Size").GetArray(time_step=-1).max()
    eulerian_divisions = tuple(int(i) for i in np.ceil(cube_size / BIN_SCALE_FACTOR / prt_size).reshape(-1,))
    eulerian_statistics_process = user_process_collection.CreateEulerianStatistics(cube_process)
    eulerian_statistics_process.SetName(EULERIAN_STATS_NAME)
    eulerian_statistics_process.SetDivisions(eulerian_divisions)
else:
    eulerian_statistics_process = user_process_collection.GetProcess(EULERIAN_STATS_NAME)

try:
    prt_mass_sum = eulerian_statistics_process.GetGridFunction("Sum of Particle Mass")
except:
    prt_mass_sum = eulerian_statistics_process.CreateEulerianGridFunction(
            "Sum", 
            "Particle Mass"
        )


# Sweeping the timeset and computing the mixing index
timeset = study.GetTimeSet()

for t in timeset:
    # Total mass
    property_filter.SetPropertyGridFunction("Particle Group")
    property_filter.SetType(FilterType.RANGE.value)
    property_filter.SetMinValue(np.min(available_prt_groups))
    property_filter.SetMaxValue(np.max(available_prt_groups))

    total_mass = prt_mass_sum.GetArray(time_step=t)
    valid_indexes = np.where(total_mass > 0.0)

    relative_mass_ratio = np.zeros_like(total_mass)
    relative_mass_ratio = np.tile(relative_mass_ratio, (available_prt_groups.size,1))

    for i, prt_group_id in enumerate(available_prt_groups):
        property_filter.SetType(FilterType.VALUE.value)
        property_filter.SetCutValue(prt_group_id)

        relative_mass_ratio[i][valid_indexes] = prt_mass_sum.GetArray(time_step=t)[valid_indexes] / total_mass[valid_indexes] * prt_group_factor[i]
   
    max_denominator = np.max(relative_mass_ratio, axis=0)
    sum_prob = relative_mass_ratio / max_denominator
    sum_prob = np.nan_to_num(sum_prob, nan=0.0)
    sum_prob = np.sum(sum_prob, axis=0)

    # Computing the Mixing Index
    cell_mi = np.zeros_like(sum_prob)
    valid_indexes = np.where(sum_prob > 0)
    cell_mi[valid_indexes] = 1.0 / (available_prt_groups.size - 1) * (sum_prob[valid_indexes] - 1.0)

    # Adding it as grid function to the Eulerian Stats
    eulerian_statistics_process.AddGridFunction("Cell Mixing Index", cell_mi, unit='-', location='cell', realization='user_generated', time_step=t)

# Adding Volume Fraction property filter
property_filter.SetType(FilterType.RANGE.value)
property_filter.SetMinValue(np.min(available_prt_groups))
property_filter.SetMaxValue(np.max(available_prt_groups))

property_filter_eulerian = user_process_collection.CreatePropertyProcess(eulerian_statistics_process) if "property_vol_fraction" not in user_process_names else user_process_collection.GetProcess("property_vol_fraction")
property_filter_eulerian.SetName("property_vol_fraction")
property_filter_eulerian.SetPropertyGridFunction("Sum of Particle Mass")
property_filter_eulerian.SetType(FilterType.RANGE.value)
property_filter_eulerian.SetMinValue(0.00001)
property_filter_eulerian.SetMaxValue(1000000)

# Display the average mixing index in a timeplot if GUI is enabled
if not NO_GUI:
    window_name = "Average Mixing Index"
    time_plot = app.GetWindow(window_name)
    if time_plot is None:
        time_plot = app.CreateTimePlotWindow(window_name)
        time_plot.ShowGridFunctionStatisticsCurve(
            "property_vol_fraction",
            "Cell Mixing Index (User Generated)",
            "average"
        )

