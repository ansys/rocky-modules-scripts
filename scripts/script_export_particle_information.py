'''
Warning: Changes in this file may not be correctly interpreted later on in the script engine.

Generated script file.

Name for generated for script: Export particle information

Script description: Script to export particle information.
For selected time range, exports the selected variables in a single file containing
all outputs or one file per output. 

@author: Ansys
@script_id:script_export_particle_properties
@version: 1.1.0
@date: 04 - 2022
'''
from __future__ import absolute_import, division, print_function, unicode_literals
import numpy
import time
import os
from enum import IntEnum


AUTOFILL_ENV_VAR = "ROCKY_SCRIPTS_AUTOFILL"
AUTOFILL_ENABLED_VALUE = "1"
PARTICLE_DATA_FOLDER = "particle-data"


class OutputFileMode(IntEnum):
    SINGLE_FILE = 0
    ONE_FILE_PER_OUTPUT = 2

    
# auxiliary functions

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

def get_selected_gf_names(filtered_names, particles):
    grid_function_names = []
        # get the arrays for the selected properties
    for j in filtered_names:
        gf = particles.GetGridFunction(j).GetArray()
        
        # checking if the grid function has more than 1 component or not
        if isinstance(gf[0], numpy.ndarray):
            number_elements = gf.shape[1]
            for k in range(number_elements):
                grid_function_names.append(j+"[" + str(k)+"]")
            
        elif isinstance(gf[0], numpy.int32) or isinstance(gf[0], numpy.float64)  or isinstance(gf[0], numpy.float32):
            grid_function_names.append(j)
            
        else:
            print('Error!! - cannot recognize the grid function type')
    return grid_function_names       

def write_gf_for_timestep(particles, filtered_names, case_file, time_step):
    # writes the desired quantities looping in the number of particles 
    number_particles = particles.GetNumberOfParticles(time_step)       
    for i in range(number_particles):
        values = []
        for j in filtered_names:          
            gf = particles.GetGridFunction(j).GetArray(time_step=time_step)
            if gf is not None:
                # checking if the grid function has more than 1 component or not
                if isinstance(gf[i], numpy.ndarray):
                    number_elements = gf.shape[1]
                    for k in range(number_elements):
                        values.append("{:12.5e}".format(gf[i][k]))
                elif isinstance(gf[i], numpy.int32) or isinstance(gf[i], numpy.float64) or isinstance(gf[i], numpy.float32):
                    values.append("{:12.5e}".format(gf[i]))
                else:
                    print('Error!!')
            else:
                values.append(str(numpy.nan))
                
        case_file.write(",".join(values))
        case_file.write("\n" )
       
    
def export_particle_information(input_dict):
    #This is the main function
    
    # Checking if a project is opened
    project = api.GetProject()
    if project is None:
        Message = [(None, '<b>Information</b>: There is no project opened. Please open a project before running this script.')]
    
        print("result:", fedit(Message, title="Error message"))
        return                           
    
    # Getting study    
    study = project.GetStudy()
    timeset = study.GetTimeSet()
    
    # Checking if the case has results
    if not study.HasResults():
        Message = [(None, '<b>Information</b>: There are no results in this project. Please run the project before exporting particle information.')]

        print("result:", fedit(Message, title="Error message"))                          
        return   
    
    #checking project path and creating a new folder to save files
    folder_name = PARTICLE_DATA_FOLDER
    base_file_name, data_folder_path = get_project_filename_and_create_folder(project, folder_name)
    
    # getting time array
    time_array = timeset.GetValues()
    #getting particles
    particles = study.GetParticles()
       
    #Dealing with the case that the user has pressed Cancel after running the script
    if input_dict is None:
        print("Script canceled")
        return
    #Getting grid functions list
    filtered_names = input_dict['selected_properties_list']
    multiple_files = input_dict['one_file_per_output'] == OutputFileMode.ONE_FILE_PER_OUTPUT
    time_start = int(input_dict['initial_time'].split(":")[0])
    time_stop = int(input_dict['final_time'].split(":")[0])

    # dealing with the case the user has set final time < initial time
    if (time_start > time_stop):
        Message = [(None, '<b>Information</b>: Final time is smaller then initial time. Please correct the order.')]

        print("result:", fedit(Message, title="Error message")) 
        return
    
    #Checking if at least one property was selected. If not, warn user
    gf_selected = [i for i, x in enumerate(filtered_names) if x is not False]
    
    if (gf_selected == []):
        Message = [(None, '<b>Information</b>: No property was selected for exporting. Please select at least one property to export.')]

        print("result:", fedit(Message, title="Error message")) 
        return     
    
    # Moving to first time step with particle to check the len of the property
    first_time_with_particles = -1
    for time_step in range(time_start, time_stop+1):
        particle_number = particles.GetNumberOfNodes(time_step)
        if particle_number > 0:
            first_time_with_particles = time_step
            print("first_time_with_particles", first_time_with_particles)
            break
    # If there are no particles in any time step, warn the user
    if first_time_with_particles == -1:
        Message = [(None, '<b>Information</b>: There are no particles in the selected time range. Please select a time range that contains particles.')]

        print("result:", fedit(Message, title="Error message"))
        return
               
    app.GoToTimeStep(first_time_with_particles)

    #Getting grid function names
    grid_function_names = filtered_names#= get_selected_gf_names(filtered_names, particles)
      
    # case the user has selected only a single file
    if not multiple_files:
        # create the file
        base_file_name_time_step = base_file_name + '.csv'
        case_file = open(os.path.join(data_folder_path, base_file_name_time_step), 'w')
                       
        #writing the file header with the grid functions names
        case_file.write(",".join(grid_function_names))
        case_file.write("\n" )
        
        # Now moving to the next time step and writing its value in the file
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)

            case_file.write("time (s) = %s" % time_array[time_step])
            case_file.write("\n" )
            
            write_gf_for_timestep(particles, filtered_names, case_file, time_step)
            
        case_file.close()
        
    # Now treating the case where the user asked for 1 file per output         
    if multiple_files:
                   
        # Moving to the next time step and writing its value in the file
        for time_step in range(time_start, time_stop+1):
            app.GoToTimeStep(time_step)

            # Mounting the name of the file with the time step                
            base_file_name_time_step = base_file_name + '-' + str(time_array[time_step]) + 's.csv'
            case_file = open(os.path.join(data_folder_path, base_file_name_time_step), 'w')
        
            case_file.write(",".join(grid_function_names))
            case_file.write("\n" )

            write_gf_for_timestep(particles, filtered_names, case_file, time_step)
            
            case_file.close()




from PyQt6.QtCore import QDate, QSize, Qt, QCoreApplication
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

class MainWindow(QMainWindow):
    def __init__(self,properties_list,time_list,output_dict, parent=None):
        super(MainWindow, self).__init__(parent)


        self.properties_list = properties_list
        self.time_list = time_list
        self.output_dict = output_dict
        self.listWidget = QListWidget()
        self.zip_lookup={}
        for property in self.properties_list:
            item = QListWidgetItem(property)
   
            item.setCheckState(Qt.CheckState.Unchecked)
            self.listWidget.addItem(item)

        self.one_file_per_output = QCheckBox("One File Per Output?")
        self.one_file_per_output.setCheckState(Qt.CheckState.Unchecked)

        self.lbl_initial = QLabel('Initial Time:', self)
        self.lbl_final = QLabel('Final Time:', self)
        self.initial_time = QComboBox(self)
        self.final_time = QComboBox(self)
        
        for i,time in enumerate(self.time_list):
            self.initial_time.addItem(f'{str(i)}: {str(time)}s')
            self.final_time.addItem(f'{str(i)}: {str(time)}s')

        self.select_all_item = QCheckBox("Select All")
        self.select_all_item.setCheckState(Qt.CheckState.Unchecked)

        self.button = QPushButton('OK')
        self.button.clicked.connect(self.GetOutputsAndQuit)

        self.select_all_item.toggled.connect(self.SelectAllAction)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.one_file_per_output)
        layout.addWidget(self.lbl_initial)
        layout.addWidget(self.initial_time)
        layout.addWidget(self.lbl_final)
        layout.addWidget(self.final_time)
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
        self.output_dict['one_file_per_output'] = self.one_file_per_output.checkState()
        self.output_dict['initial_time'] = self.initial_time.currentText()
        self.output_dict['final_time'] = self.final_time.currentText()
        self.output_dict['inputs_defined'] = True
        self.widget.close()
    

    def BatchSelection(self,desired_state):
        for index in range(self.listWidget.count()):         
            self.listWidget.item(index).setCheckState(desired_state)


study = app.GetStudy()

time_array = study.GetTimeSet().GetValues()
gflist = study.GetParticles().GetGridFunctionNames()

input_dict = {'inputs_defined': False}

# If set, run without UI (automation / CI)
if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
    # Defaults: select all properties, single file, full time range
    input_dict['selected_properties_list'] = list(gflist)
    input_dict['one_file_per_output'] = OutputFileMode.SINGLE_FILE
    input_dict['initial_time'] = f"0: {time_array[0]}s"
    input_dict['final_time'] = f"{len(time_array)-1}: {time_array[-1]}s"
    input_dict['inputs_defined'] = True
else:
    MainWindow(gflist, ["% s" % i for i in time_array], input_dict)

if input_dict['inputs_defined']:
    export_particle_information(input_dict)
else:
    Message = [(None, '<b>Information</b>: Script canceled by the user.')]
    print("result:", fedit(Message, title="Error message"))