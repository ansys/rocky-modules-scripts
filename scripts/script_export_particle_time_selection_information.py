"""
Created on Wed Jun  8 09:03:52 2016

Name for generated for Script: Export Particle Time Selection information

Script description: script to export Particle Time Selection Information.
Exports the selected variables in a single file for the selected Particle Time
Selection. 

@author: Ansys
@script_id:script_export_particle_time_selection_properties
@version: 1.1.0
@date: 07 - 2023
"""

import numpy
import time
import os
from enum import Enum
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *


PARTICLE_TIME_SELECTION_DATA_FOLDER = "Particle_time_selection_data"


class ExcludedGridFunction(Enum):
    STRESS_TENSOR = 'Stress Tensor'
    MOMENT_OF_INERTIA = 'Moment Of Inertia'


def show_message(text, title="Information"):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.exec()

def get_project_filename_and_create_folder(project, folder_name):
    # Getting project filename and creating a folder to save files 
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

def get_selected_gf_names(filtered_names, pts):
    grid_function_names = ["Particle"]
    number_of_particles = pts.GetNumberOfCells()
    # get the arrays for the selected properties
    for name in filtered_names:
        gf = pts.GetGridFunction(name).GetArray()
        if gf is None:
            show_message("One or more selected grid functions do not have data available for the entered time range.", "Warning")
        else:    
            if len(gf) == number_of_particles:
                grid_function_names.append(name)
            elif len(gf) > number_of_particles:
                number_elements = int(len(gf)/number_of_particles)
                for component in range(number_elements):
                    grid_function_names.append(name+"[" + str(component)+"]")
            else:
                print('Error!! - cannot recognize the grid function type')
    return grid_function_names       

def write_gf(pts, filtered_names, case_file):
    #write the desired grid funtions for the given PTS
    number_of_particles = pts.GetNumberOfCells()  
    data_array = numpy.arange(number_of_particles).reshape((number_of_particles,1))
    for name in filtered_names:
        gf = pts.GetGridFunction(name).GetArray()
        if gf is not None:    
            number_elements = int(len(gf)/number_of_particles)
            data_array=numpy.hstack((data_array,gf.reshape((int(number_of_particles), number_elements))))
    numpy.savetxt(case_file, data_array, fmt=b"%.4e",delimiter=',')

def export_time_selection_info(input_dict):
    #This is the main function
    
    # Checking if a project is opened
    project = api.GetProject()
    if project is None:
        show_message("There is no project opened. Please open a project before running this script.", "Error message")
        return                           
    
    # Getting study    
    study = project.GetStudy()
    
    # Checking if the case has results
    if not study.HasResults():
        show_message("There are no results in this project. Please run the project before exporting Eulerian information.", "Error message")
        return   
    
    #checking project path and creating a new folder to save files
    folder_name = PARTICLE_TIME_SELECTION_DATA_FOLDER
    base_file_name, data_folder_path = get_project_filename_and_create_folder(project, folder_name)
     
    #get the eulerian processes
    collection = project.GetUserProcessCollection()
    PTS_names = collection.GetParticleTimeSelectionProcessNames()

    if PTS_names == []:
        show_message("There are no Particle Time Selection in this project. Please create at least one before exporting its information.", "Error message")
        return
    


    #Dealing with the case that the user has pressed Cancel after running the script
    if input_dict is None:
        print("script canceled")
        return
    
    PTS_process = PTS_names.index(input_dict['time_selection'])
    pts = collection.GetProcess(PTS_names[PTS_process])

    #Checking if at least one property was selected. If not, warn user
    time_values = study.GetTimeSet().GetValues()
    for t in range(len(time_values)):
        if pts.GetNumberOfCells(time_step=t) > 0:
            first_time_with_particles = t
            break

    if first_time_with_particles == -1:
        show_message("No particles found in any timestep of the project.", "Error")
        return
    app.GoToTimeStep(first_time_with_particles)

    gf_selected = input_dict['selected_properties_list']
    if (gf_selected == []):
        show_message("No property was selected for exporting. Please select at least one property to export.", "Error message")
        return         
    
    #Getting grid functin names
    filtered_names = gf_selected
    grid_function_names = get_selected_gf_names(filtered_names, pts)
      
    # create the file
    base_file_name_time_step = base_file_name + ".csv"
    case_file = open(os.path.join(data_folder_path, base_file_name_time_step), 'w')
                      
    #writing the file header with the grid functions names
    case_file.write(",".join(grid_function_names))
    case_file.write("\n" ) 
    write_gf(pts, filtered_names, case_file)
    case_file.close()

class MainWindow(QMainWindow):
    def __init__(self,properties_list,time_process_list,output_dict, parent=None):
        super(MainWindow, self).__init__(parent)
        self.properties_list = properties_list
        self.time_process_list = time_process_list
        self.output_dict = output_dict
        self.listWidget = QListWidget()
        for property in self.properties_list:
            item = QListWidgetItem(property)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.listWidget.addItem(item)

        self.lbl_time_selection = QLabel('Particle Time Selection Process:', self)
        self.combo_time_selection = QComboBox(self)
        for time_process in self.time_process_list:
            self.combo_time_selection.addItem(time_process)

        self.select_all_item = QCheckBox("Select All")
        self.select_all_item.setCheckState(Qt.CheckState.Unchecked)

        self.button = QPushButton('OK')
        self.button.clicked.connect(self.GetOutputsAndQuit)
        self.select_all_item.toggled.connect(self.SelectAllAction)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.lbl_time_selection)
        layout.addWidget(self.combo_time_selection)
        layout.addWidget(self.select_all_item)
        layout.addWidget(self.listWidget, 1)
        layout.addWidget(self.button)

        self.widget = QDialog()
        self.widget.setLayout(layout)
        self.widget.exec()

    def SelectAllAction(self):
        if self.select_all_item.isChecked():
            self.BatchSelection(Qt.CheckState.Checked)
        else:
            self.BatchSelection(Qt.CheckState.Unchecked)

    def GetOutputsAndQuit(self):
        self.checked_items=[]
        for index in range(self.listWidget.count()):
            if self.listWidget.item(index).checkState() == Qt.CheckState.Checked:
                self.checked_items.append(self.listWidget.item(index).text())
        self.output_dict['selected_properties_list'] = self.checked_items
        self.output_dict['time_selection'] = self.combo_time_selection.currentText()
        self.output_dict['inputs_defined'] = True
        self.widget.close()

    def BatchSelection(self,desired_state):
        for index in range(self.listWidget.count()):         
            self.listWidget.item(index).setCheckState(desired_state)


 #get the eulerian processes
collection = app.GetProject().GetUserProcessCollection()
PTS_names = collection.GetParticleTimeSelectionProcessNames()
pts_name = collection.GetProcess(PTS_names[0])

#Getting grid functions list
complete_gflist = pts_name.GetGridFunctionNames()
# Removing Stress Tensor property as it is not working properly
gf_removed = [ExcludedGridFunction.STRESS_TENSOR.value, ExcludedGridFunction.MOMENT_OF_INERTIA.value]

gflist = [x for x in complete_gflist if x not in gf_removed]

input_dict={'inputs_defined':False}

MainWindow(gflist,PTS_names,input_dict)


if input_dict['inputs_defined']:
    export_time_selection_info(input_dict)
else:
    show_message("Script canceled by the user.", "Information")
