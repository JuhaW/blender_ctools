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
