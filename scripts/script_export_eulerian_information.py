# -*- coding: utf-8 -*-
"""
Created on Wed Jun  8 09:03:52 2016

Name for generated for script: Export Eulerian Statistics information

Script description: Script to export Eulerian Statistics Information.
For selected time range, exports the selected variables in a single file containing
all outputs or one file per output. 

@author: Ansys
@script_id:script_export_eulerian_statistics_properties
@version: 1.1.1
@date: 08 - 2024

"""

import numpy
import time
import os
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QCheckBox, QLabel, QPushButton, QComboBox, QScrollArea, QWidget


AUTOFILL_ENV_VAR = "ROCKY_SCRIPTS_AUTOFILL"
AUTOFILL_ENABLED_VALUE = "1"
EULERIAN_DATA_FOLDER = "eulerian_data"

    
# auxiliary functions

def get_project_filename_and_create_folder(project, folder_name):
    project_filename = project.GetProjectFilename()
    project_path = os.path.dirname(project_filename)
    project_name = os.path.splitext(os.path.basename(project_filename))[0]
    
    # Base name for the generate file(s)
    base_file_name = project_name + "_" + str(folder_name) 
    
    # Creation of a folder to save the files
    data_folder_path = os.path.join(project_path, str(folder_name))
    if not os.path.exists(data_folder_path):
        os.mkdir(data_folder_path)  
        
    return (base_file_name, data_folder_path)


def get_selected_gf_names(filtered_names, eul):
    grid_function_names = ["Bin,Center X,Center Y,Center Z"]
    number_of_bins = eul.GetNumberOfCells()
    # get the arrays for the selected properties
    for name in filtered_names:
        print(name)
        gf = eul.GetGridFunction(name).GetArray()
        
        if len(gf) == number_of_bins:
            grid_function_names.append(name)
            
        elif len(gf) > number_of_bins:
            number_elements = int(len(gf) / number_of_bins)
            for component in range(number_elements):
                grid_function_names.append(f"{name}[{component}]")
        else:
            print('Error!! - cannot recognize the grid function type')
    return grid_function_names       


def write_gf_for_timestep(eul, filtered_names, case_file, time_step):
    #write the desired grid funtions for the given time step in a certain case file, as well as the bin number
    number_of_bins = eul.GetNumberOfCells()  
    position_array = eul.GetCellCenterAsArray().reshape((number_of_bins, 3))
    bins_array = (numpy.arange(number_of_bins, dtype=numpy.int32)).reshape((number_of_bins, 1))
    data_array = numpy.hstack((bins_array, position_array))

    for name in filtered_names:
        gf = eul.GetGridFunction(name).GetArray(time_step=time_step)
        number_elements = int(len(gf) / number_of_bins)
        data_array = numpy.hstack((data_array, gf.reshape((number_of_bins, number_elements))))

    numpy.savetxt(case_file, data_array, fmt="%.4e", delimiter=',')

# UI 

def create_scrollable_list(asklist):
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
    window.resize(500, 400)  # tamanho da janela
    window.exec()

    results = []
    for w in input_widgets:
        if isinstance(w, QCheckBox):
            results.append(w.isChecked())
        elif isinstance(w, QComboBox):
            results.append(w.currentIndex())
    return results


def export_eulerian_information():
    #This is the main function
    
    # Checking if a project is opened
    project = api.GetProject()
    if project is None:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: There is no project opened. Please open a project before running this script.')
        msg.setWindowTitle('No Project Opened')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return                           
    
    # Getting study    
    study = project.GetStudy()
    timeset = study.GetTimeSet()
    
    # Checking if the case has results
    if not study.HasResults():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: There are no results in this project. Please run the project before exporting Eulerian information.')
        msg.setWindowTitle('Missing project results')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return   
    
    #checking project path and creating a new folder to save files
    folder_name = EULERIAN_DATA_FOLDER
    base_file_name, data_folder_path = get_project_filename_and_create_folder(project, folder_name)
    
    # getting time array
    time_array = timeset.GetValues()
   
    #get the eulerian processes
    collection = project.GetUserProcessCollection()
    try:
        eul_names = collection.GetEulerianStatisticsNames()
    except:
        eul_names = []

    if not eul_names:
        all_names = collection.GetProcessNames()
        eul_names = [n for n in all_names if "Eulerian" in n]

    if not eul_names:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: There are no Eulerian Processes. Please create one before exporting.')
        msg.setWindowTitle('No Eulerian Process')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return 

    # Creating a window to ask user which variables he wants to export, at which time range and in one single file or multiple files                 
    asklist = [("One file per output ?", False),
               ("Initial time", [f"{t:.2f} s" for t in time_array]),
               ("Final time", [f"{t:.2f} s" for t in time_array]),
               ("Eulerian process :", eul_names)]
    if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
        # [multiple_files, time_start_idx, time_stop_idx, eulerian_process_idx]
        result = [False, 0, len(time_array) - 1, 0]  # single file, full range, first eulerian process
    else:
        result = create_scrollable_list(asklist)
        if result is None:
            print("Script canceled")
            return
        
    multiple_files = result[0]
    time_start = result[1]
    time_stop = result[2]
    eulerian_process = result[3]

    eul = collection.GetProcess(eul_names[eulerian_process])

   
    if time_start > time_stop:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: Final time is smaller than initial time. Please correct the order.')
        msg.setWindowTitle('Time Selection')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return

    gflist = eul.GetGridFunctionNames()
    asklist2 = [(grid, False) for grid in gflist]

    if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
        result2 = [True] * len(gflist)  # select all grid functions
    else:
        result2 = create_scrollable_list(asklist2)
        if result2 is None:
            print("Script canceled")
            return

    gf_selected = [i for i, x in enumerate(result2) if x]
    if not gf_selected:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText('<b>Information</b>: No property was selected for exporting. Please select at least one property.')
        msg.setWindowTitle('Property Selection')
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return         
    
    #Getting grid functin names
    filtered_names = [gflist[i] for i in gf_selected]
    grid_function_names = get_selected_gf_names(filtered_names, eul)

    # case the user has selected only a single file
    if not multiple_files:
        # create the file
        fname = os.path.join(data_folder_path, base_file_name + ".csv")
        case_file = open(fname, 'w')
        #writing the file header with the grid functions names
        case_file.write(",".join(grid_function_names) + "\n")
        # Now moving to the next time step and writing its value in the file
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)
            case_file.write(f"time (s) = {time_array[time_step]}\n")
            write_gf_for_timestep(eul, filtered_names, case_file, time_step)
        case_file.close()

    else:
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)
            fname = os.path.join(data_folder_path, base_file_name + f"-{time_array[time_step]}s.csv")
            case_file = open(fname, 'w')
            case_file.write(",".join(grid_function_names) + "\n")
            write_gf_for_timestep(eul, filtered_names, case_file, time_step)
            case_file.close()


export_eulerian_information()
