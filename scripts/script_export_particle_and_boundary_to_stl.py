'''
Name for generated for script:
    Export Particle Beds and Geometries as Binary STL Files

Script description:
    This script exports a binary stl containing all single element particles in the output time selected when playing the script.
    The particles in the stl will have the same size and orientation they have in Rocky at the selected time. 
    This script works for different particle groups and particle size distributions.
    This script does not work for multi-component particles, such as fibers composed by several segments or flexible solids.
    In addition, The script exports the Geometries involved in the simulation and one stl file for each Particle Group.

@author: Ansys
@script_id:script_export_particle_and_boundary_to_stl
@date: 2025-11
@version: 1.2.3
'''

from __future__ import absolute_import, division, print_function, unicode_literals
from esss_qt10.qt_traits.process_events import ProcessEvents
import numpy
import math
import time
import os
import io
from six.moves import range
import struct
from enum import Enum

from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QPushButton
)
from PyQt6.QtCore import Qt

facet_dtype = {
    'names': ['normals', 'x', 'y', 'z', 'attr'],
    'formats': ['3f4', '3f4', '3f4', '3f4', 'u2']
}

AUTOFILL_ENV_VAR = "ROCKY_SCRIPTS_AUTOFILL"
AUTOFILL_ENABLED_VALUE = "1"
PARTICLE_STL_FOLDER = "particle-stl"


class RegionSelection(Enum):
    ALL_PARTICLES = "All particles"


FILTERED_GEOMETRY_CLASSES = {
    'InletProcessSubject',
    'PlaneProcessSubject',
    'InspectorProcessSubject',
    'PropertyProcessSubject',
    'CubeProcessSubject',
}
 
# auxiliary functions

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

def export_particles_stl(study, data_folder_path):
    # exporting the particle stl of all particle groups
    particle_collection = study.GetParticleCollection()

    # creating list to store particle names
    file_names = []
    # creating list to store the reference particle size from the STL export.
    # This is used to scale particles from their sieve size to actual runtime size
    particle_reference_sizes = []
    for i in range(len(particle_collection)):
        # getting particle
        particle = particle_collection[i]

        # getting particle reference size from size distribution
        particle_info = particle.GetSubject().GetInfo()
        particle_scale = particle_info.size_scale
        size_distribution_list = particle.GetSizeDistributionList()
        size_scale = size_distribution_list[0].GetScaleFactor()
        reference_size = size_distribution_list[0].GetSize()
        
        # The reference size is always the characteristic size from the distribution
        # regardless of whether it's sieve size or equivalent diameter
        particle_reference_sizes.append(reference_size * particle_scale)

        # exporting particle
        toolkit = study.GetExportToolkit()
        file_name=os.path.join(data_folder_path, "particle"+str(i))
        file_names.append(file_name+".stl")
        toolkit.ExportToSTL(file_name, particle, output_unit='m')

    return file_names, particle_reference_sizes

def export_geometry_stl(study, geometry__names_list, data_folder_path):
    # exporting the geometry parts as stl file
    geometry_collection = study.GetGeometryCollection()
    file_names = []
    toolkit = study.GetExportToolkit()
    print(geometry__names_list)
    for i, p in enumerate(geometry__names_list):
        geom = geometry_collection.GetGeometry(p)
        if (str(type(geom)).find('surface') <= 0):
            file_name=os.path.join(data_folder_path, "geometry"+str(i))
            file_names.append(file_name+".stl")
            toolkit.ExportToSTL(file_name, geom, output_unit='m')

    return file_names

def read_binary_stl(stl_name):
    #reading the binary stl to get the normals and vertex

    stl_file = open(stl_name, "rb")
    head = stl_file.read(80)
    nbtriangles=stl_file.read(4)
    number_of_triangles=struct.unpack("<I", nbtriangles)[0]
    # print(number_of_triangles)

    record_dtype = numpy.dtype([
        ('Normals', numpy.float32, (3,)),
        ('Vertex1', numpy.float32, (3,)),
        ('Vertex2', numpy.float32, (3,)),
        ('Vertex3', numpy.float32, (3,)),
        ('atttr', '<i2', (1,))
    ])


    data = numpy.fromfile(stl_file , dtype = record_dtype , count = number_of_triangles)

    stl_file.close()

    Normals = data['Normals']
    Vertex1 = data['Vertex1']
    Vertex2 = data['Vertex2']
    Vertex3 = data['Vertex3']

    return(Normals, Vertex1, Vertex2, Vertex3)

#from itertools import izip



def rotation_matrix(orientation_vetor, orientation_angle):
    from math import sqrt, cos, sin
    # Normalizing base vector
    x = orientation_vetor[0]
    y = orientation_vetor[1]
    z = orientation_vetor[2]
    module = sqrt(x * x + y * y + z * z)
    if module == 0:
        return None
    x /= module
    y /= module
    z /= module
    #ang = math.radians(orientation_angle)
    ang = (orientation_angle)
    c = cos(ang)
    s = sin(ang)
    t = 1 - c
    rotation_matrix = numpy.array([[t * x * x + c, t * x * y - z * s, t * x * z + y * s],
                                   [t * x * y + z * s, t * y * y + c, t * y * z - x * s],
                                   [t * x * z - y * s, t * y * z + x * s, t * z * z + c]])   
     
    return rotation_matrix

def rotate_particle(normal, vertex1, vertex2, vertex3, rotation_matrix):

    rotated_normal = numpy.matmul(rotation_matrix, normal.transpose()).transpose()
    rotated_vertex1 = numpy.matmul(rotation_matrix, vertex1.transpose()).transpose()
    rotated_vertex2 = numpy.matmul(rotation_matrix, vertex2.transpose()).transpose()
    rotated_vertex3 = numpy.matmul(rotation_matrix, vertex3.transpose()).transpose()
    #print(rotated_normal)
    return (rotated_normal, rotated_vertex1, rotated_vertex2, rotated_vertex3)

def position_particle(normal, vertex1, vertex2, vertex3, x, y, z):
    position = numpy.array([x, y, z])
    # print("position", position)

    translated_vertex1 = vertex1 + position
    translated_vertex2 = vertex2 + position
    translated_vertex3 = vertex3 + position

    return (normal, translated_vertex1, translated_vertex2, translated_vertex3)

def scale_particle(normal, vertex1, vertex2, vertex3, scale):
   
    scaled_vertex1 = vertex1*scale
    scaled_vertex2 = vertex2*scale
    scaled_vertex3 = vertex3*scale

    return (normal, scaled_vertex1, scaled_vertex2, scaled_vertex3)


def write_file(case_file, translated_normal, translated_vertex1, translated_vertex2, translated_vertex3, number_of_triangles):
    np_data = numpy.zeros(len(translated_normal), dtype=facet_dtype)
    np_data['normals'] = translated_normal
    np_data['x'] = translated_vertex1
    np_data['y'] = translated_vertex2
    np_data['z'] = translated_vertex3
    np_data['attr'] = 0

    np_data.tofile(case_file)


def dialog(project, time_array):
    class InputDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Export Particle Bed and Boundary")
            self.setMinimumWidth(400)
            layout = QVBoxLayout()

            layout.addWidget(QLabel("Select Time [s]:"))
            self.time_combo = QComboBox()
            self.time_combo.addItems(["%g" % t for t in time_array])
            self.time_combo.setCurrentIndex(len(time_array)//2)
            layout.addWidget(self.time_combo)

            layout.addWidget(QLabel("Scale Particle Bed (0-1):"))
            self.scale_spin = QDoubleSpinBox()
            self.scale_spin.setRange(0.0, 1.0)
            self.scale_spin.setValue(1.0)
            self.scale_spin.setSingleStep(0.1)
            layout.addWidget(self.scale_spin)

            user_processes = project.GetUserProcessCollection()
            user_processes_names = [RegionSelection.ALL_PARTICLES.value]
            for name in user_processes.GetCubeProcessNames():
                user_processes_names.append(name)
            for name in user_processes.GetCylinderProcessNames():
                user_processes_names.append(name)
            for name in user_processes.GetPolyhedronProcessNames():
                user_processes_names.append(name)
            for name in user_processes.GetPropertyProcessNames():
                user_processes_names.append(name)

            layout.addWidget(QLabel("Particle Region:"))
            self.region_combo = QComboBox()
            self.region_combo.addItems(user_processes_names)
            layout.addWidget(self.region_combo)

            self.ok_button = QPushButton("OK")
            self.ok_button.clicked.connect(self.accept)
            layout.addWidget(self.ok_button)

            self.setLayout(layout)

    app_qt = QApplication.instance()
    if not app_qt:
        app_qt = QApplication([])

    dialog = InputDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (
            dialog.time_combo.currentIndex() + 1,
            dialog.scale_spin.value(),
            dialog.region_combo.currentIndex()
        ), [dialog.region_combo.itemText(i) for i in range(dialog.region_combo.count())]
    return None, None


def export_particles():
    #This is the main function

    # Checking if a project is opened
    project = api.GetProject()
    if project is None:
        Message = [(None, '<b>Information</b>: There is no project opened. Please open a project before running this macro.')]

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
    
    # checking if the project has multi-component particles
    particle_collection = study.GetParticleCollection()
    particles = study.GetParticles()
    for particle in particle_collection:
        if particle.GetFlexible():
            Message = [(None, '<b>Information</b>: Project has multi-component/flexible particles. This script only supports single-element particles.')]
            print("result:", fedit(Message, title="Error message"))
            return 
        
    #checking project path and creating a new folder to save files    
    folder_name = PARTICLE_STL_FOLDER
    base_file_name, data_folder_path = get_project_filename_and_create_folder(project, folder_name)

    #exporting particles stls
    stl_file_names, particle_reference_sizes = export_particles_stl(study, data_folder_path)
    print(particle_reference_sizes)

    #exporting geometry stls
    geometry_collection = study.GetGeometryCollection()
    geometry_names = geometry_collection.GetGeometryNames()
    # Remove Inlet and User Processes from geometry list
    geometry__names_list = [
        i
        for i in geometry_names
        if geometry_collection.GetGeometry(i).GetClassName() not in FILTERED_GEOMETRY_CLASSES
    ]
    geom_stl_file_names = export_geometry_stl(study, geometry__names_list, data_folder_path) 

    # getting time array
    time_array = timeset.GetValues()

    # AUTOFILL / TEST MODE 
    if os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE:
        region_options = [RegionSelection.ALL_PARTICLES.value]
        result = (1, 1.0, 0)  # (time_index_1based, scale, region_index)
    else:
        result, region_options = dialog(project, time_array)

    # Dealing with cancel
    if result is None:
        print("Macro canceled")
        return

    time_step = result[0] - 1
    
    # reading the particles' stl
    particleSTLs = list()
    for i, file in enumerate(stl_file_names):
        stl = read_binary_stl(stl_file_names[i])
        particleSTLs.append(stl)

    # reading the geometries's stl    
    geomSTLs = list()
    for filename in geom_stl_file_names:
        stl = read_binary_stl(filename)
        geomSTLs.append(stl)

    initial_time = time.time()

    # Moving to the next time step and writing its value in the file
    app.GoToTimeStep(time_step)

    # Mounting the name of the file with the time step
    base_file_name_time_step = base_file_name + '-{0:.3f}.stl'.format(time_array[time_step])
    base_file_name_time_step = 'Particle_Bed' + '.stl'
    with open(os.path.join(data_folder_path, base_file_name_time_step), 'wb') as case_file:
        # Write header
        case_file.write(b'\0' * 80) 

        # write a temporary number of triangles
        number_of_triangles = 0
        case_file.write(struct.pack('I', number_of_triangles))

        selected_region_name = region_options[result[2]]
        if selected_region_name != RegionSelection.ALL_PARTICLES.value:
            region_to_account = study.GetElement(selected_region_name)
            particles = region_to_account

        Index = particles.GetGridFunction('Particle ID').GetArray(time_step=time_step)
        X = particles.GetGridFunction('Particle X-Coordinate').GetArray(time_step=time_step)
        Y = particles.GetGridFunction('Particle Y-Coordinate').GetArray(time_step=time_step)
        Z = particles.GetGridFunction('Particle Z-Coordinate').GetArray(time_step=time_step)
        OrientationX = particles.GetGridFunction('Orientation Vector X').GetArray(time_step=time_step)
        OrientationY = particles.GetGridFunction('Orientation Vector Y').GetArray(time_step=time_step)
        OrientationZ = particles.GetGridFunction('Orientation Vector Z').GetArray(time_step=time_step)
        OrientationAngle = particles.GetGridFunction('Orientation Angle').GetArray(time_step=time_step)
        Size = particles.GetGridFunction('Particle Size').GetArray(time_step=time_step)      
        Particle_name = particles.GetGridFunction('Particle Group').GetArray(time_step=time_step)

        text = []
        particles_total = float(particles.GetNumberOfParticles(time_step=time_step))
        last_update = time.time()
        for i, p in enumerate(particles.IterParticles(time_step=time_step)):
            #finding the particle rotation matrix
            particle_rotation_matrix = rotation_matrix([OrientationX[i], OrientationY[i], OrientationZ[i]], OrientationAngle[i])
            #getting the correspondent particle vertex and normals
            normal = particleSTLs[Particle_name[i]][0]
            vertex1 = particleSTLs[Particle_name[i]][1]
            vertex2 = particleSTLs[Particle_name[i]][2]
            vertex3 = particleSTLs[Particle_name[i]][3]
            scale = Size[i]/particle_reference_sizes[Particle_name[i]]
            print(scale)

            #rotating the particle
            rotated_normal, rotated_vertex1, rotated_vertex2, rotated_vertex3 = rotate_particle(normal, vertex1, vertex2, vertex3, particle_rotation_matrix)
            #scaling the particle
            scaled_normal, scaled_vertex1, scaled_vertex2, scaled_vertex3 = scale_particle(rotated_normal, rotated_vertex1, rotated_vertex2, rotated_vertex3, scale*result[1])
            #translating the particle
            translated_normal, translated_vertex1, translated_vertex2, translated_vertex3 = position_particle(scaled_normal, scaled_vertex1, scaled_vertex2, scaled_vertex3, X[i], Y[i], Z[i])

            number_of_triangles += len(translated_normal)

            #writing the triangles of that particle in the file
            write_file(case_file, translated_normal, translated_vertex1, translated_vertex2, translated_vertex3, number_of_triangles)

            if time.time() - last_update >= 1.0:            
                print('Particle: %s / %s (%.2f %%)' % (i, particles_total, (100*i/particles_total)))
                ProcessEvents()
                last_update = time.time()


        # write the number of triangles        
        print('Number of triangles:', number_of_triangles)
        # skip header
        case_file.seek(80)
        case_file.write(struct.pack('I', number_of_triangles))
                        
    print('Total time: %.2fs' % (time.time() - initial_time))


export_particles()
