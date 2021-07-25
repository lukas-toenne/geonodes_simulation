# MIT License
#
# Copyright (c) 2021 Lukas Toenne
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

bl_info = {
    "name": "Geometry Nodes Simulation",
    "author": "Lukas Toenne",
    "version": (0, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Object > Modifiers",
    "description": "Integrate geometry nodes into iterative simulations",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Mesh",
}

import bpy
from . import operator, settings, simulation, ui

if "bpy" in locals():
    import importlib
    importlib.reload(simulation)
    importlib.reload(settings)
    importlib.reload(operator)
    importlib.reload(ui)


def register():
    operator.register()
    settings.register()
    ui.register()

def unregister():
    operator.unregister()
    settings.unregister()
    ui.unregister()

if __name__ == "__main__":
    register()
