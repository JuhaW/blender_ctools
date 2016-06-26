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


import bpy

from . import grouping
from . import tooldata
from .va import vaoperator as vaop
from .enums import *

tool_data = tooldata.tool_data
memoize = tool_data.memoize


def is_properties_changed(operator, properties):
    for name in op.properties.rna_type.properties.keys():
        if name != 'rna_type' and name in properties:
            pass


class OperatorResetProperties(bpy.types.Operator):
    bl_idname = 'at.reset_properties'
    bl_label = 'Reset Properties'
    bl_description = 'Reset Properties'
    bl_options = {'REGISTER', 'INTERNAL'}

    # UILayout.context_pointer_set('operator', self)とやると
    # context.operatorはselfとは別の型になるので(propertiesとかが無い)不適
    operators = {}

    operator_idname = bpy.props.StringProperty(options={'HIDDEN'})
    # ,で区切る。前後にspaceは可。 e.g. 'mode,axis' or 'mode, axis'
    attributes = bpy.props.StringProperty(options={'HIDDEN'})

    @classmethod
    def set_operator(cls, operator):
        cls.operators[operator.bl_idname] = operator

    def execute(self, context):
        # op = context.operator
        op = self.operators[self.operator_idname]
        attrs = [s.strip(' ') for s in self.attributes.split(',')]
        for name in op.properties.rna_type.properties.keys():
            if name != 'rna_type' and name in attrs:
                op.properties.property_unset(name)
        return {'FINISHED'}


class OperatorResetPropertiesInternal(bpy.types.Operator):
    bl_idname = 'at.reset_operator_properties'
    bl_label = 'Reset Properties'
    bl_options = {'REGISTER', 'INTERNAL'}

    operator = None

    def execute(self, context):
        op = self.operator
        for name in op.properties.rna_type.properties.keys():
            if name != 'rna_type':
                op.properties.property_unset(name)
        return {'FINISHED'}


def reset_operator_properties(operator):
    OperatorResetPropertiesInternal.operator = operator
    bpy.ops.at.reset_operator_properties()


classes = [
    OperatorResetProperties,
    OperatorResetPropertiesInternal
]
