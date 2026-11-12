'''
Name for generated for script:
    Custom Color Scale

Script description:
    Customizes the color scale in Rocky

@author: Ansys
@date: 2026-06
@version: 1.0.0
'''

import platform
import os
import importlib

operational_system = platform.system()

if operational_system == 'Windows':
    from win32com.shell import shell
    documents_directory = shell.SHGetFolderPath(0, 0x0005, None, 0)
    bin_directory = os.path.join(
        documents_directory, 'Rocky', 'Scripts', 'colorscaletools')
else:
    documents_directory = os.getenv("HOME")
    bin_directory = os.path.join(
        documents_directory, '.Rocky', 'scripts', 'colorscaletools')

# dynamic import (VS Code auto order wont touch this)
GraphicalUserInterface = importlib.import_module(
    "colorscaletools.application"
).GraphicalUserInterface

GraphicalUserInterface(app)
