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


import inspect

import bpy

from . import drawnearest
from . import lockcoords
from . import lockcursor3d
from . import mousegesture
from . import overwrite_builtin_images
from . import quadview_move
from . import regionruler
from . import screencastkeys
from . import updatetag


bl_info = {
    'name': 'CUtils',
    'author': 'chromoly',
    'version': (1, 0),
    'blender': (2, 76, 0),
    'location': '',
    'description': '',
    'warning': '',
    'wiki_url': '',
    'category': 'User Interface'
}


sub_modules = [
    drawnearest,
    lockcoords,
    lockcursor3d,
    mousegesture,
    overwrite_builtin_images,
    quadview_move,
    regionruler,
    screencastkeys,
    updatetag,
]


"""
サブモジュールでAddonPreferenceを使用する場合

class RegionRulerPreferences(
    @classmethod
    def get_prefs(cls):
        if '.' in __package__:
            import importlib
            pkg, name = __package__.split('.')
            mod = importlib.import_module(pkg)
            return mod.get_addon_preferences(name)
        else:
            context = bpy.context
            return context.user_preferences.addons[__package__].preferences

    @classmethod
    def register(cls):
        # bpy.utils.register_class(cls)の際に実行される
        if '.' in __package__:
            cls.get_prefs()

"""


def _get_pref_class(mod):
    for obj in vars(mod).values():
        if inspect.isclass(obj) and issubclass(obj, bpy.types.PropertyGroup):
            if hasattr(obj, 'bl_idname') and obj.bl_idname == mod.__package__:
                return obj


def get_addon_preferences(name=''):
    """登録と取得"""
    prefs = bpy.context.user_preferences.addons[__package__].preferences
    if name:
        if not hasattr(prefs, name):
            for mod in sub_modules:
                if mod.__package__.split('.')[-1] == name:
                    cls = _get_pref_class(mod)
                    if cls:
                        prop = bpy.props.PointerProperty(type=cls)
                        setattr(CToolsPreferences, name, prop)
                        bpy.utils.unregister_class(CToolsPreferences)
                        bpy.utils.register_class(CToolsPreferences)
        return getattr(prefs, name, None)
    else:
        return prefs


def register_submodule(mod):
    if not hasattr(mod, '__addon_enabled__'):
        mod.__addon_enabled__ = False
    if not mod.__addon_enabled__:
        mod.register()
        mod.__addon_enabled__ = True


def unregister_submodule(mod):
    if mod.__addon_enabled__:
        mod.unregister()
        mod.__addon_enabled__ = False

        prefs = get_addon_preferences()
        name = mod.__package__.split('.')[-1]
        if hasattr(CToolsPreferences, name):
            delattr(CToolsPreferences, name)
            bpy.utils.unregister_class(CToolsPreferences)
            bpy.utils.register_class(CToolsPreferences)
            if name in prefs:
                del prefs[name]


class CToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # def __getattribute__(self, item):
    #     # test
    #     return super().__getattribute__(item)

    def draw(self, context):
        layout = self.layout
        """:type: bpy.types.UILayout"""

        for mod in sub_modules:
            info = mod.bl_info
            column = layout.column(align=True)
            box = column.box()
            mod_name = mod.__package__.split('.')[-1]

            # 一段目
            expand = getattr(self, 'show_expanded_' + mod_name)
            icon = 'TRIA_DOWN' if expand else 'TRIA_RIGHT'
            col = box.column()  # boxのままだと行間が広い
            row = col.row()
            sub = row.row()
            sub.context_pointer_set('addon_prefs', self)
            sub.alignment = 'LEFT'
            op = sub.operator('wm.context_toggle', text='', icon=icon,
                              emboss=False)
            op.data_path = 'addon_prefs.show_expanded_' + mod_name
            sub.label(info['name'])
            sub = row.row()
            sub.alignment = 'RIGHT'
            if info.get('warning'):
                sub.label('', icon='ERROR')
            sub.prop(self, 'use_' + mod_name, text='')
            # 二段目
            if expand:
                # col = box.column()  # boxのままだと行間が広い
                # 参考: space_userpref.py
                if info.get('description'):
                    split = col.row().split(percentage=0.15)
                    split.label('Description:')
                    split.label(info['description'])
                if info.get('location'):
                    split = col.row().split(percentage=0.15)
                    split.label('Location:')
                    split.label(info['location'])
                if info.get('author') and info.get('author') != 'chromoly':
                    split = col.row().split(percentage=0.15)
                    split.label('Author:')
                    split.label(info['author'])
                if info.get('version'):
                    split = col.row().split(percentage=0.15)
                    split.label('Version:')
                    split.label('.'.join(str(x) for x in info['version']),
                                translate=False)
                if info.get('warning'):
                    split = col.row().split(percentage=0.15)
                    split.label('Warning:')
                    split.label('  ' + info['warning'], icon='ERROR')

                # 設定値
                if getattr(self, 'use_' + mod_name):
                    prefs = get_addon_preferences(mod_name)
                    if prefs and hasattr(prefs, 'draw'):
                        box = column.box()
                        prefs.layout = box
                        prefs.draw(context)
                        del prefs.layout

for mod in sub_modules:
    info = mod.bl_info
    mod_name = mod.__package__.split('.')[-1]

    def gen_update(mod):
        def update(self, context):
            if getattr(self, 'use_' + mod.__package__.split('.')[-1]):
                if not mod.__addon_enabled__:
                    register_submodule(mod)
            else:
                if mod.__addon_enabled__:
                    unregister_submodule(mod)
        return update


    prop = bpy.props.BoolProperty(
        name=info['name'],
        description=info.get('description', ''),
        update=gen_update(mod),
    )
    setattr(CToolsPreferences, 'use_' + mod_name, prop)
    prop = bpy.props.BoolProperty()
    setattr(CToolsPreferences, 'show_expanded_' + mod_name, prop)


classes = [
    CToolsPreferences,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = get_addon_preferences()
    for mod in sub_modules:
        if not hasattr(mod, '__addon_enabled__'):
            mod.__addon_enabled__ = False
        name = mod.__package__.split('.')[-1]
        if getattr(prefs, 'use_' + name):
            register_submodule(mod)


def unregister():
    prefs = get_addon_preferences()
    for mod in sub_modules:
        if getattr(prefs, 'use_' + mod.__package__.split('.')[-1]):
            unregister_submodule(mod)

    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
