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
from bpy.app.handlers import persistent
from . import simulation


_geonodes_sim_collections = list()


# Non-persistent handler: Gets added by the load_post handler or when settings change.
def frame_change_pre(scene):
    step = scene.frame_current - scene.frame_start
    print("GeoNodes Sim: Frame {}, step {}".format(scene.frame_current, step))
    for coll in _geonodes_sim_collections:
        settings = coll.geo_nodes_sim_settings
        simulation.sim_modifier_pre_step(settings.sim_input, settings.sim_output, step, report=print)

# Non-persistent handler: Gets added by the load_post handler or when settings change.
def frame_change_post(scene):
    for coll in _geonodes_sim_collections:
        settings = coll.geo_nodes_sim_settings
        simulation.sim_modifier_post_step(settings.sim_input, settings.sim_output, report=print)


def update_frame_handler():
    global _geonodes_sim_collections
    _geonodes_sim_collections = [
        coll
        for coll in bpy.data.collections
            if coll.geo_nodes_sim_settings.enabled and coll.geo_nodes_sim_settings.control_mode == 'TIMELINE'
        ]
    if _geonodes_sim_collections:
        print("GeoNodes Sim: Found {} collections in timeline mode, adding frame change handler".format(len(_geonodes_sim_collections)))
        if frame_change_pre not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(frame_change_pre)
        if frame_change_post not in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.append(frame_change_post)
    else:
        print("GeoNodes Sim: No collections in timeline mode, removing frame change handler")
        if frame_change_pre in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.remove(frame_change_pre)
        if frame_change_post in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(frame_change_post)


@persistent
def load_handler(dummy):
    update_frame_handler()


def register():
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    bpy.app.handlers.load_post.remove(load_handler)
