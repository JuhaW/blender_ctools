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


"""
commit a791153ca5e6f87d50396e188a3664b579884161
3D Cursor: Add option to lock it in place to prevent accidental modification

これを再現したものになります

各SpaceView3DのフラグはScreenのIDPropertyに保存されます
"""


bl_info = {
    'name': 'Lock 3D Cursor',
    'author': 'chromoly',
    'version': (0, 3),
    'blender': (2, 76, 0),
    'location': '3D View',
    'description': 'commit a791153: 3D Cursor: Add option to lock it in place '
                   'to prevent accidental modification',
    'warning': '',
    'wiki_url': '',
    'tracker_url': '',
    'category': '3D View'
}


import bpy


TARGET_KEYCONFIG = 'Blender'  # or 'Blender User'


class SpaceProperty:
    """
    bpy.types.Spaceに仮想的なプロパティを追加

    # インスタンス生成
    space_prop = SpaceProperty(
        [[bpy.types.SpaceView3D, 'lock_cursor_location',
          bpy.props.BoolProperty()]])

    # 描画時
    def draw(self, context):
        layout = self.layout
        view = context.space_data
        prop = space_prop.get_prop(view, 'lock_cursor_location')
        layout.prop(prop, 'lock_cursor_location')

    # register / unregister
    def register():
        space_prop.register()

    def unregister():
        space_prop.unregister()
    """

    space_types = {
        'EMPTY': bpy.types.Space,
        'NONE': bpy.types.Space,
        'CLIP_EDITOR': bpy.types.SpaceClipEditor,
        'CONSOLE': bpy.types.SpaceConsole,
        'DOPESHEET_EDITOR': bpy.types.SpaceDopeSheetEditor,
        'FILE_BROWSER': bpy.types.SpaceFileBrowser,
        'GRAPH_EDITOR': bpy.types.SpaceGraphEditor,
        'IMAGE_EDITOR': bpy.types.SpaceImageEditor,
        'INFO': bpy.types.SpaceInfo,
        'LOGIC_EDITOR': bpy.types.SpaceLogicEditor,
        'NLA_EDITOR': bpy.types.SpaceNLA,
        'NODE_EDITOR': bpy.types.SpaceNodeEditor,
        'OUTLINER': bpy.types.SpaceOutliner,
        'PROPERTIES': bpy.types.SpaceProperties,
        'SEQUENCE_EDITOR': bpy.types.SpaceSequenceEditor,
        'TEXT_EDITOR': bpy.types.SpaceTextEditor,
        'TIMELINE': bpy.types.SpaceTimeline,
        'USER_PREFERENCES': bpy.types.SpaceUserPreferences,
        'VIEW_3D': bpy.types.SpaceView3D,
    }
    # space_types_r = {v: k for k, v in space_types.items()}

    def __init__(self, *props):
        """
        :param props: [[space_type, attr, prop], ...]
            [[文字列かbpy.types.Space, 文字列,
              bpy.props.***()かPropertyGroup], ...]
        :type props: list[list]
        """
        self.props = [list(elem) for elem in props]
        for elem in self.props:
            space_type = elem[0]
            if isinstance(space_type, str):
                elem[0] = self.space_types[space_type]
        self.registered = []
        self.save_pre = self.save_post = self.load_post = None

    def gen_save_pre(self):
        @bpy.app.handlers.persistent
        def save_pre(dummy):
            wm = bpy.context.window_manager
            for (space_type, attr, prop), (cls, wm_prop_name) in zip(
                    self.props, self.registered):
                if wm_prop_name not in wm:
                    continue
                d = {p['name']: p for p in wm[wm_prop_name]}  # not p.name
                for screen in bpy.data.screens:
                    ls = []
                    for area in screen.areas:
                        for space in area.spaces:
                            if isinstance(space, space_type):
                                key = str(space.as_pointer())
                                if key in d:
                                    ls.append(d[key])
                                else:
                                    ls.append({})
                    screen[wm_prop_name] = ls
        self.save_pre = save_pre
        return save_pre

    def gen_save_post(self):
        @bpy.app.handlers.persistent
        def save_post(dummy):
            # 掃除
            for cls, wm_prop_name in self.registered:
                for screen in bpy.data.screens:
                    if wm_prop_name in screen:
                        del screen[wm_prop_name]
        self.save_post = save_post
        return save_post

    def gen_load_post(self):
        @bpy.app.handlers.persistent
        def load_post(dummy):
            from collections import OrderedDict
            for (space_type, attr, prop), (cls, wm_prop_name) in zip(
                    self.props, self.registered):
                d = OrderedDict()
                for screen in bpy.data.screens:
                    if wm_prop_name not in screen:
                        continue

                    spaces = []
                    for area in screen.areas:
                        for space in area.spaces:
                            if isinstance(space, space_type):
                                spaces.append(space)

                    for space, p in zip(spaces, screen[wm_prop_name]):
                        key = p['name'] = str(space.as_pointer())
                        d[key] = p
                if d:
                    bpy.context.window_manager[wm_prop_name] = list(d.values())

            # 掃除
            for cls, wm_prop_name in self.registered:
                for screen in bpy.data.screens:
                    if wm_prop_name in screen:
                        del screen[wm_prop_name]

        self.load_post = load_post
        return load_post

    def get_prop(self, space, attr=''):
        """
        :type space: bpy.types.Space
        :param attr: プロパティが一つだけの場合のみ省略可
        :type attr: str
        :return:
        :rtype:
        """
        context = bpy.context
        for (space_type, attri, prop), (cls, wm_prop_name) in zip(
                self.props, self.registered):
            if isinstance(space, space_type):
                if attri == attr or not attr and len(self.props) == 1:
                    seq = getattr(context.window_manager, wm_prop_name)
                    key = str(space.as_pointer())
                    if key not in seq:
                        item = seq.add()
                        item.name = key
                    return seq[key]

    def _property_name(self, space_type, attr):
        return space_type.__name__.lower() + '_' + attr

    def register(self):
        import inspect
        for space_type, attr, prop in self.props:
            if inspect.isclass(prop) and \
                    issubclass(prop, bpy.types.PropertyGroup):
                cls = prop
            else:
                name = 'WM_PG_' + space_type.__name__ + '_' + attr
                cls = type(name, (bpy.types.PropertyGroup,), {attr: prop})
                bpy.utils.register_class(cls)

            collection_prop = bpy.props.CollectionProperty(type=cls)
            wm_prop_name = self._property_name(space_type, attr)
            setattr(bpy.types.WindowManager, wm_prop_name, collection_prop)

            self.registered.append((cls, wm_prop_name))

            def gen():
                def get(self):
                    seq = getattr(bpy.context.window_manager, wm_prop_name)
                    key = str(self.as_pointer())
                    if key not in seq:
                        item = seq.add()
                        item.name = key
                    return getattr(seq[key], attr)

                def set(self, value):
                    seq = getattr(bpy.context.window_manager, wm_prop_name)
                    key = str(self.as_pointer())
                    if key not in seq:
                        item = seq.add()
                        item.name = key
                    return setattr(seq[key], attr, value)

                return property(get, set)

            setattr(space_type, attr, gen())

        bpy.app.handlers.save_pre.append(self.gen_save_pre())
        bpy.app.handlers.save_post.append(self.gen_save_post())
        bpy.app.handlers.load_post.append(self.gen_load_post())

    def unregister(self):
        bpy.app.handlers.save_pre.remove(self.save_pre)
        bpy.app.handlers.save_post.remove(self.save_post)
        bpy.app.handlers.load_post.remove(self.load_post)

        for (space_type, attr, prop), (cls, wm_prop_name) in zip(
                self.props, self.registered):
            delattr(bpy.types.WindowManager, wm_prop_name)
            if wm_prop_name in bpy.context.window_manager:
                del bpy.context.window_manager[wm_prop_name]
            delattr(space_type, attr)

            bpy.utils.unregister_class(cls)

            for screen in bpy.data.screens:
                if wm_prop_name in screen:
                    del screen[wm_prop_name]

        self.registered.clear()


space_prop = SpaceProperty(
    [bpy.types.SpaceView3D, 'lock_cursor_location',
     bpy.props.BoolProperty()])


class VIEW3D_OT_cursor3d_restrict(bpy.types.Operator):
    bl_idname = 'view3d.cursor3d_restrict'
    bl_label = 'Cursor 3D'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if bpy.ops.view3d.cursor3d.poll():
            if not context.space_data.lock_cursor_location:
                return True
        return False

    def invoke(self, context, event):
        return bpy.ops.view3d.cursor3d(context.copy(), 'INVOKE_DEFAULT')


draw_func_bak = None


def panel_draw_set():
    global draw_func_bak

    def draw(self, context):
        layout = self.layout
        view = context.space_data
        layout.prop(space_prop.get_prop(view), 'lock_cursor_location')
        col = layout.column()
        col.active = not view.lock_cursor_location
        col.prop(view, 'cursor_location', text='Location')
        if hasattr(view, 'use_cursor_snap_grid'):
            col = layout.column()
            U = context.user_preferences
            col.active = not U.view.use_mouse_depth_cursor
            col.prop(view, "use_cursor_snap_grid", text="Cursor to Grid")

    draw_func_bak = None

    cls = bpy.types.VIEW3D_PT_view3d_cursor
    if hasattr(cls.draw, '_draw_funcs'):
        # bpy_types.py: _GenericUI._dyn_ui_initialize
        for i, func in enumerate(cls.draw._draw_funcs):
            if func.__module__ == cls.__module__:
                cls.draw._draw_funcs[i] = draw
                draw_func_bak = func
                break
    else:
        draw_func_bak = cls.draw
        cls.draw = draw


def panel_draw_restore():
    cls = bpy.types.VIEW3D_PT_view3d_cursor
    if hasattr(cls.draw, '_draw_funcs'):
        if draw_func_bak:
            for i, func in enumerate(cls.draw._draw_funcs):
                if func.__module__ == __package__:
                    cls.draw._draw_funcs[i] = draw_func_bak
    else:
        cls.draw = draw_func_bak


keymap_items = []


@bpy.app.handlers.persistent
def scene_update_pre(scene):
    """起動後に一度だけ実行"""
    kc = bpy.context.window_manager.keyconfigs[TARGET_KEYCONFIG]
    if kc:
        km = kc.keymaps.get('3D View')
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == 'view3d.cursor3d':
                    kmi.idname = 'view3d.cursor3d_restrict'
                    keymap_items.append((km, kmi))
    bpy.app.handlers.scene_update_pre.remove(scene_update_pre)


classes = [
    VIEW3D_OT_cursor3d_restrict
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    """
    NOTE: 特定Areaを最大化すると一時的なScreenが生成されるので
    lock_cursor_location属性はScreenでは不適。WindowManagerを使う。
    """
    space_prop.register()

    bpy.app.handlers.scene_update_pre.append(scene_update_pre)

    panel_draw_set()


def unregister():
    panel_draw_restore()

    if scene_update_pre in bpy.app.handlers.scene_update_pre:
        bpy.app.handlers.scene_update_pre.remove(scene_update_pre)

    space_prop.unregister()

    for km, kmi in keymap_items:
        # km.keymap_items.remove(kmi)
        kmi.idname = 'view3d.cursor3d'
    keymap_items.clear()

    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
