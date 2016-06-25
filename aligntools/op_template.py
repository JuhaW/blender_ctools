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


EPS = 1e-5


__all__ = (
    'orientation_enum_items',
    '_OperatorTemplate',
    '_OperatorTemplateTranslation',
    '_OperatorTemplateGroup',
    'EPS',
)


def orientation_enum_items():
    orientations = ['GLOBAL', 'LOCAL', 'GRID', 'NORMAL', 'GIMBAL', 'VIEW',
                    'CUSTOM', 'REGION', 'MANIPULATOR', 'PLANE', 'AXIS']
    p = bpy.types.SpaceView3D.bl_rna.properties['transform_orientation']
    if 'GRID' not in p.enum_items:
        orientations.remove('GRID')
    return [(name, name.title(), '') for name in orientations]


class _OperatorTemplate(vaop.OperatorTemplate):
    def __init__(self):
        super().__init__()
        tool_data.operator = self
        memoize.clear()

    def draw_box(self, layout, title, attr):
        layout = layout.column(align=True)
        column_title = layout.column(align=True)
        row = column_title.row(align=True)
        if attr:
            sub = row.row()
            if getattr(self, attr):
                icon = 'DISCLOSURE_TRI_DOWN'
            else:
                icon = 'DISCLOSURE_TRI_RIGHT'
            sub.prop(self, attr, text='', icon=icon, emboss=False)
        sub = row.row()
        sub.label(title)

        box = layout.box()
        return box


class _OperatorTemplateTranslation(_OperatorTemplate):
    space = bpy.props.EnumProperty(
        name='Space',
        items=orientation_enum_items(),
        default='GLOBAL',
    )
    axis = bpy.props.EnumProperty(
        name='Axis',
        items=(('X', 'X', ''),
               ('Y', 'Y', ''),
               ('Z', 'Z', '')),
        default='X',
    )

    # この二つは_OperatorTemplateGroupでも定義される
    object_data = bpy.props.EnumProperty(
        name='Object Data',
        description='Object data type (only object mode)',
        items=(('ORIGIN', 'Object Origin', 'Object origin'),
               ('MESH', 'Mesh', 'Mesh data'),
               ('DM_PREVIEW', 'Derived Mesh Preview',
                'Derived mesh (apply modifiers)'),
               ('DM_RENDER', 'Derived Mesh Render',
                'Derived mesh (apply modifiers)')),
        default='ORIGIN',
    )
    individual_orientation = bpy.props.BoolProperty(
        name='Individual Orientation',
        default=False
    )

    show_expand_axis = bpy.props.BoolProperty()


class _OperatorTemplateGroup(_OperatorTemplate):
    def __init__(self):
        super().__init__()
        self.groups = None

    def _group_type_get(self, context):
        items = [
            ['NONE', 'None', '', 'NONE'],
            ['ALL', 'All', '', 'NONE'],
        ]
        if context.mode == 'OBJECT':
            items.append(['PARENT_CHILD', 'Parent-Child', '', 'NONE'])
            items.append(['GROUP', 'Object Group', '', 'NONE'])
        elif context.mode == 'EDIT_MESH':
            items.append(['LINKED', 'Linked', 'Connected with edge', 'NONE'])
            items.append(['GROUP', 'Vertex Group', '', 'NONE'])
        else:
            items.append(['BONE', 'Bone', '', 'NONE'])
            items.append(['PARENT_CHILD', 'Parent-Child', '', 'NONE'])
            items.append(['PARENT_CHILD_CONNECTED', 'Parent-Child (Connected)',
                          '', 'NONE'])
            items.append(['GROUP', 'Bone Group', '', 'NONE'])
        items.append(['BOUNDING_BOX', 'Bounding Box', '', 'NONE'])
        items = [tuple(item + [i]) for i, item in enumerate(items)]
        self.__class__._group_type_get_cache = items
        return items

    group_type = bpy.props.EnumProperty(
        name='Group Type',
        items=_group_type_get)
    object_data = bpy.props.EnumProperty(
        name='Object Data',
        description='Object data type (only object mode)',
        items=(('ORIGIN', 'Object Origin', 'Object origin'),
               ('MESH', 'Mesh', 'Mesh data'),
               ('DM_PREVIEW', 'Derived Mesh Preview',
                'Derived mesh (apply modifiers)'),
               ('DM_RENDER', 'Derived Mesh Render',
                'Derived mesh (apply modifiers)')),
        default='ORIGIN',
    )
    individual_orientation = bpy.props.BoolProperty(
        name='Individual Orientation',
        default=False)
    bb_type = bpy.props.EnumProperty(
        name='Group BB Type',
        description='Bounding Box Type',
        items=(('AABB', 'AABB', 'Axis Aligned Bounding Box 軸並行境界ボックス'),
               ('OBB', 'OBB', 'Oriented Bounding Box 有向境界ボックス')),
        default='AABB')
    bb_space = bpy.props.EnumProperty(
        name='Bounding Box Space',
        items=[(name, name.title(), '') for name in
               ['GLOBAL', 'LOCAL', 'GRID', 'NORMAL', 'GIMBAL', 'VIEW',
                'CUSTOM', 'REGION', 'MANIPULATOR', 'PLANE']],
        default='GLOBAL')
    shrink_fatten = bpy.props.FloatProperty(
        name='Group BB Shrink Fatten',
        description='BB判定の際にBBを拡大する量',
        default=0.0)
    pivot_point = bpy.props.EnumProperty(
        name='Group Pivot Point',
        items=(('CENTER', 'Center', 'Bounding box center'),
               ('MEDIAN', 'Median', ''),
               ('ACTIVE', 'Active', 'only group_type==ALL'),
               ('CURSOR', '3D Cursor', 'only group_type==ALL'),
               ('ROOT', 'Root', ''),
               ('HEAD_TAIL', 'Head / Tail', 'Bone / PoseBone'),
               ('BOUNDING_BOX', 'Bounding Box', 'center of bounding box'),
               ('TARGET', 'Target', '')),
        default='CENTER')
    pivot_point_target_distance = bpy.props.EnumProperty(
        name='Target Pivot Point Distance',
        items=(('CLOSEST', 'Closest', ''),
               ('MIN', 'Min', ''),
               ('CENTER', 'Center', ''),
               ('MAX', 'Max', '')),
        default='CLOSEST')
    pivot_point_bb_position = bpy.props.FloatVectorProperty(
        name='Bounding Box Pivot Position',
        description='-1:min, 0:center, 1:max',
        default=(0, 0, 0), subtype='XYZ', size=3)
    head_tail = bpy.props.FloatProperty(
        name='Head/Tail',
        description='Target along length of bone: Head=0, Tail=1',
        default=0.0,
        precision=3,
        soft_min=0.0,
        soft_max=1.0,
        subtype='FACTOR')

    show_expand_pivot = bpy.props.BoolProperty()
    show_expand_grouping = bpy.props.BoolProperty()

    def make_groups(self, context, **kwargs):
        """
        :rtype: Groups
        """
        kw = {}
        kw['group_type'] = GroupType.get(self.group_type)
        kw['object_data'] = ObjectData.get(self.object_data)
        kw['bb_type'] = BoundingBox.get(self.bb_type)
        kw['bb_space'] = self.bb_space
        for attr in ('shrink_fatten', 'individual_orientation'):
            kw[attr] = getattr(self, attr)
        if kwargs:
            kw.update(kwargs)
        if self.groups is None:
            groups = self.groups = grouping.context_groups(context, **kw)
        else:
            groups = self.groups
            for attr, value in kw.items():
                setattr(groups, attr, value)
            groups.update(context)
        # calc pivot
        for group in groups:
            group.pivot = group.calc_pivot(
                context, self.pivot_point, self.pivot_point_bb_position,
                self.head_tail, tool_data.plane,
                self.pivot_point_target_distance, fallback=None)
        return groups

    def draw_group_boxes(self, context, layout):
        # Object Data Source
        if context.mode == 'OBJECT':
            # Axis
            box = self.draw_box(layout, 'Data Source', '')
            column = box.column(align=True)
            self.draw_property('object_data', column, text='')

        # Pivot
        box = self.draw_box(layout, 'Pivot', 'show_expand_pivot')
        column = box.column()
        self.draw_property('pivot_point', column, text='')
        if self.show_expand_pivot:
            if self.pivot_point == 'BOUNDING_BOX':
                self.draw_property('pivot_point_bb_position', column)
            elif self.pivot_point in {'ROOT', 'HEAD_TAIL'}:
                self.draw_property('head_tail', column)
            elif self.pivot_point == 'TARGET':
                self.draw_property('pivot_point_target_distance', column)

        # Grouping
        box = self.draw_box(layout, 'Grouping',
                            'show_expand_grouping')
        column = box.column()
        self.draw_property('group_type', column, text='')
        if self.show_expand_grouping:
            if (self.group_type == 'BOUNDING_BOX' or
                        self.pivot_point in {'CENTER', 'BOUNDING_BOX'}):
                self.draw_property('bb_type', column)
                self.draw_property('bb_space', column)
                self.draw_property('shrink_fatten', column)

