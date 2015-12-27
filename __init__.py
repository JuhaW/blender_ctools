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
import traceback
import tempfile
import urllib.request
import zipfile
import os
import shutil
import pathlib

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
    'name': 'CTools',
    'author': 'chromoly',
    'version': (1, 0),
    'blender': (2, 76, 0),
    'location': '',
    'description': 'Addon Collection',
    'warning': '',
    'wiki_url': 'https://github.com/chromoly/blender_ctools',
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


sub_modules.sort(
    key=lambda mod: (mod.bl_info['category'], mod.bl_info['name']))


"""
サブモジュールでAddonPreferenceを使用する場合

from .utils import AddonPreferences
class RegionRulerPreferences(
        AddonPreferences,
        bpy.types.PropertyGroup if '.' in __name__ else
        bpy.types.AddonPreferences):
    ...

"""


def _get_pref_class(mod):
    for obj in vars(mod).values():
        if inspect.isclass(obj) and issubclass(obj, bpy.types.PropertyGroup):
            if hasattr(obj, 'bl_idname') and obj.bl_idname == mod.__name__:
                return obj


def get_addon_preferences(name=''):
    """登録と取得"""
    prefs = bpy.context.user_preferences.addons[__name__].preferences
    if name:
        if not hasattr(prefs, name):
            for mod in sub_modules:
                if mod.__name__.split('.')[-1] == name:
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
        name = mod.__name__.split('.')[-1]
        if hasattr(CToolsPreferences, name):
            delattr(CToolsPreferences, name)
            bpy.utils.unregister_class(CToolsPreferences)
            bpy.utils.register_class(CToolsPreferences)
            if name in prefs:
                del prefs[name]


class CToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

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
            mod_name = mod.__name__.split('.')[-1]

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
            sub.label('{}: {}'.format(info['category'], info['name']))
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

                tot_row = int(bool(info.get('wiki_url')))
                if tot_row:
                    split = col.row().split(percentage=0.15)
                    split.label(text='Internet:')
                    if info.get('wiki_url'):
                        op = split.operator('wm.url_open',
                                            text='Documentation', icon='HELP')
                        op.url = info.get('wiki_url')
                    for i in range(4 - tot_row):
                        split.separator()

                # 詳細・設定値
                if getattr(self, 'use_' + mod_name):
                    prefs = get_addon_preferences(mod_name)
                    if prefs and hasattr(prefs, 'draw'):
                        box = column.box()
                        prefs.layout = box
                        try:
                            prefs.draw(context)
                        except:
                            traceback.print_exc()
                            box.label(text='Error (see console)', icon='ERROR')
                        del prefs.layout

        split = layout.row().split()
        row = split.row()
        row.operator('script.cutils_module_update',
                     icon='FILE_REFRESH')
        for i in range(3):
            split.separator()


for mod in sub_modules:
    info = mod.bl_info
    mod_name = mod.__name__.split('.')[-1]

    def gen_update(mod):
        def update(self, context):
            if getattr(self, 'use_' + mod.__name__.split('.')[-1]):
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


class SCRIPT_OT_cutils_module_update(bpy.types.Operator):
    """このアドオンのディレクトリの中身を全部消して置換する"""
    bl_idname = 'script.cutils_module_update'
    bl_label = 'Update'

    ctools_dir = os.path.dirname(os.path.abspath(__file__))
    bl_description = 'Download and install addon. ' + \
        'Warning: remove all files under {}/'.format(ctools_dir)

    url = 'https://github.com/chromoly/blender_ctools/archive/master.zip'

    def execute(self, context):
        # '.git'が存在すればやめる
        if '.git' in os.listdir(self.ctools_dir):
            self.report(type={'ERROR'},
                        message="Found '.git' directory. "
                                "Please use git command")
            return {'CANCELLED'}

        context.window.cursor_set('WAIT')

        req = urllib.request.urlopen(self.url)

        with tempfile.TemporaryDirectory() as tmpdir_name:
            with tempfile.NamedTemporaryFile(
                    'wb', suffix='.zip', dir=tmpdir_name,
                    delete=False) as tmpfile:
                tmpfile.write(req.read()),
            zf = zipfile.ZipFile(tmpfile.name, 'r')
            dirname = ''
            for name in zf.namelist():
                p = pathlib.PurePath(name)
                if len(p.parts) == 1:
                    dirname = p.parts[0]
                zf.extract(name, path=tmpdir_name)

            # delete all
            for n in os.listdir(self.ctools_dir):
                p = os.path.join(self.ctools_dir, n)
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)

            # copy all
            new_ctools_dir = os.path.join(tmpdir_name, dirname)
            for n in os.listdir(new_ctools_dir):
                p = os.path.join(new_ctools_dir, n)
                if os.path.isdir(p):
                    shutil.copytree(p, os.path.join(self.ctools_dir, n))
                else:
                    shutil.copy2(p, os.path.join(self.ctools_dir, n))

        context.window.cursor_set('DEFAULT')

        self.report(type={'WARNING'}, message='Updated. Please restart')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


classes = [
    CToolsPreferences,
    SCRIPT_OT_cutils_module_update,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = get_addon_preferences()
    for mod in sub_modules:
        if not hasattr(mod, '__addon_enabled__'):
            mod.__addon_enabled__ = False
        name = mod.__name__.split('.')[-1]
        if getattr(prefs, 'use_' + name):
            register_submodule(mod)


def unregister():
    prefs = get_addon_preferences()
    for mod in sub_modules:
        if getattr(prefs, 'use_' + mod.__name__.split('.')[-1]):
            unregister_submodule(mod)

    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)
