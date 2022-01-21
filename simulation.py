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
_sim_node_sig = [("Reset", 'BOOLEAN'), ("Step", 'INT')]


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


def check_sim_modifier(obj, report):
    return _find_modifier(obj, _sim_node_sig, report)


# Copies the depsgraph result to bpy.data
# and replaces the object mesh for the next iteration.
def _copy_mesh_result_to_data(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    # mesh_eval = obj_eval.data
    mesh_new = bpy.data.meshes.new_from_object(obj_eval, preserve_all_data_layers=True, depsgraph=depsgraph)
    mesh_old = obj.data
    obj.data = mesh_new
    bpy.data.meshes.remove(mesh_old)


# If true, the modifier result is copied to mesh data right after each step update.
_show_next_step_result = False

# Prepare modifier and update geometry
def sim_modifier_pre_step(obj, step, report):
    mod_show = None

    mod = _find_modifier(obj, _sim_node_sig)
    if not mod:
        return

    if not _show_next_step_result:
        # Get last modifier result and copy it back to mesh data
        _copy_mesh_result_to_data(obj)

    # Disable modifier while changing inputs
    mod_show = (mod.show_render, mod.show_viewport)
    mod.show_render = False
    mod.show_viewport = False

    _set_geonodes_input(mod, "Step", step)
    _set_geonodes_input(mod, "Reset", step == 0)

    # Re-enable only after all inputs have been set to avoid recomputing the modifier.
    mod.show_render, mod.show_viewport = mod_show
    mod_show = None


# Store geometry result
def sim_modifier_post_step(obj, report):
    if _show_next_step_result:
        _copy_mesh_result_to_data(obj)
