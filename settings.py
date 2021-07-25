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

import bpy
from bpy.props import *


class GeoNodesSimSettings(bpy.types.PropertyGroup):
    enabled : BoolProperty(
        name="Enabled",
        description="Simulate objects with geometry node modifiers in this collection",
        default=False,
        )

    control_mode_items = [
        ('TIMELINE', "Timeline", "Use the timeline to advance the simulation, reset on the start frame"),
        ('MANUAL', "Manual", "Manually advance and reset the simulation"),
    ]
    control_mode : EnumProperty(
        name="Control Mode",
        description="How simulation steps are executed",
        items=control_mode_items,
        default='TIMELINE',
        )

    step_count : IntProperty(
        name="Step Count",
        default=100,
        )

    use_view_update : BoolProperty(
        name="Use View Update",
        default=False,
        )

    view_update_steps : IntProperty(
        name="View Update Steps",
        default=10,
        )

    view_update_interval : FloatProperty(
        name="View Update Interval",
        default=1.0,
        )

    next_step : IntProperty(
        name="Steps Done",
        default=0,
        options={'HIDDEN'},
        )


def register():
    bpy.utils.register_class(GeoNodesSimSettings)
    bpy.types.Collection.geo_nodes_sim_settings = PointerProperty(type=GeoNodesSimSettings)


def unregister():
    del bpy.types.Collection.geo_nodes_sim_settings
    bpy.utils.unregister_class(GeoNodesSimSettings)
