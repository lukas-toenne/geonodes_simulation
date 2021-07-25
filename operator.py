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
from .simulation import GeoNodesSimBase


class GeoNodesSimControlOperator(GeoNodesSimBase):
    @classmethod
    def poll(cls, context):
        coll = context.collection
        if coll is None:
            return False
        settings = coll.geo_nodes_sim_settings
        return settings.enabled and settings.control_mode == 'MANUAL'


class GeoNodesReset(GeoNodesSimControlOperator, bpy.types.Operator):
    """Reset geometry"""
    bl_idname = "geonodes.sim_reset"
    bl_label = "Reset"

    def execute(self, context):
        coll = context.collection
        settings = coll.geo_nodes_sim_settings

        for obj in coll.objects:
            mod = find_modifier(obj, sim_node_sig)
            if mod:
                self.pre_step(mod, 0)
                self.step(mod)
                self.post_step(mod)

        settings.next_step = 1

        return {'FINISHED'}


class GeoNodesStep(GeoNodesSimControlOperator, bpy.types.Operator):
    """Advance geometry nodes simulation by one step"""
    bl_idname = "geonodes.sim_step"
    bl_label = "Step"

    def execute(self, context):
        coll = context.collection
        settings = coll.geo_nodes_sim_settings

        for obj in coll.objects:
            mod = find_modifier(obj, sim_node_sig)
            if mod:
                self.pre_step(mod, settings.next_step)
                self.step(mod)
                self.post_step(mod)

        settings.next_step += 1

        return {'FINISHED'}


class GeoNodesRun(GeoNodesSimControlOperator, bpy.types.Operator):
    """Compute geometry nodes simulation"""
    bl_idname = "geonodes.sim_run"
    bl_label = "Run"

    _timer = None

    def run_steps(self, context):
        coll = context.collection
        settings = coll.geo_nodes_sim_settings

        step_start = settings.next_step
        if settings.use_view_update:
            step_end = min(settings.step_count, step_start + settings.view_update_steps)
        else:
            step_end = settings.step_count

        print("Substeps: {}:{}".format(step_start, step_end))
        for step in range(step_start, step_end):
            for obj in coll.objects:
                mod = find_modifier(obj, sim_node_sig)
                if mod:
                    self.pre_step(mod, step)
                    self.step(mod)
                    self.post_step(mod)

            settings.next_step = step + 1

        return {'RUNNING_MODAL'} if step_end < settings.step_count else {'FINISHED'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            return self.run_steps(context)

        return {'PASS_THROUGH'}

    def execute(self, context):
        coll = context.collection
        settings = coll.geo_nodes_sim_settings

        settings.next_step = 0

        if settings.use_view_update:
            wm = context.window_manager
            self._timer = wm.event_timer_add(settings.view_update_interval, window=context.window)
            wm.modal_handler_add(self)

            return self.run_steps(context)
        else:
            return self.run_steps(context)

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self._timer = None


def register():
    bpy.utils.register_class(GeoNodesReset)
    bpy.utils.register_class(GeoNodesStep)
    bpy.utils.register_class(GeoNodesRun)


def unregister():
    bpy.utils.unregister_class(GeoNodesReset)
    bpy.utils.unregister_class(GeoNodesStep)
    bpy.utils.unregister_class(GeoNodesRun)
