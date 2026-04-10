'''
Name for generated for script:
    Equivalent Network Circuit

Script description:
    This script calculate an equivalent network circuit

@author: Ansys
@script_id:script_equivalent_network_circuit
@date: 2021-12
@version: 1.2.0
'''

import os
import sys
import numpy as np
from enum import IntEnum


AUTOFILL_ENV_VAR = "ROCKY_SCRIPTS_AUTOFILL"
AUTOFILL_ENABLED_VALUE = "1"


class ContactType(IntEnum):
    PARTICLE_PARTICLE = 0
    PARTICLE_BOUNDARY = 1


def _is_pytest_run():
    return ("PYTEST_CURRENT_TEST" in os.environ) or ("pytest" in sys.modules)


def _autofill_enabled():
    return os.environ.get(AUTOFILL_ENV_VAR, "0") == AUTOFILL_ENABLED_VALUE and _is_pytest_run()


def _pick_index(values, target, tol=1e-12):
    for i, v in enumerate(values):
        try:
            if abs(float(v) - float(target)) <= tol:
                return i
        except Exception:
            pass
    return 0


def _pick_first_matching_name(names, preferred_substrings):
    """
    preferred_substrings: list[str]
    returns first name whose lower() contains any preferred_substrings in order.
    """
    low_names = [(n, (n or "").lower()) for n in names]
    for sub in preferred_substrings:
        sub = (sub or "").lower()
        for n, ln in low_names:
            if sub and sub in ln:
                return n
    return names[0] if names else ""


def _emit_progress(self, msg):
    progress = getattr(self, "progressSignal", None)
    if progress is None:
        return
    emit = getattr(progress, "emit", None)
    if callable(emit):
        emit(msg)
        return
    if callable(progress):
        progress(msg)


def create_contact_index(self):
    _emit_progress(self, "Status: Creating contacts ID's.")
    contacts = self.study.GetElement('Contacts')
    self.full_array_contact_type = contacts.GetGridFunction('Contact Type').GetArray(time_step=self.timestep)
    if self.full_array_contact_type is None:
        raise RuntimeError("The contact network does not have active contacts.\n\nPlease, review the selected output time.")
    index = np.zeros(len(self.full_array_contact_type))
    for i in range(len(self.full_array_contact_type)):
        index[i] = i
    contacts.AddGridFunction('Contact ID', index, '-', 'cell', time_step=self.timestep)


def get_contact_network(self):
    region = self.study.GetElement(self.region)
    self.array_contact_id = region.GetGridFunction('Contact ID (User Generated)').GetArray(time_step=self.timestep)
    self.array_contact_type = region.GetGridFunction('Contact Type').GetArray(time_step=self.timestep)
    self.array_contact_particle_group_from = region.GetGridFunction('Particle Group From').GetArray(time_step=self.timestep)
    self.array_contact_particle_group_to = region.GetGridFunction('Particle Group To').GetArray(time_step=self.timestep)
    self.array_contact_boundary_to = region.GetGridFunction('Boundary To').GetArray(time_step=self.timestep)
    self.array_contact_normal_force = region.GetGridFunction('Absolute Normal Force').GetArray(time_step=self.timestep)
    self.array_contact_particle_id_from = region.GetGridFunction('Particle ID From').GetArray(time_step=self.timestep)
    self.array_contact_particle_id_to = region.GetGridFunction('Triangle or Particle ID To').GetArray(time_step=self.timestep)


def get_particle_size(self):
    self.array_particle_size = self.study.GetElement('Particles').GetGridFunction('Particle Size').GetArray(time_step=self.timestep)


def get_sorted_list(reference, array):
    return list(zip(*(sorted(zip(reference, array)))))[1]


def get_thermal_properties(self):
    _emit_progress(self, "Status: Getting properties.")
    particles = self.study.GetParticleCollection()
    self.particles_names = particles.GetParticleNames()
    self.array_particle_young = []
    self.array_particle_conductivity = []
    self.array_particle_poisson = []
    self.current_id_part = []
    for particle_name in self.particles_names:
        self.current_id_part.append(particles.subject.GetIndexByName(particle_name))
        particle = self.study.GetElement(particle_name)
        self.array_particle_young.append(particle.GetMaterial().GetYoungsModulus(unit='N/m2'))
        self.array_particle_conductivity.append(particle.GetMaterial().GetThermalConductivity(unit='W/m.K'))
        self.array_particle_poisson.append(particle.GetMaterial().GetPoissonRatio(unit='-'))

    self.array_particle_young = get_sorted_list(self.current_id_part, self.array_particle_young)
    self.array_particle_conductivity = get_sorted_list(self.current_id_part, self.array_particle_conductivity)
    self.array_particle_poisson = get_sorted_list(self.current_id_part, self.array_particle_poisson)

    geometries = self.study.GetGeometryCollection()
    all_names = geometries.GetGeometryNames()

    self.geometries_names = []
    self.array_geometry_young = []
    self.array_geometry_conductivity = []
    self.array_geometry_poisson = []
    self.current_id_geom = []

    for geometry_name in all_names:
        geometry = self.study.GetElement(geometry_name)

        # Only these exist in geometries.subject (and are the ones with material)
        if geometry.GetClassName() != 'CustomBoundaryProcessSubject':
            continue

        self.current_id_geom.append(geometries.subject.GetIndexByName(geometry_name))
        self.geometries_names.append(geometry_name)

        self.array_geometry_young.append(geometry.GetMaterial().GetYoungsModulus(unit='N/m2'))
        self.array_geometry_conductivity.append(geometry.GetMaterial().GetThermalConductivity(unit='W/m.K'))
        self.array_geometry_poisson.append(geometry.GetMaterial().GetPoissonRatio(unit='-'))

    self.boundary_1_index = geometries.subject.GetIndexByName(self.boundary_1)
    self.boundary_2_index = geometries.subject.GetIndexByName(self.boundary_2)

    if self.boundary_1_index == self.boundary_2_index:
        raise RuntimeError(
            "The Low and High potential geometries you select must not be equal.\n\nPlease select different geometries."
        )


def compute_conductivity(self):
    _emit_progress(self, "Status: Computing contacts conductivities.")
    self.softening_factor = self.study.GetPhysics().GetNumericalSofteningFactor()
    self.array_contact_conductivity = np.zeros(len(self.array_contact_type))

    for i in range(len(self.array_contact_type)):
        if self.array_contact_type[i] == ContactType.PARTICLE_PARTICLE:
            equivalent_kc = (
                2 / (
                    1 / self.array_particle_conductivity[self.array_contact_particle_group_from[i]]
                    + 1 / self.array_particle_conductivity[self.array_contact_particle_group_to[i]]
                )
            )
            equivalent_young = (
                (1 - self.array_particle_poisson[self.array_contact_particle_group_from[i]] ** 2)
                * self.softening_factor
                / self.array_particle_young[self.array_contact_particle_group_from[i]]
                + (1 - self.array_particle_poisson[self.array_contact_particle_group_to[i]] ** 2)
                * self.softening_factor
                / self.array_particle_young[self.array_contact_particle_group_to[i]]
            ) ** -1

            equivalent_radius = (
                2 / self.array_particle_size[self.array_contact_particle_id_from[i]]
                + 2 / self.array_particle_size[self.array_contact_particle_id_to[i]]
            ) ** -1

            a = (3 * equivalent_radius * self.array_contact_normal_force[i] / (4 * equivalent_young)) ** (1 / 3)
            a *= self.softening_factor ** (4 / 15)
            self.array_contact_conductivity[i] = 2 * equivalent_kc * a
        else:
            if (self.array_contact_boundary_to[i] == self.boundary_1_index) or (
                self.array_contact_boundary_to[i] == self.boundary_2_index
            ):
                equivalent_kc = (
                    2
                    / (
                        1 / self.array_particle_conductivity[self.array_contact_particle_group_from[i]]
                        + 1 / self.array_geometry_conductivity[self.array_contact_boundary_to[i]]
                    )
                )
                equivalent_young = (
                    (1 - self.array_particle_poisson[self.array_contact_particle_group_from[i]] ** 2)
                    * self.softening_factor
                    / self.array_particle_young[self.array_contact_particle_group_from[i]]
                    + (1 - self.array_geometry_poisson[self.array_contact_boundary_to[i]] ** 2)
                    * self.softening_factor
                    / self.array_geometry_young[self.array_contact_boundary_to[i]]
                ) ** -1

                equivalent_radius = (2 / self.array_particle_size[self.array_contact_particle_id_from[i]]) ** -1

                a = (3 * equivalent_radius * self.array_contact_normal_force[i] / (4 * equivalent_young)) ** (1 / 3)
                a *= self.softening_factor ** (4 / 15)
                self.array_contact_conductivity[i] = 2 * equivalent_kc * a


def create_linear_system(self):
    _emit_progress(self, "Status: Creating linear system.")
    self.array_independent_term = np.zeros(len(self.array_particle_size))
    self.matrix_particle_coeff = np.zeros((len(self.array_particle_size), len(self.array_particle_size)))
    self.array_contacts_boundary1_particle = []
    self.array_contacts_boundary2_particle = []
    cont_boundary_1 = 0
    cont_boundary_2 = 0

    for i in range(len(self.array_contact_type)):
        if self.array_contact_type[i] == ContactType.PARTICLE_PARTICLE:
            self.matrix_particle_coeff[self.array_contact_particle_id_from[i]][self.array_contact_particle_id_from[i]] += (
                -self.array_contact_conductivity[i]
            )
            self.matrix_particle_coeff[self.array_contact_particle_id_from[i]][self.array_contact_particle_id_to[i]] += (
                self.array_contact_conductivity[i]
            )

            self.matrix_particle_coeff[self.array_contact_particle_id_to[i]][self.array_contact_particle_id_from[i]] += (
                self.array_contact_conductivity[i]
            )
            self.matrix_particle_coeff[self.array_contact_particle_id_to[i]][self.array_contact_particle_id_to[i]] += (
                -self.array_contact_conductivity[i]
            )
        else:
            if self.array_contact_boundary_to[i] == self.boundary_1_index:
                self.matrix_particle_coeff[self.array_contact_particle_id_from[i]][self.array_contact_particle_id_from[i]] += (
                    -self.array_contact_conductivity[i]
                )
                self.array_independent_term[self.array_contact_particle_id_from[i]] += -self.array_contact_conductivity[i]
                self.array_contacts_boundary1_particle.append(i)
                cont_boundary_1 += 1
            elif self.array_contact_boundary_to[i] == self.boundary_2_index:
                self.matrix_particle_coeff[self.array_contact_particle_id_from[i]][self.array_contact_particle_id_from[i]] += (
                    -self.array_contact_conductivity[i]
                )
                self.array_contacts_boundary2_particle.append(i)
                cont_boundary_2 += 1

    if cont_boundary_1 <= 0:
        raise RuntimeError(
            "The High potential geometry you selected does not have active contacts.\n\n"
            "Please review the dimensions of your User Process shape to ensure it includes all desirable contacts."
        )
    if cont_boundary_2 <= 0:
        raise RuntimeError(
            "The Low potential geometry you selected does not have active contacts.\n\n"
            "Please review the dimensions of your User Process shape to ensure it includes all desirable contacts."
        )

    self.index_out = []
    self.index_in = []
    for i in range(len(self.array_particle_size)):
        if self.matrix_particle_coeff[i][i] == 0:
            self.index_out.append(i)
        else:
            self.index_in.append(i)

    self.matrix_particle_coeff = np.delete(self.matrix_particle_coeff, self.index_out, axis=0)
    self.matrix_particle_coeff = np.delete(self.matrix_particle_coeff, self.index_out, axis=1)
    self.array_independent_term = np.delete(self.array_independent_term, self.index_out)


def resolve_linear_system(self):
    _emit_progress(self, "Status: Resolving linear system.")
    try:
        self.inverse = np.linalg.inv(self.matrix_particle_coeff)
        self.solution = self.inverse.dot(self.array_independent_term)
    except Exception as e:
        raise RuntimeError(
            "It was not possible to resolve the linear system.\n\n"
            "Please verify that the particle bed is fully formed, and that both the High and Low potential geometries "
            "you selected are correctly positioned within the Region of interest you selected.\n\n"
            f"Exception: {e}"
        )


def compute_local_rates(self):
    _emit_progress(self, "Status: Computing local rates.")
    self.array_contact_local_rate = np.zeros(len(self.array_contact_type))
    self.array_particle_local_rate = np.zeros(len(self.array_particle_size))
    self.full_solution = np.zeros(len(self.array_particle_size))
    self.full_solution[self.index_in] = self.solution

    for i in range(len(self.array_contact_type)):
        if self.array_contact_type[i] == ContactType.PARTICLE_PARTICLE:
            delta = self.full_solution[self.array_contact_particle_id_to[i]] - self.full_solution[self.array_contact_particle_id_from[i]]
            delta *= self.delta_potential
            self.array_contact_local_rate[i] = self.array_contact_conductivity[i] * abs(delta)
            if delta < 0:
                self.array_particle_local_rate[self.array_contact_particle_id_from[i]] += -self.array_contact_conductivity[i] * delta
            else:
                self.array_particle_local_rate[self.array_contact_particle_id_to[i]] += self.array_contact_conductivity[i] * delta
        else:
            if self.array_contact_boundary_to[i] == self.boundary_1_index:
                delta = 1 - self.full_solution[self.array_contact_particle_id_from[i]]
                delta *= self.delta_potential
                self.array_contact_local_rate[i] = self.array_contact_conductivity[i] * abs(delta)
            elif self.array_contact_boundary_to[i] == self.boundary_2_index:
                delta = 0 - self.full_solution[self.array_contact_particle_id_from[i]]
                delta *= self.delta_potential
                self.array_contact_local_rate[i] = self.array_contact_conductivity[i] * abs(delta)


def create_new_properties_curves(self):
    _emit_progress(self, "Status: Creating new properties and curves.")
    particles = self.study.GetElement('Particles')
    particles.AddGridFunction('Particle Potential', self.full_solution, '-', 'cell', time_step=self.timestep)
    particles.AddGridFunction('Outgoing Energy Flow', self.array_particle_local_rate, 'W', 'cell', time_step=self.timestep)

    contacts = self.study.GetElement('Contacts')
    full_array_contact_conductivity = np.zeros(len(self.full_array_contact_type))
    full_array_contact_local_rate = np.zeros(len(self.full_array_contact_type))
    full_array_contact_conductivity[self.array_contact_id.astype(int)] = self.array_contact_conductivity
    full_array_contact_local_rate[self.array_contact_id.astype(int)] = self.array_contact_local_rate
    contacts.AddGridFunction('Contact Conductivity', full_array_contact_conductivity, 'W/K', 'cell', time_step=self.timestep)
    contacts.AddGridFunction('Outgoing Energy Flow', full_array_contact_local_rate, 'W', 'cell', time_step=self.timestep)

    self.heat1 = 0
    for i in self.array_contacts_boundary1_particle:
        self.heat1 += (
            self.array_contact_conductivity[i]
            * (1 - self.full_solution[self.array_contact_particle_id_from[i]])
            * self.delta_potential
        )
    timeset = self.study.GetTimeSet()
    curve_equivalent_conductivity = np.zeros(len(timeset))
    for i in range(len(timeset)):
        if self.timestep == i:
            curve_equivalent_conductivity[i] = self.heat1 / self.delta_potential
    particles.AddCurve('Equivalent Conductivity', timeset, curve_equivalent_conductivity, 'W/K')

    for i, name in enumerate(self.geometries_names):
        if self.boundary_1 == name:
            value = 1
        elif self.boundary_2 == name:
            value = 0
        else:
            value = -1
        geometry = self.study.GetElement(self.geometries_names[i])
        geometry_potential = np.full(geometry.GetNumberOfCells(), value)
        geometry.AddGridFunction('Geometry Potential', geometry_potential, '-', 'cell', time_step=self.timestep)


def main(self):
    self.timestep = self.timeset
    self.region = self.roi
    self.boundary_1 = self.high_geometry
    self.boundary_2 = self.low_geometry

    self.project = self.app.GetProject()
    self.study = self.project.GetStudy()

    create_contact_index(self)
    get_contact_network(self)
    get_particle_size(self)

    if self.isRunning:
        get_thermal_properties(self)
    if self.isRunning:
        compute_conductivity(self)
    if self.isRunning:
        create_linear_system(self)
    if self.isRunning:
        resolve_linear_system(self)
    if self.isRunning:
        compute_local_rates(self)
    if self.isRunning:
        create_new_properties_curves(self)


class _HeadlessContext:
    """
    Small container to match the previous 'self' contract.
    """
    def __init__(self, app, timeset_idx, roi, high_geom, low_geom, delta_potential):
        self.isRunning = True
        self.app = app
        self.timeset = timeset_idx
        self.roi = roi
        self.high_geometry = high_geom
        self.low_geometry = low_geom
        self.delta_potential = float(delta_potential)

    def progressSignal(self, msg):
        # keep it quiet in tests; print if you want visibility
        # print(msg)
        return


def run_headless(app):
    project = app.GetProject()
    if project is None:
        raise RuntimeError("No project open.")

    study = project.GetStudy()
    times = study.GetTimeSet().GetValues()
    ts_idx = _pick_index(times, 0.1, tol=1e-9)

    # ROI: prefer "Cube <01>" then anything with "cube"
    user_processes = project.GetUserProcessCollection()
    roi_names = (
        user_processes.GetCubeProcessNames()
        + user_processes.GetCylinderProcessNames()
        + user_processes.GetPolyhedronProcessNames()
    )
    roi = _pick_first_matching_name(roi_names, ["cube <01>", "cube", "cylinder", "polyhedron"])

    # Geometries: use CustomBoundaryProcessSubject only
    geom_names = study.GetGeometryCollection().GetGeometryNames()
    custom_geoms = []
    for g in geom_names:
        try:
            if study.GetElement(g).GetClassName() == "CustomBoundaryProcessSubject":
                custom_geoms.append(g)
        except Exception:
            pass
    if len(custom_geoms) < 2:
        raise RuntimeError("Need at least two custom geometries (CustomBoundaryProcessSubject).")

    high = _pick_first_matching_name(custom_geoms, ["high", "hot", "upper"])
    # low must differ from high
    low_candidates = [g for g in custom_geoms if g != high]
    low = _pick_first_matching_name(low_candidates, ["low", "cold", "lower"])

    ctx = _HeadlessContext(
        app=app,
        timeset_idx=ts_idx,
        roi=roi,
        high_geom=high,
        low_geom=low,
        delta_potential=1.0,
    )
    main(ctx)


def _run_gui(app):
    
    from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt, QCoreApplication
    from PyQt6.QtWidgets import (
        QMessageBox, QPushButton, QDialog, QMainWindow,
        QVBoxLayout, QWidget, QFormLayout, QHBoxLayout,
        QComboBox, QLabel, QDoubleSpinBox
    )

    class MyWorker(QObject):
        signal_pre_processing = pyqtSignal()
        progressSignal = pyqtSignal(object)
        signal_post_processing = pyqtSignal()
        finished = pyqtSignal()

        def __init__(self, app, timeset, roi, high_geometry, low_geometry, delta_potential):
            super(MyWorker, self).__init__()
            self.isRunning = True
            self.app = app
            self.timeset = timeset
            self.roi = roi
            self.high_geometry = high_geometry
            self.low_geometry = low_geometry
            self.delta_potential = delta_potential

        def run(self):
            self.signal_pre_processing.emit()
            try:
                main(self)
            finally:
                if self.isRunning:
                    self.signal_post_processing.emit()
                self.finished.emit()

        def stop(self):
            self.isRunning = False
            self.progressSignal.emit("Status: Stopping calculation.")

    class graphical_user_interface(QMainWindow):
        def __init__(self, app):
            super().__init__(None)
            self.app = app
            self.first_checks()
            self.widget_main.exec()

        def first_checks(self):
            warning = (
                "The simulation does not yet meet the requirements for running this script.\n\n"
                "Please address the following items, and then run the script again:"
            )
            project = app.GetProject()
            if project is None:
                raise RuntimeError(
                    "You have not opened a project.\n\nPlease open or create the simulation project you want to use,\n"
                    "and then process it before running this script."
                )

            study = project.GetStudy()
            contacts = study.GetElement('Contacts')

            geometries_names = app.GetStudy().GetGeometryCollection().GetGeometryNames()
            self.geometries_names_filter = []
            for geometry_name in geometries_names:
                geometry = app.GetStudy().GetElement(geometry_name)
                if geometry.GetClassName() == 'CustomBoundaryProcessSubject':
                    self.geometries_names_filter.append(geometry_name)

            if len(self.geometries_names_filter) <= 1:
                warning += "\n  -  Import two geometries between which the contact network will be defined."
            if contacts.GetCollectContactsData() is False:
                warning += "\n  -  Enable the Collect Contacts Data checkbox."
            if study.HasResults() is False:
                warning += "\n  -  Process the simulation."

            user_processes = project.GetUserProcessCollection()
            user_processes_cube = user_processes.GetCubeProcessNames()
            user_processes_cylinder = user_processes.GetCylinderProcessNames()
            user_processes_polyhedron = user_processes.GetPolyhedronProcessNames()
            region_of_interest_names = user_processes_cube + user_processes_cylinder + user_processes_polyhedron
            self.region_of_interest_names_filter = []
            for region_name in region_of_interest_names:
                region = app.GetStudy().GetElement(region_name)
                if region.subject.GetSourceProcess().name == 'Contacts':
                    self.region_of_interest_names_filter.append(region_name)

            if len(self.region_of_interest_names_filter) == 0:
                warning += (
                    "\n  -  Create a Cube, Cylinder, or Polyhedron (Envelope) User Process shape\n"
                    "     on the Contacts entity to be used as a region of interest for the script."
                )

            if len(warning) > 142:
                raise RuntimeError(warning)
            return self.build_gui()

        def build_gui(self):
            self.widget_main = QDialog()
            self.widget_main.setWindowTitle('Equivalent Network Circuit')
            self.widget_main.setFixedSize(275, 285)

            self.layout_main = QVBoxLayout()
            self.widget_main.setLayout(self.layout_main)

            self.box1 = QWidget()
            self.box2 = QWidget()
            self.layout_main.addWidget(self.box1)
            self.layout_main.addWidget(self.box2)

            self.timeset = QComboBox()
            timeset_values = app.GetStudy().GetTimeSet().GetValues()
            self.timeset_list = ["% s" % i for i in timeset_values]
            self.timeset.setFixedWidth(110)
            self.timeset.setToolTip('Output time in [s].')
            self.timeset.addItems(self.timeset_list)
            self.timeset.currentIndexChanged.connect(self.update_timeset_value)

            self.property = QComboBox()
            self.property_list = ['Thermal']
            self.property.setFixedWidth(110)
            self.property.addItems(self.property_list)

            self.region_of_interest = QComboBox()
            self.region_of_interest_list = ["% s" % i for i in self.region_of_interest_names_filter]
            self.region_of_interest.setFixedWidth(110)
            self.region_of_interest.setToolTip(
                'Region of interest is defined through a User Process shape.\n\n'
                'You need to have created at least one Cube, Cylinder or\n'
                'Polyhedron (Envelope) User Process from the Contacts entity.'
            )
            self.region_of_interest.addItems(self.region_of_interest_list)

            self.high_geometry = QComboBox()
            self.high_geometry_list = ["% s" % i for i in self.geometries_names_filter]
            self.high_geometry.setFixedWidth(110)
            self.high_geometry.setToolTip(
                'A High potential geometry is defined as the custom (imported)\n'
                'geometry entity within the bounds of the Region of interest\n'
                'that has the highest potential.'
            )
            self.high_geometry.addItems(self.high_geometry_list)

            self.low_geometry = QComboBox()
            self.low_geometry_list = ["% s" % i for i in self.geometries_names_filter]
            self.low_geometry.setFixedWidth(110)
            self.low_geometry.setToolTip(
                'A Low potential geometry is defined as a custom (imported)\n'
                'geometry entity within the bounds of the Region of interest\n'
                'that has the lowest potential.'
            )
            self.low_geometry.addItems(self.low_geometry_list)

            self.delta_potential = QDoubleSpinBox()
            self.delta_potential.setFixedWidth(110)
            self.delta_potential.setValue(1.0)
            self.delta_potential.setDecimals(1)
            self.delta_potential.setRange(0, 10000)
            self.delta_potential.setToolTip('Temperature potential difference in K.\n\nRange: Positive values.')

            self.H_button_layout_input_1 = QHBoxLayout()
            self.ClosePushButton = QPushButton("Close", default=False, autoDefault=False)
            self.ClosePushButton.clicked.connect(self.close_call)
            self.ClosePushButton.setFixedWidth(110)
            self.StartPushButton = QPushButton("Calculate", default=False, autoDefault=False)
            self.StartPushButton.clicked.connect(self.calculation_call)
            self.StartPushButton.setFixedWidth(110)
            self.H_button_layout_input_1.addWidget(self.ClosePushButton)
            self.H_button_layout_input_1.addWidget(self.StartPushButton)
            self.H_button_layout_input_1.setAlignment(Qt.AlignLeft)

            self.H_button_layout_input_2 = QHBoxLayout()
            self.H_button_layout_input_2.setAlignment(Qt.AlignLeft)

            self.prograss_label = QLabel(self)

            self.form1 = QFormLayout()
            self.form1.addRow("Output time [s]:", self.timeset)
            self.form1.addRow("Analysis type:", self.property)
            self.form1.addRow("Region of interest:", self.region_of_interest)
            self.form1.addRow("High potential geometry:", self.high_geometry)
            self.form1.addRow("Low potential geometry:", self.low_geometry)
            self.form1.addRow("Potential difference [K]:", self.delta_potential)

            self.form2 = QFormLayout()
            self.form2.addRow(self.H_button_layout_input_1)
            self.form2.addRow(self.H_button_layout_input_2)
            self.form2.addRow(self.prograss_label)

            self.box1.setLayout(self.form1)
            self.box2.setLayout(self.form2)

        def update_timeset_value(self):
            self.app.GoToTimeStep(self.timeset.currentIndex())

        def close_call(self):
            self.widget_main.close()

        def calculation_call(self):
            self.thread = QThread()
            self.worker = MyWorker(
                self.app,
                self.timeset.currentIndex(),
                self.region_of_interest.currentText(),
                self.high_geometry.currentText(),
                self.low_geometry.currentText(),
                self.delta_potential.value(),
            )
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.signal_pre_processing.connect(self.pre_calculation)
            self.worker.progressSignal.connect(self.on_progressSignal)
            self.worker.signal_post_processing.connect(self.post_message)
            self.worker.finished.connect(self.post_calculation)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.thread.start()

            self.StoptPushButton = QPushButton("Stop", default=False, autoDefault=False)
            self.StoptPushButton.clicked.connect(self.stop_call)
            self.StoptPushButton.setFixedWidth(110)
            self.H_button_layout_input_2.addWidget(self.StoptPushButton)

        def on_progressSignal(self, text):
            self.prograss_label.setText(text)

        def stop_call(self):
            self.worker.stop()

        def pre_calculation(self):
            self.box1.setDisabled(True)
            self.StartPushButton.setDisabled(True)
            self.ClosePushButton.setDisabled(True)
            self.StartPushButton.setText('Calculating')

        def post_calculation(self):
            self.box1.setDisabled(False)
            self.StartPushButton.setDisabled(False)
            self.ClosePushButton.setDisabled(False)
            self.StartPushButton.setText('Calculate')
            self.StoptPushButton.deleteLater()
            self.prograss_label.setText("")

        def post_message(self):
            text = 'Geometries Properties'
            text += '\n      Geometry Potential (User Generated)'
            text += '\n\nParticles Properties'
            text += '\n      Particle Potential (User Generated)'
            text += '\n      Outgoing Energy Flow (User Generated)'
            text += '\nParticles Curves'
            text += '\n      Equivalent Conductivity (User)'
            text += '\n\nContacts Properties'
            text += '\n      Contact ID (User Generated)'
            text += '\n      Contact Conductivity (User Generated)'
            text += '\n      Outgoing Energy Flow (User Generated)'

            msg = QMessageBox(self.widget_main)
            msg.setWindowTitle("Equivalent Network Circuit")
            msg.setIcon(QMessageBox.Information)
            msg.setText('This script created the following entities:')
            msg.setInformativeText(text)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    graphical_user_interface(app)



if _autofill_enabled():
    
    run_headless(app)
else:
    _run_gui(app)