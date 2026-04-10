'''
Warning: Changes in this file may not be correctly interpreted later on in the script engine.

Generated script file.

Name for generated for script: Export Boundary Information
@author: Ansys
@script_id:script_export_boundary_information
@version: 1.4.0
@date: 10 - 2024
'''
from math import cos, sin
import numpy
import time
import os
import sys
from enum import Enum
from PyQt6.QtWidgets import QApplication, QScrollArea, QWidget, QVBoxLayout, QCheckBox, QLabel, QPushButton, QDialog, QComboBox, QMessageBox


AUTOFILL_ENV_VAR = "ROCKY_SCRIPTS_AUTOFILL"
AUTOFILL_ENABLED_VALUE = "1"
GEOMETRY_DATA_FOLDER = "geometry_data"


class GridLocation(Enum):
    CELL = "cell"
    NODE = "node"


def get_project_filename_and_create_folder(project, folder_name):
    # Getting project filename and creating a folder to save files 
    project_filename = project.GetProjectFilename()
    project_path = os.path.dirname(project_filename)
    project_name = os.path.splitext(os.path.basename(project_filename))[0]

    # Base name for the generate file(s)
    base_file_name = project_name

    # Creation of a folder to save the files
    data_folder_path = os.path.join(project_path, str(folder_name))
    if not os.path.exists(data_folder_path):
        os.mkdir(data_folder_path)  
        
    return (base_file_name, data_folder_path)

def write_cell_gf_for_timestep(geometry, cell_grid_functions, case_file, time_step):
    # write the desired grid functions for the given time step in a certain case file,
    # as well as the corresponding triangle center global coordinates
    number_triangles = geometry.GetNumberOfCells(time_step=time_step) 
    position_array = geometry.GetCellCenterAsArray().reshape((number_triangles,3))
    triangles_array = (numpy.arange(number_triangles, dtype=numpy.int32)).reshape((number_triangles,1))
    data_array = numpy.hstack((triangles_array, position_array))
    
    for name in cell_grid_functions:
        gf = geometry.GetGridFunction(name).GetArray(time_step=time_step)
        number_elements = int(len(gf)/number_triangles)
        data_array = numpy.hstack((data_array, gf.reshape((number_triangles, number_elements))))
    
    fmt = r'%d' + (len(cell_grid_functions)+3) * r',%.4e'
    numpy.savetxt(case_file, data_array, fmt=fmt)


def write_node_gf_for_timestep(geometry, nodal_grid_functions, case_file, time_step):
    # write the desired grid functions for the given time step in a certain case file,
    # as well as the corresponding node global coordinates
    number_of_nodes = geometry.GetNumberOfNodes()
    nodes_position = geometry.GetGeometry().GetRawPoints().AsNumPyArray()
    position_array = nodes_position.reshape((number_of_nodes,3))
    nodes_array = (numpy.arange(number_of_nodes, dtype=numpy.int32)).reshape((number_of_nodes,1))
    data_array = numpy.hstack((nodes_array, position_array))
    
    for name in nodal_grid_functions:
        gf = geometry.GetGridFunction(name).GetArray(time_step=time_step)
        number_elements = int(len(gf)/number_of_nodes)
        data_array = numpy.hstack((data_array, gf.reshape((number_of_nodes, number_elements))))
    
    fmt = r'%d' + (len(nodal_grid_functions)+3) * r',%.4e'
    numpy.savetxt(case_file, data_array, fmt=fmt)


st = time.time()


def export_boundary_information():
    def check_project_and_show_error():
        project = api.GetProject()
        if project is None:
            qt_app = QApplication.instance() or QApplication(sys.argv)            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText('<b>Information</b>: There is no project opened. Please open a project before running this script.')
            msg.setWindowTitle('No Project Opened')
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if msg.exec() == QMessageBox.StandardButton.Ok:
                return False
        return True  

    if not check_project_and_show_error():
        return

    # Getting study    
    study = project.GetStudy()
    timeset = study.GetTimeSet()

    def check_results_and_show_error(study):
        if not study.HasResults():
            qt_app = QApplication.instance() or QApplication(sys.argv)            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText('<b>Information</b>: There are no results in this project. Please run the project before exporting boundary information.')
            msg.setWindowTitle('Missing project results')
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if msg.exec() == QMessageBox.StandardButton.Ok:
                return False
        return True  

    if not check_results_and_show_error(study):
        return

    #checking project path and creating a new folder to save files
    folder_name = GEOMETRY_DATA_FOLDER
    base_file_name, data_folder_path = get_project_filename_and_create_folder(project, folder_name)
    
    # getting time array
    time_array = timeset.GetValues()

    # List of geometries
    collection = study.GetGeometryCollection()
    geometry_names = collection.GetGeometryNames()

    # Removing Inlet Processes from geometry list
    geometries = [i for i in geometry_names if collection.GetGeometry(i).GetClassName() != 'InletProcessSubject']

    # Creating a window to ask user the geometry to select
    if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
        selected_geometry_name = geometries[1] if len(geometries) > 1 else geometries[0]
    else:
        ask_geom = [("Geometry", geometries)]
        result_geom = create_scrollable_list(ask_geom, width=400, height=150)
        if result_geom is None:
            print("Script canceled")
            return
        selected_geometry_name = geometries[result_geom[0]]


    selected_geometry = collection.GetGeometry(selected_geometry_name)


    # Getting the selected geometry
    # selected_geometry_name = geometries[result_geom[0]]
    # selected_geometry = collection.GetGeometry(selected_geometry_name)

    # Getting grid functions list
    gflist = selected_geometry.GetGridFunctionNames()

    # Creating a window to ask user which property he wants to export, 
    # for which geometry and at which time range                 
    asklist2 = [("One file per output ?", False), 
                ("Initial time", [f"{t:.2f} s" for t in time_array]),
                ("Final time", [f"{t:.2f} s" for t in time_array])] \
                + [(grid, False) for grid in gflist]

    if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
        # result2 layout: [multiple_files(bool), initial_time_idx, final_time_idx] + one bool per grid function
        # choose: single file, full time range, select all grid functions
        result2 = [False, 0, len(time_array) - 1] + [True] * len(gflist)
    else:
        result2 = create_scrollable_list(asklist2, width=600, height=400)
        if result2 is None:
            print("Script canceled")
            return

    multiple_files = result2[0]
    time_start = result2[1]
    time_stop = result2[2]

    # dealing with the case the user has set final time < initial time
    def check_time_and_show_error(time_start, time_stop):
        # Check if the final time is smaller than the initial time
        if time_start > time_stop:
            qt_app = QApplication.instance() or QApplication(sys.argv)          
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText('<b>Information</b>: Final time is smaller than initial time. Please correct the order.')
            msg.setWindowTitle('Time Selection')
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            if msg.exec() == QMessageBox.StandardButton.Ok:
                return False
        return True  

    if not check_time_and_show_error(time_start, time_stop):
        return

    gf_selected = [i for i, x in enumerate(result2[3:]) if x]
    if not gf_selected:
        qt_app = QApplication.instance() or QApplication(sys.argv)      
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: No property was selected for exporting. Please select at least one property.')
        msg.setWindowTitle('Property Selection')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return

    #getting geometry name chosen by the user
    geom = collection.GetGeometry(selected_geometry_name)
    filtered_names = [gflist[i] for i in gf_selected]

    cell_grid_functions = [
        i
        for i in filtered_names
        if geom.HasGridFunction(i) and geom.GetGridFunction(i).GetLocation() == GridLocation.CELL.value
    ]
    nodal_grid_functions = [
        i
        for i in filtered_names
        if geom.HasGridFunction(i) and geom.GetGridFunction(i).GetLocation() == GridLocation.NODE.value
    ]

    if not multiple_files:
        if cell_grid_functions:
            cell_file = open(os.path.join(data_folder_path, base_file_name + "_cell_properties.csv"), 'w')
            cell_file.write("Geometry = " + selected_geometry_name +"\n")
            cell_file.write("Triangle ID, X, Y, Z, ")
            cell_file.write(",".join(cell_grid_functions) + "\n")
        if nodal_grid_functions:
            node_file = open(os.path.join(data_folder_path, base_file_name + "_nodal_properties.csv"), 'w')
            node_file.write("Geometry = " + selected_geometry_name +"\n")
            node_file.write("Node ID, X, Y, Z, ")
            node_file.write(",".join(nodal_grid_functions) + "\n")
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)
            if cell_grid_functions:
                cell_file.write(f"time (s) = {time_array[time_step]} \n")
                write_cell_gf_for_timestep(geom, cell_grid_functions, cell_file, time_step)
                cell_file.write("\n")
            if nodal_grid_functions:
                node_file.write(f"time (s) = {time_array[time_step]} \n")
                write_node_gf_for_timestep(geom, nodal_grid_functions, node_file, time_step)
                node_file.write("\n")
        if cell_grid_functions: cell_file.close()
        if nodal_grid_functions: node_file.close()

    else:
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)
            if cell_grid_functions:
                fname = os.path.join(data_folder_path, base_file_name + f"_cell_properties_{time_array[time_step]}s.csv")
                with open(fname, 'w') as f:
                    f.write("Geometry = " + selected_geometry_name +"\n")
                    f.write("Triangle ID, X, Y, Z, ")
                    f.write(",".join(cell_grid_functions) + "\n")
                    write_cell_gf_for_timestep(geom, cell_grid_functions, f, time_step)
                    f.write("\n")
            if nodal_grid_functions:
                fname = os.path.join(data_folder_path, base_file_name + f"_node_properties_{time_array[time_step]}s.csv")
                with open(fname, 'w') as f:
                    f.write("Geometry = " + selected_geometry_name +"\n")
                    f.write("Node ID, X, Y, Z, ")
                    f.write(",".join(nodal_grid_functions) + "\n")
                    write_node_gf_for_timestep(geom, nodal_grid_functions, f, time_step)
                    f.write("\n")


def create_scrollable_list(asklist, width=400, height=200):
    qt_app = QApplication.instance() or QApplication(sys.argv)    
    window = QDialog()
    window.setWindowTitle('Export details')
    layout = QVBoxLayout()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    input_widgets = []

    for label, default in asklist:
        if isinstance(default, bool):
            checkbox = QCheckBox(label)
            checkbox.setChecked(default)
            input_widgets.append(checkbox)
            scroll_layout.addWidget(checkbox)
        elif isinstance(default, list):
            scroll_layout.addWidget(QLabel(label))
            combo = QComboBox()
            combo.addItems([str(item) for item in default])
            input_widgets.append(combo)
            scroll_layout.addWidget(combo)

    scroll.setWidget(scroll_content)
    layout.addWidget(scroll)

    confirm = QPushButton('Confirm')
    layout.addWidget(confirm)
    confirm.clicked.connect(window.accept)

    window.setLayout(layout)
    window.resize(width, height)
    window.exec()

    results = []
    for w in input_widgets:
        if isinstance(w, QCheckBox):
            results.append(w.isChecked())
        elif isinstance(w, QComboBox):
            results.append(w.currentIndex())
    return results


export_boundary_information()
