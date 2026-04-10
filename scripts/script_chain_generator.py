"""
Name for generated for script:
    Chain Generator

Script description:
    This script creates a chain courtain using custom fiber

@author: Ansys
@script_id:script_chain_generator
@date: 2022-07
@version: 1.2.0
"""

import math
import os
import re
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd


# Constants
MILLIMETER_TO_METER = 0.001
HALF_ROTATION = np.pi / 2
FULL_ROTATION = np.pi
DEGREES_IN_SEMICIRCLE = 180
LINK_SPACING_MULTIPLIER = 2.1


class Direction(Enum):
    """Enum for chain direction options."""
    Y_NEGATIVE = "-Y direction"
    X_POSITIVE = "X direction"
    Z_POSITIVE = "Z direction"
    X_NEGATIVE = "-X direction"
    Y_POSITIVE = "Y direction"
    Z_NEGATIVE = "-Z direction"


class ConstraintType(Enum):
    """Enum for chain constraint types."""
    FREE_FREE = "free-free"
    FIXED_FREE = "fixed-free"
    FIXED_FIXED = "fixed-fixed"


def _autofill_enabled() -> bool:
    return os.environ.get("ROCKY_SCRIPTS_AUTOFILL", "0") == "1"


if not _autofill_enabled():
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QFormLayout, QLineEdit, QCheckBox,
        QComboBox, QDialogButtonBox, QLabel
    )


def show_form(fields, title="Input", comment=""):
    # AUTOFILL / TEST MODE
    if _autofill_enabled():
        results = []
        for label, default in fields:
            if label is None:
                results.append(default)
            elif isinstance(default, bool):
                results.append(default)
            elif isinstance(default, (list, tuple)):
                results.append(1 if len(default) > 1 else 0)
            else:
                results.append(default)
        return results

    # GUI mode
    app_qt = QApplication.instance() or QApplication([])

    dlg = QDialog()
    dlg.setWindowTitle(title)
    layout = QFormLayout(dlg)

    if comment:
        layout.addRow(QLabel(comment))

    widgets = []
    for label, default in fields:
        if label is None:
            layout.addRow(QLabel(str(default) if default else ""))
            widgets.append(None)
            continue

        if isinstance(default, bool):
            w = QCheckBox()
            w.setChecked(default)
        elif isinstance(default, (list, tuple)):
            w = QComboBox()
            for opt in default:
                w.addItem(str(opt))
            w.setCurrentIndex(0)
        else:
            w = QLineEdit(str(default))

        layout.addRow(label, w)
        widgets.append(w)

    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(btns)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None

    results = []
    for w, (_, default) in zip(widgets, fields):
        if w is None:
            results.append(default)
        elif isinstance(w, QCheckBox):
            results.append(w.isChecked())
        elif isinstance(w, QComboBox):
            results.append(w.currentIndex())
        else:
            txt = w.text().strip()
            try:
                results.append(float(txt) if "." in txt else int(txt))
            except ValueError:
                results.append(txt)
    return results


def rotate(rotation_axis, coords, theta):
    ux, uy, uz = rotation_axis

    rotation_matrix = np.array(
        [
            [np.cos(theta) + (1 - np.cos(theta)) * ux**2,
             (1 - np.cos(theta)) * ux * uy - np.sin(theta) * uz,
             (1 - np.cos(theta)) * ux * uz + np.sin(theta) * uy],
            [(1 - np.cos(theta)) * uy * ux + np.sin(theta) * uz,
             np.cos(theta) + (1 - np.cos(theta)) * uy**2,
             (1 - np.cos(theta)) * uy * uz - np.sin(theta) * ux],
            [(1 - np.cos(theta)) * uz * ux - np.sin(theta) * uy,
             (1 - np.cos(theta)) * uz * uy + np.sin(theta) * ux,
             np.cos(theta) + (1 - np.cos(theta)) * uz**2],
        ]
    )

    a = [str(i) for i in np.dot(coords[:3], rotation_matrix)]
    b = [str(i) for i in np.dot(coords[3:], rotation_matrix)]
    return ",".join(a) + "," + ",".join(b)


def link_geo():
    fields = [
        ("Length [mm]", 60.0),
        ("Width  [mm]", 35.0),
        ("Wire diameter [mm]", 10.0),
        ("Material density [kg/m3]", 7800.0),
    ]
    setup = show_form(fields, title="Link definition", comment="Specify the link dimensions and material")
    if setup is None:
        return None

    material_collection = app.GetStudy().GetMaterialCollection()
    mat = material_collection.AddSolidMaterial()
    mat.SetName("Chain")
    mat.SetDensity(setup[3], "kg/m3")
    mat_name = mat.GetName()

    return {
        "link-length": float(setup[0]) * MILLIMETER_TO_METER,
        "link-width": float(setup[1]) * MILLIMETER_TO_METER,
        "wire-diameter": float(setup[2]) * MILLIMETER_TO_METER,
        "density-link": mat_name,
    }


def create_particle(data, frozen=0):
    p = app.GetStudy().GetParticleCollection().New()
    p.SetShape("custom_fiber")

    if frozen == 1:
        p.SetName("Link Fixed")
        p.SetFlexible(True)
        p.SetTargetNumberOfElements(data["n-elements"])
        p.SetMaterial(data["material"])
    else:
        p.SetName("Link Free")
        p.SetMaterial(data["material"])

    p.ImportCustomFiber(data["file-path"])
    p.SetSizeType("original_size_scale")


def create_custom_input(file_path, particle_name, name):
    custom_input = app.GetStudy().GetInletsOutletsCollection().AddCustomInput()
    custom_input.SetParticle(particle_name)
    custom_input.SetName(name)
    custom_input.SetFilePath(str(file_path))


def link_format(link_data, chain_data, base_dir: Path, frozen=0):
    direction = re.search(r"([X|Y|Z]?)\s", chain_data["chain-direction"]).group(0).replace(" ", "")

    if direction == "X":
        rotation_axis = np.array([0.0, 0.0, 1.0])
        rotation_angle = HALF_ROTATION
    elif direction == "Z":
        rotation_axis = np.array([1.0, 0.0, 0.0])
        rotation_angle = HALF_ROTATION
    else:
        rotation_axis = np.array([0.0, 1.0, 0.0])
        rotation_angle = 0.0

    r = (link_data["link-width"] - link_data["wire-diameter"]) / 2
    h = link_data["link-length"] - link_data["link-width"]

    tol = int(math.radians(DEGREES_IN_SEMICIRCLE) / math.asin(link_data["wire-diameter"] / (2 * r)))
    n_elements = 2 * tol + 2
    theta = DEGREES_IN_SEMICIRCLE / tol
    gap = r - r * math.cos(math.radians(90 / tol))

    file_name = "link_format_frozen.csv" if frozen == 1 else "link_format.csv"
    file_path = base_dir / file_name


    with open(file_path, "w", newline="\n") as fd:
        fd.write("x1,y1,z1,x2,y2,z2,diameter,k_multiplier,frozen\n")

        x, y = r, h + 2 * gap
        x1, y1, z1, x2, y2, z2 = r, 0, 0, x, y, 0
        rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
        fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")

        for i in range(1, tol):
            x_i = r * math.cos(math.radians(i * theta))
            y_i = h + 2 * gap + r * math.sin(math.radians(i * theta))
            x1, y1, z1, x2, y2, z2 = x, y, 0, x_i, y_i, 0
            rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
            fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")
            x, y = x_i, y_i

        x1, y1, z1, x2, y2, z2 = x, y, 0, -r, h + 2 * gap, 0
        rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
        fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")

        x1, y1, z1, x2, y2, z2 = -r, h + 2 * gap, 0, -r, 0, 0
        rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
        fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")

        x, y = -r, 0
        for i in range(1, tol):
            x_i = -r * math.cos(math.radians(i * theta))
            y_i = -r * math.sin(math.radians(i * theta))
            x1, y1, z1, x2, y2, z2 = x, y, 0, x_i, y_i, 0
            rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
            fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")
            x, y = x_i, y_i

        x1, y1, z1, x2, y2, z2 = x, y, 0, r, 0, 0
        rot = rotate(rotation_axis, np.array([x1, y1, z1, x2, y2, z2]), rotation_angle)
        fd.write(f"{rot},{link_data['wire-diameter']},1,{frozen}\n")

    return {
        "file-path": str(file_path),
        "n-elements": n_elements,
        "material": link_data["density-link"],
    }


def create_csv(chain_data, link_data, distribution, base_dir: Path):
    sign = -1 if re.search("-", chain_data["chain-direction"]) else 1
    direction = re.search(r"([X|Y|Z]?)\s", chain_data["chain-direction"]).group(0).replace(" ", "")
    rep_direction = re.search(r"([X|Y|Z]?)\s", chain_data["replication"]).group(0).replace(" ", "")

    s_first = chain_data[direction]
    delta = link_data["link-length"] - LINK_SPACING_MULTIPLIER * link_data["wire-diameter"]

    pos = np.zeros(np.sum(np.array(distribution)))
    ang = np.zeros((pos.shape[0], 1))
    rep = pos.copy()
    release_time = np.zeros((pos.shape[0], 1))

    for i in range(chain_data["number-chains"]):
        start = int(np.sum(distribution[:i]))
        end = start + int(distribution[i])
        pos[start:end] = np.arange(0, distribution[i]) * delta * sign
        ang[start:end, 0] = np.arange(0, distribution[i]) * HALF_ROTATION
        rep[start:end] = np.repeat(i, distribution[i])

    pos_matrix = np.zeros((pos.shape[0], 3))

    if direction == "X":
        rot_array = np.array([1.0, 0.0, 0.0])
        pos_matrix[:, 0] = pos
        ft = 0
    elif direction == "Y":
        rot_array = np.array([0.0, 1.0, 0.0])
        pos_matrix[:, 1] = pos
        ft = 1
    else:
        rot_array = np.array([0.0, 0.0, 1.0])
        pos_matrix[:, 2] = pos
        ft = 2

    if rep_direction == "X":
        pos_matrix[:, 0] = rep * chain_data["distance-replication"]
    elif rep_direction == "Y":
        pos_matrix[:, 1] = rep * chain_data["distance-replication"]
    else:
        pos_matrix[:, 2] = rep * chain_data["distance-replication"]

    pos_matrix_up = pos_matrix.copy()
    pos_matrix_up[:, 0] += chain_data["X"]
    pos_matrix_up[:, 1] += chain_data["Y"]
    pos_matrix_up[:, 2] += chain_data["Z"]

    rot_matrix = np.tile(rot_array, (pos.shape[0], 1))
    data = np.concatenate((pos_matrix_up, rot_matrix, ang, release_time), axis=1)

    header = ["x", "y", "z", "nx", "ny", "nz", "angle", "release"]

    file_path = base_dir / "chain_injection.csv"
    fixed = []
    result = {"file-path": str(file_path)}

    if chain_data["restriction"] != ConstraintType.FREE_FREE.value:
        file_path_frozen = base_dir / "chain_injection_frozen.csv"
        fixed = np.where(pos_matrix_up[:, ft] == s_first)[0]

        if chain_data["restriction"] != ConstraintType.FIXED_FREE.value:
            j = [int(np.sum(distribution[:i]) + distribution[i] - 1) for i in range(chain_data["number-chains"])]
            fixed = np.concatenate((fixed, j), axis=0)

        pd.DataFrame(data[fixed, :]).to_csv(file_path_frozen, header=header, index=False)
        result["file-path-frozen"] = str(file_path_frozen)

    pd.DataFrame(data[np.setdiff1d(np.arange(pos.shape[0]), fixed), :]).to_csv(
        file_path, header=header, index=False
    )

    return result


def chain_position():
    frozenlinks = [0, ConstraintType.FIXED_FREE.value, ConstraintType.FIXED_FIXED.value, ConstraintType.FREE_FREE.value]
    directions = [0, Direction.Y_NEGATIVE.value, Direction.X_POSITIVE.value, Direction.Z_POSITIVE.value, 
                  Direction.X_NEGATIVE.value, Direction.Y_POSITIVE.value, Direction.Z_NEGATIVE.value]
    rep_directions = [0, Direction.Z_POSITIVE.value, Direction.X_POSITIVE.value, Direction.Y_POSITIVE.value, 
                      Direction.X_NEGATIVE.value, Direction.Y_NEGATIVE.value, Direction.Z_NEGATIVE.value]

    fields = [
        ("Number of chains:", 5),
        ("Number of links per chain:", 10),
        ("Same number of links per chain?", True),
        (None, None),
        (None, "Position of the first link"),
        ("X [m]", 0.0),
        ("Y [m]", 0.0),
        ("Z [m]", 0.0),
        (None, None),
        ("Chain direction:", directions),
        (None, None),
        (None, "Set the chain constraints"),
        ("Constraints:", frozenlinks),
        (None, None),
        ("Chain replication:", rep_directions),
        ("Distance between the chains [mm]", 50.0),
        (None, None),
    ]

    chain = show_form(fields, title="Chain setup", comment="Specify the chain parameters")
    if chain is None:
        return None

    chain = [c for c in chain if c is not None and not isinstance(c, str)]
    return {
        "number-chains": int(chain[0]),
        "number-links": int(chain[1]),
        "uniform": chain[2],
        "X": float(chain[3]),
        "Y": float(chain[4]),
        "Z": float(chain[5]),
        "chain-direction": directions[chain[6]],
        "restriction": frozenlinks[chain[7]],
        "replication": rep_directions[chain[8]],
        "distance-replication": float(chain[9]) * MILLIMETER_TO_METER,
    }


def chain_distribution(number_chains, number_links):
    fields = [(f"Chain {i + 1}", number_links) for i in range(number_chains)]
    chain_data = show_form(fields, title="Chain Distribution", comment="Input the number of links for each chain")
    return np.array(chain_data, dtype="int32")


if __name__ == "__main__":
    pass
else:

    base_dir = Path.cwd()

    link_data = link_geo()
    chain_data = chain_position()

    if link_data is None or chain_data is None:
        pass
    else:
        if not chain_data["uniform"]:
            distribution = chain_distribution(chain_data["number-chains"], chain_data["number-links"])
        else:
            distribution = [chain_data["number-links"] for _ in range(chain_data["number-chains"])]

        chain_link_free = link_format(link_data, chain_data, base_dir=base_dir)
        create_particle(chain_link_free)

        if chain_data["restriction"] != ConstraintType.FREE_FREE.value:
            chain_link_frozen = link_format(link_data, chain_data, base_dir=base_dir, frozen=1)
            create_particle(chain_link_frozen, frozen=1)

        result = create_csv(chain_data, link_data, distribution, base_dir=base_dir)

        create_custom_input(Path(result["file-path"]), "Link Free", "Injection Free")
        if "file-path-frozen" in result:
            create_custom_input(Path(result["file-path-frozen"]), "Link Fixed", "Injection Fixed")