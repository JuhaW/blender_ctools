# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import itertools

import bpy
import bpy.utils.previews

from mathutils import Matrix

from . import funcs
from . import memocoords
from . import tooldata
from .va import manipulatormatrix
from .op_template import *


tool_data = tooldata.tool_data
memoize = tool_data.memoize


class OperatorManipulatorSetA(_OperatorTemplate, bpy.types.Operator):
    bl_idname = 'at.manipulator_set_a'
    bl_label = 'Set Manipulator A'
    bl_description = 'Set manipulator A'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return manipulatormatrix.ManipulatorMatrix.poll(context)

    def execute(self, context):
        mmat = memocoords.manipulator_matrix(context)
        mmat.update(context, view_only=True, cursor_only=True)
        tool_data.matrix_a = Matrix(mmat)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class OperatorManipulatorSetB(_OperatorTemplate, bpy.types.Operator):
    bl_idname = 'at.manipulator_set_b'
    bl_label = 'Set Manipulator B'
    bl_description = 'Set manipulator B'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return manipulatormatrix.ManipulatorMatrix.poll(context)

    def execute(self, context):
        mmat = memocoords.manipulator_matrix(context)
        mmat.update(context, view_only=True, cursor_only=True)
        tool_data.matrix_b = Matrix(mmat)
        return {'FINISHED'}


class OperatorManipulatorAtoB(_OperatorTemplateGroup, bpy.types.Operator):
    bl_idname = 'at.manipulator_a_to_b'
    bl_label = 'Manipulator A to B'
    bl_description = 'Apply manipulator difference'
    bl_options = {'REGISTER', 'UNDO'}

    space = bpy.props.EnumProperty(
        name='Space',
        items=orientation_enum_items(),
        default='GLOBAL')
    mode = bpy.props.EnumProperty(
        name='Mode',
        items=(('TRANSLATE', 'Translate', ''),
               ('ROTATE', 'Rotate', ''),
               ('ROTATE_RESIZE', 'Rotate & Resize', 'Apply matrix 3x3'),
               ('ALL', 'All', '')),
        default='TRANSLATE')

    # influence = bpy.props.FloatProperty(
    #     name='Influence',
    #     default=1.0,
    #     step=1,
    #     precision=3,
    #     soft_min=0.0,
    #     soft_max=1.0,
    #     subtype='NONE'
    # )

    show_expand_transform = bpy.props.BoolProperty()
    # show_expand_others = bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'EDIT_MESH', 'EDIT_ARMATURE', 'POSE'}

    def execute(self, context):
        bpy.ops.at.fix()
        memocoords.cache_init(context)
        groups = self.make_groups(context)
        if not groups:
            return {'FINISHED'}

        a = tool_data.matrix_a
        b = tool_data.matrix_b
        # aからの相対的な行列を求める。 (inv_a * b) = c * (inv_a * a)
        c = a.inverted() * b
        if self.mode == 'TRANSLATE':
            v1 = a.to_translation()
            v2 = b.to_translation()
            matrix = Matrix.Translation(v2 - v1)
        elif self.mode == 'ROTATE':
            matrix = c.normalized().to_quaternion().to_matrix().to_4x4()
        elif self.mode == 'ROTATE_RESIZE':
            matrix = c.copy()
            matrix.col[3][:] = [0, 0, 0, 1]
        else:
            matrix = c.copy()

        matrices = {}
        for group in groups:
            omat = group.get_orientation(context, self.space)
            if not omat:
                matrices[group] = Matrix.Identity(4)
                continue
            m1 = Matrix.Translation(-group.pivot)
            m2 = Matrix.Translation(group.pivot)
            omat = omat.to_4x4()
            oimat = omat.inverted()
            matrices[group] = m2 * omat * matrix * oimat * m1
        groups.transform(context, matrices,
                         reverse=self.individual_orientation)

        if context.mode == 'OBJECT':
            objects = [bpy.data.objects[name]
                       for name in itertools.chain.from_iterable(groups)]
        else:
            objects = [context.active_object]
        funcs.update_tag(context, objects)

        return {'FINISHED'}

    def draw(self, context):
        # Transform
        box = self.draw_box(self.layout, 'Transform', 'show_expand_transform')
        column = box.column()
        self.draw_property('mode', column)
        self.draw_property('space', column)
        if self.show_expand_transform:
            self.draw_property('individual_orientation', column)

        # Groups
        self.draw_group_boxes(context, self.layout)

        # # Others
        # # box = self.draw_box(self.layout, 'Others', 'show_expand_others')
        # box = self.draw_box(self.layout, 'Others', '')
        # column = box.column()
        # self.draw_property('influence', column)


classes = [
    OperatorManipulatorSetA,
    OperatorManipulatorSetB,
    OperatorManipulatorAtoB
]
