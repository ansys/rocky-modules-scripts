"""
Logic functions (no GUI manipulation)
"""
import os
import pandas as pd

def get_available_processes(app):
    processes_dict = {}

    if len(app.GetStudy().GetParticleCollection()) > 0:
        processes_dict["Particles"] = app.GetStudy().GetParticles()

    if app.GetStudy().GetSphSettings().GetEnabled():
        processes_dict["SPH"] = app.GetStudy().GetSphSettings()

    gc = app.GetStudy().GetGeometryCollection()

    geometry = next(
        (
            gc.GetGeometry(i)
            for i in gc.GetGeometryNames()
            if gc.GetGeometry(i).GetClassName() == "CustomBoundaryProcessSubject"
        ),
        None
    )

    if geometry is not None:
        processes_dict["Geometries"] = geometry

    if app.GetStudy().GetJointsData().IsCollectJointDataEnabled():
        processes_dict["Joints"] = app.GetStudy().GetJointsData()

    if app.GetStudy().GetContactData().IsCollectContactsDataEnabled():
        processes_dict["Contacts"] = app.GetStudy().GetContactData()

    if app.GetStudy().GetCFDCoupling().GetCouplingMode() != 'no_coupling':
        processes_dict["CFD"] = app.GetStudy(
        ).GetCFDCoupling().GetCouplingProcess()

    pc_collection = app.GetStudy().GetPointCloudCollection()

    if len(pc_collection) > 0:
        for pc in pc_collection:
            processes_dict[pc.GetName()] = pc

    return processes_dict


def rocky_processes(app, presets_folder, key):
    if not key:
        return {"process": None, "gfs": [], "color_scales": []}

    processes_dict = get_available_processes(app)
    process = processes_dict.get(key)

    if process is None:
        return {"process": None, "gfs": [], "color_scales": []}

    gfs = sorted(process.GetGridFunctionNames())

    color_presets = os.listdir(presets_folder)
    color_scales = [
        os.path.splitext(file)[0]
        for file in color_presets if file.endswith('.txt')
    ]

    return {
        "process": process,
        "gfs": gfs,
        "color_scales": color_scales
    }


def set_color_scale(presets_folder, selected):
    if not selected:
        return None

    file_path = os.path.join(presets_folder, selected + ".txt")

    if not os.path.exists(file_path):
        return None

    data = pd.read_csv(file_path)

    data.iloc[:, 1:] = data.iloc[:, 1:] / 255.0

    return [
        (
            float(row["scalar"]),
            (
                float(row["RGB_r"]),
                float(row["RGB_g"]),
                float(row["RGB_b"])
            )
        )
        for _, row in data.iterrows()
    ]
    