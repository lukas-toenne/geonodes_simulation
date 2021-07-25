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
from .simulation import find_modifier, sim_node_sig


class GeoNodesSimPanel(bpy.types.Panel):
    """Panel for controlling geometry nodes simulation"""
    bl_label = "Geometry Nodes Simulation"
    bl_idname = "OBJECT_PT_geometry_nodes_simulation"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "collection"

    @classmethod
    def poll(cls, context):
        if context.collection is None:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        coll = context.collection
        settings = coll.geo_nodes_sim_settings

        layout.prop(settings, "enabled")

        col = layout.column()
        col.enabled = settings.enabled

        errors = list()
        def report(message):
            nonlocal errors
            errors.append(message)
        for obj in coll.objects:
            mod = find_modifier(obj, sim_node_sig, report=report)
        for message in errors:
            col.label(text=message, icon='ERROR')

        row = col.row()
        row.prop(settings, "control_mode")

        if settings.control_mode == 'TIMELINE':
            pass
        elif settings.control_mode == 'MANUAL':
            col.operator("geonodes.sim_reset")
            col.operator("geonodes.sim_step")

            col.prop(settings, "step_count")
            row = col.row()
            row.prop(settings, "use_view_update")
            sub = row.column()
            sub.active = settings.use_view_update
            sub.prop(settings, "view_update_steps")
            sub.prop(settings, "view_update_interval")
            col.operator("geonodes.sim_run")


def register():
    bpy.utils.register_class(GeoNodesSimPanel)


def unregister():
    bpy.utils.unregister_class(GeoNodesSimPanel)
