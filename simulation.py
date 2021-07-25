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
def _get_geonodes_input(mod, name):
    identifier = mod.node_group.inputs[name].identifier
    return mod[identifier]
def _set_geonodes_input(mod, name, value):
    identifier = mod.node_group.inputs[name].identifier
    mod[identifier] = value


# Signatures expected on modifier types
_sim_node_sig = [("Input", 'OBJECT'), ("Reset", 'BOOLEAN'), ("Step", 'INT')]
_copy_geo_sig = [("Input", 'OBJECT')]


# Returns true if the node group signature matches
def _check_nodes_sig(node_group, sig, report=None):
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


def _find_modifier(obj, sig, report=None):
    for mod in obj.modifiers:
        if mod.type=='NODES' and mod.node_group and _check_nodes_sig(mod.node_group, sig, report):
            return mod


def _get_swap_chain(obj):
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


def _find_next_swap_chain_object(mod):
    swap_chain = _get_swap_chain(mod.id_data)
    swap_chain_next = swap_chain[1:] + [swap_chain[0]]

    cur_obj = _get_geonodes_input(mod, "Input")
    for obj, next_obj in zip(swap_chain, swap_chain_next):
        if obj == cur_obj:
            return next_obj
    # No object from swap chain set, select arbitrary
    return swap_chain[0]


def check_sim_modifier(obj, report):
    return _find_modifier(obj, _sim_node_sig, report)


# Prepare modifier and update geometry
def sim_modifier_pre_step(obj, step, report):
    mod_show = None

    mod = _find_modifier(obj, _sim_node_sig)
    if not mod:
        return

    # Disable modifier while changing inputs
    mod_show = (mod.show_render, mod.show_viewport)
    mod.show_render = False
    mod.show_viewport = False

    # Swap objects for the prev/next iteration
    next_obj = _find_next_swap_chain_object(mod)
    _set_geonodes_input(mod, "Input", next_obj)
    _set_geonodes_input(mod, "Step", step)
    _set_geonodes_input(mod, "Reset", step == 0)

    # Re-enable only after all inputs have been set to avoid recomputing the modifier.
    mod.show_render, mod.show_viewport = mod_show
    mod_show = None


# Store geometry result
def sim_modifier_post_step(obj, report):
    mod = _find_modifier(obj, _sim_node_sig)
    if not mod:
        return

    copy_geo_nodes = bpy.data.node_groups['CopyGeometry']
    if not copy_geo_nodes:
        report("Could not find node group 'CopyGeometry'")
        return
    if not _check_nodes_sig(copy_geo_nodes, _copy_geo_sig, report=report):
        return

    # Order here is important for performance and to avoid dependency cycles:
    # 1. Add a "CopyGeometry" modifier to the swap chain output object
    # 2  Set "Input" to the simulation object to copy the result of the current frame.
    # 3. Apply the CopyGeometry modifier to store the result in the swap chain output object.
    next_obj = _find_next_swap_chain_object(mod)
    copy_geo_mod = next_obj.modifiers.new(type='NODES', name="Copy")

    new_geo_nodes = copy_geo_mod.node_group
    copy_geo_mod.node_group = copy_geo_nodes
    # New GeometryNodes modifier adds an empty node group, polluting the bpy.data.node_groups collection over time.
    if new_geo_nodes:
        bpy.data.node_groups.remove(new_geo_nodes)

    _set_geonodes_input(copy_geo_mod, "Input", mod.id_data)

    override = bpy.context.copy()
    override['object'] = next_obj
    override['active_object'] = next_obj
    override['selected_objects'] = [next_obj]
    bpy.ops.object.modifier_apply(override, modifier=copy_geo_mod.name)
