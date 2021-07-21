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

from .operator import 


class GeoNodesSimBase():
    @classmethod
    def poll(cls, context):
        return hasattr(context, "modifier")

    def pre_step(self, mod, step):
        # Disable modifier while changing inputs
        self._mod_show = (mod.show_render, mod.show_viewport)
        mod.show_render = False
        mod.show_viewport = False

        # Swap objects for the prev/next iteration
        next_obj = find_next_swap_chain_object(mod)
        set_geonodes_input(mod, "Input", next_obj)

        set_geonodes_input(mod, "Step", step)

    def step(self, mod):
        # Re-enable only after all inputs have been set to avoid recomputing the modifier.
        mod.show_render, mod.show_viewport = self._mod_show
        del self._mod_show

    def post_step(self, mod):
        copy_geo_nodes = bpy.data.node_groups['CopyGeometry']
        if not copy_geo_nodes:
            self.report('ERROR_INVALID_CONTEXT', "Could not find node group 'CopyGeometry'")
            return
        if not check_nodes_sig(copy_geo_nodes, copy_geo_sig, report=self.report):
            return

        # Order here is important for performance and to avoid dependency cycles:
        # 1. Add a "CopyGeometry" modifier to the swap chain output object
        # 2  Set "Input" to the simulation object to copy the result of the current frame.
        # 3. Apply the CopyGeometry modifier to store the result in the swap chain output object.
        next_obj = find_next_swap_chain_object(mod)
        copy_geo_mod = next_obj.modifiers.new(type='NODES', name="Copy")
        copy_geo_mod.node_group = copy_geo_nodes
        set_geonodes_input(copy_geo_mod, "Input", mod.id_data)

        override = bpy.context.copy()
        override['object'] = next_obj
        override['active_object'] = next_obj
        override['selected_objects'] = [next_obj]
        bpy.ops.object.modifier_apply(override, modifier=copy_geo_mod.name)

    def load_erosion_map(self, step):
        # img = bpy.data.images['Erosion']
        # img.filepath = "D:/BlenderCache/GNErosion/step{}.exr".format(step)
        # img.reload()
        pass

    def render_height_map(self, step):
        # print("Render Height Map {}".format(step))
        # scene = bpy.data.scenes["HeightMapRender"]
        # scene.render.filepath = "D:/BlenderCache/GNErosion/step{}.exr".format(step)
        # scene.render.image_settings.file_format = 'OPEN_EXR'
        # bpy.ops.render.render(animation=False, write_still=True, use_viewport=False, scene=scene.name)

        # self.load_erosion_map(step)
        pass

    def render_erosion(self, step):
        # print("Render Erosion {}".format(step))
        # scene = bpy.data.scenes["ErosionRender"]
        # scene.render.filepath = "D:/BlenderCache/GNErosion/step{}.exr".format(step)
        # scene.render.image_settings.file_format = 'OPEN_EXR'
        # bpy.ops.render.render(animation=False, write_still=True, use_viewport=False, scene=scene.name)

        # self.load_erosion_map(step)
        pass


class GeoNodesReset(GeoNodesSimBase, bpy.types.Operator):
    """Reset geometry"""
    bl_idname = "geonodes.sim_reset"
    bl_label = "Reset"

    def execute(self, context):
        obj = context.object
        mod = context.modifier
        settings = obj.geo_nodes_sim_settings

        self.render_height_map(0)

        self.pre_step(mod, 0)
        set_geonodes_input(mod, "Reset", True)
        self.step(mod)
        self.post_step(mod)

        settings.next_step = 1

        return {'FINISHED'}


class GeoNodesStep(GeoNodesSimBase, bpy.types.Operator):
    """Advance geometry nodes simulation by one step"""
    bl_idname = "geonodes.sim_step"
    bl_label = "Step"

    def execute(self, context):
        obj = context.object
        mod = context.modifier
        settings = obj.geo_nodes_sim_settings

        self.pre_step(mod, settings.next_step)
        set_geonodes_input(mod, "Reset", False)
        self.step(mod)
        self.post_step(mod)

        self.render_erosion(settings.next_step)

        settings.next_step += 1

        return {'FINISHED'}


class GeoNodesRun(GeoNodesSimBase, bpy.types.Operator):
    """Compute geometry nodes simulation"""
    bl_idname = "geonodes.sim_run"
    bl_label = "Run"

    _timer = None
    _obj = None
    _mod = None

    def run_steps(self, obj, mod):
        settings = obj.geo_nodes_sim_settings

        step_start = settings.next_step
        if settings.use_view_update:
            step_end = min(settings.step_count, step_start + settings.view_update_steps)
        else:
            step_end = settings.step_count

        print("Substeps: {}:{}".format(step_start, step_end))
        for step in range(step_start, step_end):
            # print("  step " + str(step))
            self.pre_step(mod, step)
            set_geonodes_input(mod, "Reset", step == 0)
            self.step(mod)
            self.post_step(mod)

            self.render_erosion(step)

            settings.next_step = step + 1

        return {'RUNNING_MODAL'} if step_end < settings.step_count else {'FINISHED'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            return self.run_steps(self._obj, self._mod)

        return {'PASS_THROUGH'}

    def execute(self, context):
        obj = context.object
        mod = context.modifier
        settings = obj.geo_nodes_sim_settings

        settings.next_step = 0

        if settings.use_view_update:
            wm = context.window_manager
            self._timer = wm.event_timer_add(settings.view_update_interval, window=context.window)
            wm.modal_handler_add(self)

            self._obj = obj
            self._mod = mod
            return self.run_steps(obj, mod)
        else:
            return self.run_steps(obj, mod)

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self._timer = None
        self._obj = None
        self._mod = None


class GeoNodesSimPanel(bpy.types.Panel):
    """Panel for controlling geometry nodes simulation"""
    bl_label = "Geometry Nodes Simulation"
    bl_idname = "OBJECT_PT_geometry_nodes_simulation"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    
    @classmethod
    def poll(cls, context):
        if context.object is None:
            return False
        if not find_modifier(context.object, sim_node_sig):
            return False
        return True

    def draw(self, context):
        mod = find_modifier(context.object, sim_node_sig, report=print)
        layout = self.layout
        layout.context_pointer_set("modifier", mod)

        layout.operator("geonodes.sim_reset")
        layout.operator("geonodes.sim_step")

        context.object.geo_nodes_sim_settings.draw(context, layout)
        layout.operator("geonodes.sim_run")


def register():
    bpy.utils.register_class(GeoNodesReset)
    bpy.utils.register_class(GeoNodesStep)
    bpy.utils.register_class(GeoNodesRun)
    bpy.utils.register_class(GeoNodesSimPanel)
    bpy.utils.register_class(GeoNodesSimSettings)
    bpy.types.Object.geo_nodes_sim_settings = PointerProperty(type=GeoNodesSimSettings)


def unregister():
    bpy.utils.unregister_class(GeoNodesReset)
    bpy.utils.unregister_class(GeoNodesStep)
    bpy.utils.unregister_class(GeoNodesRun)
    bpy.utils.unregister_class(GeoNodesSimPanel)
    del bpy.types.Object.geo_nodes_sim_settings
    bpy.utils.unregister_class(GeoNodesSimSettings)
