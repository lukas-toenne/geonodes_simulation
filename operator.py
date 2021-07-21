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


# GN modifier uses socket identifiers as input names,
# which are rather arbitrary.
# This util function provides lookup with meaningful names.
def get_geonodes_input(mod, name):
    identifier = mod.node_group.inputs[name].identifier
    return mod[identifier]
def set_geonodes_input(mod, name, value):
    identifier = mod.node_group.inputs[name].identifier
    mod[identifier] = value


# Signatures expected on modifier types
sim_node_sig = [("Input", 'OBJECT'), ("Reset", 'BOOLEAN'), ("Step", 'INT')]
copy_geo_sig = [("Input", 'OBJECT')]


# Returns true if the node group signature matches
def check_nodes_sig(node_group, sig, report=None):
    for input_name, input_type in sig:
        node_input = node_group.inputs.get(input_name, None)
        if node_input is None:
            if report is not None:
                report("Could not find node group input {}".format(input_name))
            return False
        if node_input.type != input_type:
            if report is not None:
                report("Node group input {} has type {}, expected type {}".format(input_name, node_input.type, input_type))
            return False
    return True


def find_modifier(obj, sig, report=None):
    for mod in obj.modifiers:
        if mod.type=='NODES' and mod.node_group and check_nodes_sig(mod.node_group, sig, report):
            return mod


def get_swap_chain(obj):
    swap_chain_coll = bpy.data.collections.get("__swap_chain", None)
    if swap_chain_coll is None:
        swap_chain_coll = bpy.data.collections.new("__swap_chain")
        bpy.context.scene.collection.children.link(swap_chain_coll)
        swap_chain_coll.hide_render = True
        layer_swap_chain = bpy.context.view_layer.layer_collection.children.get(swap_chain_coll.name, None)
        if layer_swap_chain:
            layer_swap_chain.hide_viewport = True

    swap_chain = list()
    for i in range(2):
        name = "{}.__swap_chain_{}".format(obj.name, i + 1)
        swap_obj = swap_chain_coll.objects.get(name, None)
        if swap_obj is None:
            mesh = bpy.data.meshes.get(name, None)
            if mesh is None:
                mesh = bpy.data.meshes.new(name)
            swap_obj = bpy.data.objects.new(name, mesh)
            swap_chain_coll.objects.link(swap_obj)
        swap_chain.append(swap_obj)

    return swap_chain


def find_next_swap_chain_object(mod):
    swap_chain = get_swap_chain(mod.id_data)
    swap_chain_next = swap_chain[1:] + [swap_chain[0]]

    cur_obj = get_geonodes_input(mod, "Input")
    for obj, next_obj in zip(swap_chain, swap_chain_next):
        if obj == cur_obj:
            return next_obj
    # No object from swap chain set, select arbitrary
    return swap_chain[0]


class GeoNodesSimSettings(bpy.types.PropertyGroup):
    enabled : BoolProperty(
        name="Enabled",
        default=False,
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

    def draw(self, context, layout):
        layout.prop(self, "step_count")
        row = layout.row()
        row.prop(self, "use_view_update")
        sub = row.column()
        sub.active = self.use_view_update
        sub.prop(self, "view_update_steps")
        sub.prop(self, "view_update_interval")


class GeoNodesSimBase():
    @classmethod
    def poll(cls, context):
        return context.collection is not None

    def pre_step(self, mod, step):
        # Disable modifier while changing inputs
        self._mod_show = (mod.show_render, mod.show_viewport)
        mod.show_render = False
        mod.show_viewport = False

        # Swap objects for the prev/next iteration
        next_obj = find_next_swap_chain_object(mod)
        set_geonodes_input(mod, "Input", next_obj)
        set_geonodes_input(mod, "Step", step)
        set_geonodes_input(mod, "Reset", step == 0)

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

        new_geo_nodes = copy_geo_mod.node_group
        copy_geo_mod.node_group = copy_geo_nodes
        # New GeometryNodes modifier adds an empty node group, polluting the bpy.data.node_groups collection over time.
        if new_geo_nodes:
            bpy.data.node_groups.remove(new_geo_nodes)

        set_geonodes_input(copy_geo_mod, "Input", mod.id_data)

        override = bpy.context.copy()
        override['object'] = next_obj
        override['active_object'] = next_obj
        override['selected_objects'] = [next_obj]
        bpy.ops.object.modifier_apply(override, modifier=copy_geo_mod.name)


class GeoNodesReset(GeoNodesSimBase, bpy.types.Operator):
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


class GeoNodesStep(GeoNodesSimBase, bpy.types.Operator):
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


class GeoNodesRun(GeoNodesSimBase, bpy.types.Operator):
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

        col.operator("geonodes.sim_reset")
        col.operator("geonodes.sim_step")

        settings.draw(context, col)
        col.operator("geonodes.sim_run")


def register():
    bpy.utils.register_class(GeoNodesReset)
    bpy.utils.register_class(GeoNodesStep)
    bpy.utils.register_class(GeoNodesRun)
    bpy.utils.register_class(GeoNodesSimPanel)
    bpy.utils.register_class(GeoNodesSimSettings)
    bpy.types.Collection.geo_nodes_sim_settings = PointerProperty(type=GeoNodesSimSettings)


def unregister():
    bpy.utils.unregister_class(GeoNodesReset)
    bpy.utils.unregister_class(GeoNodesStep)
    bpy.utils.unregister_class(GeoNodesRun)
    bpy.utils.unregister_class(GeoNodesSimPanel)
    del bpy.types.Collection.geo_nodes_sim_settings
    bpy.utils.unregister_class(GeoNodesSimSettings)
