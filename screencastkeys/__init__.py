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

# <pep8 compliant>


bl_info = {
    "name": "Screencast Keys Mod",
    "author": "Paulo Gomes, Bart Crouch, John E. Herrenyo, Gaia Clary, Pablo Vazquez, chromoly",
    "version": (1, 7, 4),
    "blender": (2, 76, 0),
    "location": "3D View > Properties Panel > Screencast Keys",
    "warning": "",
    "description": "Display keys pressed in the 3D View, "
                   "useful for screencasts.",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/"
                "Py/Scripts/3D_interaction/Screencast_Key_Status_Tool",
    'wiki_url2': 'https://github.com/chromoly/blender-ScreencastKeysMod',
    "tracker_url": "http://projects.blender.org/tracker/index.php?"
                   "func=detail&aid=21612",
    "category": "3D View"
}

import time
import datetime
import functools
from ctypes import *
import logging

import bpy
import bgl
import blf
import bpy.props

from .utils import AddonPreferences


MOUSE_RATIO = 0.535

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
_handler = logging.StreamHandler()
_handler.setLevel(logging.NOTSET)
_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


###############################################################################
# ctypes
###############################################################################
class Structures:
    class ListBase(Structure):
        """source/blender/makesdna/DNA_listBase.h: 59"""
        _fields_ = [
            ('first', c_void_p),
            ('last', c_void_p)
        ]

    class wmEvent(Structure):
        """source/blender/windowmanager/WM_types.h: 431"""
        pass

    wmEvent._fields_ = [
        ('next', POINTER(wmEvent)),
        ('prev', POINTER(wmEvent)),
        ('type', c_short),
        ('val', c_short),
        ('x', c_int),
        ('y', c_int),
        ('mval', c_int * 2),
        ('utf8_buf', c_char * 6),

        ('ascii', c_char),
        ('pad', c_char),

        ('is_key_pressed', c_bool),

        ('prevtype', c_short),
        ('prevval', c_short),
        ('prevx', c_int),
        ('prevy', c_int),
        ('prevclick_time', c_double),
        ('prevclickx', c_int),
        ('prevclicky', c_int),

        ('shift', c_short),
        ('ctrl', c_short),
        ('alt', c_short),
        ('oskey', c_short),
        ('keymodifier', c_short),

        ('check_click', c_short),

        ('keymap_idname', c_char_p),

        ('tablet_data', c_void_p),  # const struct wmTabletData

        ('custom', c_short),
        ('customdatafree', c_short),
        ('pad2', c_int),

        ('customdata', c_void_p),
    ]

    class wmOperatorType(Structure):
        """source/blender/windowmanager/WM_types.h: 517"""
        _fields_ = [
            ('name', c_char_p),
            ('idname', c_char_p),
            ('translation_context', c_char_p),
            ('description', c_char_p),
        ]

    class wmWindow(Structure):
        """source/blender/makesdna/DNA_windowmanager_types.h: 175"""
        pass

    wmWindow._fields_ = [
        ('next', POINTER(wmWindow)),
        ('prev', POINTER(wmWindow)),

        ('ghostwin', c_void_p),

        ('screen', c_void_p),  # struct bScreen
        ('newscreen', c_void_p),  # struct bScreen
        ('screenname', c_char * 64),

        ('posx', c_short),
        ('posy', c_short),
        ('sizex', c_short),
        ('sizey', c_short),
        ('windowstate', c_short),
        ('monitor', c_short),
        ('active', c_short),
        ('cursor', c_short),
        ('lastcursor', c_short),
        ('modalcursor', c_short),
        ('grabcursor', c_short),
        ('addmousemove', c_short),

        ('winid', c_int),

        ('lock_pie_event', c_short),
        ('last_pie_event', c_short),

        ('eventstate', POINTER(wmEvent)),

        ('curswin', c_void_p),  # struct wmSubWindow

        ('tweak', c_void_p),  # struct wmGesture

        ('ime_data', c_void_p),  # struct wmIMEData

        ('drawmethod', c_int),
        ('drawfail', c_int),
        ('drawdata', ListBase),

        ('queue', ListBase),
        ('handlers', ListBase),
        ('modalhandlers', ListBase),

        ('subwindows', ListBase),
        ('gesture', ListBase),

        ('stereo3d_format', c_void_p),  # struct Stereo3dFormat
    ]

    class wmOperator(Structure):
        """source/blender/makesdna/DNA_windowmanager_types.h: 344"""
        pass

    wmOperator._fields_ = [
        ('next', POINTER(wmOperator)),
        ('prev', POINTER(wmOperator)),

        ('idname', c_char * 64),
        ('properties', c_void_p),  # IDProperty

        ('type', POINTER(wmOperatorType)),
        ('customdata', c_void_p),
        ('py_instance', py_object),  # python stores the class instance here

        ('ptr', c_void_p),  # PointerRNA
        ('reports', c_void_p),  # ReportList

        ('macro', ListBase),
        ('opm', POINTER(wmOperator)),
        ('layout', c_void_p),  # uiLayout
        ('flag', c_short),
        ('pad', c_short * 3)
    ]

    class wmEventHandler(Structure):
        """source/blender/windowmanager/wm_event_system.h: 45"""
        pass

    wmEventHandler._fields_ = [
        ('next', POINTER(wmEventHandler)),
        ('prev', POINTER(wmEventHandler)),  # struct wmEventHandler

        ('type', c_int),
        ('flag', c_int),

        ('keymap', c_void_p),
        ('bblocal', c_void_p),
        ('bbwin', c_void_p),  # const rcti

        ('op', POINTER(wmOperator)),
        ('op_area', c_void_p),  # struct ScrArea
        ('op_region', c_void_p),  # struct ARegion
        ('op_region_type', c_short),

        ('ui_handle', c_void_p),
        # /* ui handler */
        # wmUIHandlerFunc ui_handle;          /* callback receiving events */
        # wmUIHandlerRemoveFunc ui_remove;    /* callback when handler is removed */
        # void *ui_userdata;                  /* user data pointer */
        # struct ScrArea *ui_area;            /* for derived/modal handlers */
        # struct ARegion *ui_region;          /* for derived/modal handlers */
        # struct ARegion *ui_menu;            /* for derived/modal handlers */
        #
        # /* drop box handler */
        # ListBase *dropboxes;
    ]


###############################################################################
# ModalHandlerManager
###############################################################################
class ModalHandlerManager:
    """
    常時バックグラウンドで動作する({'PASS_THROUGH'}を返す)ようなModalOperator
    を補助する。

    効果:
    ほぼ全てのイベントでmodal()が呼び出されるようになる。
    全てのWindowに対して自動でオペレータを起動する。

    副作用:
    常時監視する為負荷が増える。
    特にレンダリング時はEventTimerを追加するので注意。
    必要に応じてオペレータを再起動するので、インスタンス属性・bpy.propsを用いた
    プロパティへの変更は無駄となる。クラス属性を使うか、get,set関数を使った
    bpy.propsのプロパティを用いる事。

    基本的にこのクラスを継承して使用しない事。
    レンダリング時のタイマーをクラス属性で管理している為、これを継承した複数の
    クラスを同時に使用した場合、その分レンダリング時のタイマー発生が増える。
    """

    RENDERING_TIMER_STEP = 1.0 / 60  # min: 0.005s

    _render_timers = {}
    _is_rendering = False

    managers = []  # 全てのインスタンス
    """:type: list[ModalHandlerManager]"""

    NORMAL = 0
    RESTART = 1
    AUTO_START = 2

    def __init__(self, idname, restart=True, all_windows=True, callback=None,
                 args=('INVOKE_DEFAULT',), kwargs=None,
                 render_timer_step=RENDERING_TIMER_STEP):
        """
        :param idname: ModalOperator e.g. 'mod.function'
        :type idname: str
        :param restart: handlerが先頭でないなら再起動
        :type restart: bool
        :param all_windows: 新規Windowに対して自動でオペレータを起動し、
            ModalHandlerを追加する。
        :type all_windows: bool
        :param callback: 再起動・自動起動の際に実行。
            第一引数にcontext, 第ニ引数にevent, 第三引数に新規operator。
            再起動の場合は第四引数にそのwindowで動作中のoperator、
            自動起動の場合は第四引数はNoneとなる。
        :type callback: collections.abc.Callable
        :param args: operator実行時に渡す引数
        :type args: list | tuple
        :param kwargs: operator実行時に渡す引数
        :type kwargs: dict
        :param render_timer_step:
        :type render_timer_step: float
        """

        # SUBMOD_OT_foo -> submod.foo
        if '.' not in idname and '_OT_' in idname:
            mod, func = idname.split('_OT_')
            idname = mod.lower() + '.' + func

        self.idname = idname
        self.args = args
        self.kwargs = kwargs
        self.restart = restart
        self.all_windows = all_windows

        self.callback = callback
        self.render_timer_step = render_timer_step

        # 値がNoneとなるのはinvoke()の時のみ
        self.operators = {}
        """:type: dict[int, T]"""

        self._exit_timers = {}

        self.status = self.NORMAL

        self.managers.append(self)

    def _get_window_modal_handlers(self, window):
        """ctypesを使い、windowに登録されている modal handlerのリストを返す。
        idnameはUIなら 'UI'、認識できない物なら 'UNKNOWN' となる。
        :rtype: list[(Structures.wmEventHandler, str, int, int, int)]
        """
        if not window:
            return []

        addr = window.as_pointer()
        win = cast(c_void_p(addr), POINTER(Structures.wmWindow)).contents

        handlers = []

        ptr = cast(win.modalhandlers.first, POINTER(Structures.wmEventHandler))
        while ptr:
            # http://docs.python.jp/3/library/ctypes.html#surprises
            # この辺りの事には注意する事
            handler = ptr.contents
            area = handler.op_area  # NULLの場合はNone
            region = handler.op_region  # NULLの場合はNone
            idname = 'UNKNOWN'
            if handler.ui_handle:
                idname = 'UI'
            if handler.op:
                op = handler.op.contents
                ot = op.type.contents
                if ot.idname:
                    idname = ot.idname.decode()
            handlers.append((handler, idname, area, region,
                             handler.op_region_type))
            ptr = handler.next

        return handlers

    @staticmethod
    def _operator_call(op, args=None, kwargs=None, scene_update=True):
        from _bpy import ops as ops_module

        if isinstance(op, str):
            mod, func = op.split('.')
            op = getattr(getattr(bpy.ops, mod), func)

        BPyOpsSubModOp = op.__class__
        op_call = ops_module.call
        context = bpy.context

        # Get the operator from blender
        wm = context.window_manager

        # run to account for any rna values the user changes.
        if scene_update:
            BPyOpsSubModOp._scene_update(context)

        if not args:
            args = ()
        if not kwargs:
            kwargs = {}
        if args:
            C_dict, C_exec, C_undo = BPyOpsSubModOp._parse_args(args)
            ret = op_call(op.idname_py(), C_dict, kwargs, C_exec, C_undo)
        else:
            ret = op_call(op.idname_py(), None, kwargs)

        if 'FINISHED' in ret and context.window_manager == wm:
            if scene_update:
                BPyOpsSubModOp._scene_update(context)

        return ret

    def _parse_args(self, context, override_context=None):
        override = op_context = undo = None
        if self.args:
            for arg in self.args:
                if isinstance(arg, dict):
                    override = arg
                elif isinstance(arg, str):
                    op_context = arg
                elif isinstance(arg, bool):
                    undo = arg

        # override
        if override_context:
            if not override:
                override = context.copy()
            else:
                override = override.copy()
            override.update(override_context)
        # operator context
        if not op_context or not op_context.startswith('INVOKE'):
            op_context = 'INVOKE_DEFAULT'
        # merge
        args = []
        for value in (override, op_context, undo):
            if value is not None:
                args.append(value)

        return args

    def _restart_do(self, context, window):
        """必要無ければ再起動を行わない"""
        addr = window.as_pointer()
        if addr not in self.operators:
            return

        restart = False
        op_area_ptr = op_region_ptr = None
        op_region_type = -1
        handlers = self._get_window_modal_handlers(window)
        for handler, idname, area_p, region_p, region_t in handlers:
            if idname == 'UNKNOWN':
                continue
            if '.' not in idname and '_OT_' in idname:
                mod, func = idname.split('_OT_')
                idname_py = mod.lower() + '.' + func
            else:
                idname_py = idname
            if idname_py == self.idname:
                op_area_ptr = cast(area_p, c_void_p)
                op_region_ptr = cast(region_p, c_void_p)
                op_region_type = region_t
                break
            else:
                for m in self.managers:
                    if idname_py == m.idname:
                        break
                else:
                    restart = True

        if not restart:
            return

        # Call invoke()
        logger.debug('Restart')
        args = self._parse_args(context)
        self.status = self.RESTART
        r = self._operator_call(self.idname, args, self.kwargs,
                                scene_update=False)
        self.status = self.NORMAL

        # Set Handler Area & Region
        # 安全の為慎重に進める
        if op_area_ptr or op_region_ptr:
            if {'RUNNING_MODAL'} & r and not {'FINISHED', 'CANCELLED'} & r:
                handlers_prev = handlers
                handlers = self._get_window_modal_handlers(window)
                if len(handlers) == len(handlers_prev) + 1:
                    handler, idname, _area_p, _region_p, _region_t = \
                        handlers[0]
                    if handler.op:
                        if '.' not in idname and '_OT_' in idname:
                            mod, func = idname.split('_OT_')
                            idname_py = mod.lower() + '.' + func
                        else:
                            idname_py = idname
                        if idname_py == self.idname:
                            if op_area_ptr:
                                handler.op_area = op_area_ptr
                            if op_region_ptr:
                                handler.op_region = op_region_ptr
                                handler.op_region_type = op_region_type
                                logger.debug(
                                    'Set wmEventHandler.op_region, '
                                    'wmEventHandler.op_area')

    def _auto_start_do(self, context, window):
        """必要無ければ自動起動を行わない"""
        addr = window.as_pointer()
        if addr in self.operators:
            return

        override = {}
        screen = context.screen
        scene = context.scene
        if not (context.window == window and screen and scene and
                screen == window.screen and scene == screen.scene):
            override['window'] = window
            override['screen'] = window.screen
            override['scene'] = window.screen.scene
            override['area'] = None
            override['region'] = None
        args = self._parse_args(context, override)

        # Call invoke()
        logger.debug('Auto Start')
        self.status = self.AUTO_START
        self._operator_call(self.idname, args, self.kwargs, scene_update=False)
        self.status = self.NORMAL

    @classmethod
    def _scene_update_pre(cls, scn):
        """再起動及び新規windowへの自動起動"""
        context = bpy.context
        window = context.window
        screen = context.screen
        scene = context.scene
        if not window:
            return

        addr = window.as_pointer()
        running_any = False
        for m in cls.managers:
            m._cleanup(context)
            if m.is_running(context):
                running_any = True
                if addr in m.operators:
                    if m.restart:
                        m._restart_do(context, window)
                else:
                    if m.all_windows:
                        if (window and screen and scene and
                                screen == window.screen and
                                scene == screen.scene == scn):
                            # メインループなら必ずこれが一致する
                            m._auto_start_do(context, window)
        if not running_any:
            handlers = bpy.app.handlers.scene_update_pre
            if cls._scene_update_pre in handlers:
                handlers.remove(cls._scene_update_pre)
                logger.debug('Remove scene handler')

    @classmethod
    def _render_timer_add(cls):
        context = bpy.context
        wm = context.window_manager

        steps = [m.render_timer_step for m in cls.managers
                 if m.is_running(context)]
        if not steps or set(steps) == {0.0}:
            return
        else:
            step = min([f for f in steps if f != 0.0])

        for window in wm.windows:
            addr = window.as_pointer()
            if addr not in cls._render_timers:
                timer = wm.event_timer_add(step, window)
                cls._render_timers[addr] = timer
                logger.debug('Add timer')

    @classmethod
    def _render_init(cls, dummy):
        """bpy.app.handlers.render_init.append(_render_init)とだけ行い、
        他のhandlerの追加・削除はレンダリング完了／中断時に自動で行われる
        """
        cls._render_timer_add()
        cls._is_rendering = True

        # add render handlers
        # complete
        render_complete = bpy.app.handlers.render_complete
        if cls._render_complete not in render_complete:
            render_complete.append(cls._render_complete)
        # cancel
        render_cancel = bpy.app.handlers.render_cancel
        if cls._render_cancel not in render_cancel:
            render_cancel.append(cls._render_cancel)

        logger.debug('Add render complete/cancel handler')

        # NOTE: BLI_callback_exec(re->main, (ID *)scene,
        #                         BLI_CB_EVT_RENDER_INIT);

    @classmethod
    def _render_complete(cls, dummy):
        context = bpy.context
        wm = context.window_manager
        for timer in cls._render_timers.values():
            wm.event_timer_remove(timer)
            logger.debug('Remove timer')
        cls._render_timers.clear()
        cls._is_rendering = False

        # remove render handlers
        # init
        running = any([m.is_running(context) for m in cls.managers])
        if not running:
            render_init = bpy.app.handlers.render_init
            if cls._render_init in render_init:
                render_init.remove(cls._render_init)
        # complete
        render_complete = bpy.app.handlers.render_complete
        if cls._render_complete in render_complete:
            render_complete.remove(cls._render_complete)
        # cancel
        render_cancel = bpy.app.handlers.render_cancel
        if cls._render_cancel in render_cancel:
            render_cancel.remove(cls._render_cancel)
        logger.debug('Remove render handlers')

    @classmethod
    def _render_cancel(cls, dummy):
        cls._render_complete(dummy)

    @classmethod
    def _add_handlers(cls):
        # 削除は自動
        # Scene
        handlers = bpy.app.handlers.scene_update_pre
        if cls._scene_update_pre not in handlers:
            handlers.append(cls._scene_update_pre)
            logger.debug('Add scene handler')

        # Render
        handlers = bpy.app.handlers.render_init
        if cls._render_init not in handlers:
            handlers.append(cls._render_init)
            logger.debug('Add render int handler')

    @classmethod
    def terminate(cls):
        """handler,timer,operator全てを強制削除"""
        context = bpy.context
        wm = context.window_manager

        # Scene update handler
        handlers = bpy.app.handlers.scene_update_pre
        if cls._scene_update_pre in handlers:
            handlers.remove(cls._scene_update_pre)

        # Render handlers
        render_init = bpy.app.handlers.render_complete
        if cls._render_init in render_init:
            render_init.remove(cls._render_init)
        render_complete = bpy.app.handlers.render_complete
        if cls._render_complete in render_complete:
            render_complete.remove(cls._render_complete)
        render_cancel = bpy.app.handlers.render_cancel
        if cls._render_cancel in render_cancel:
            render_cancel.remove(cls._render_cancel)
        logger.debug('Remove render handlers')

        # Render timers
        for timer in cls._render_timers.values():
            wm.event_timer_remove(timer)
        cls._render_timers.clear()

        # operators, exit_timers
        for m in cls.managers:
            m.operators.clear()
            for timer in m._exit_timers.values():
                wm.event_timer_remove(timer)
            m._exit_timers.clear()
            m.status = m.NORMAL

    def _exit(self, context, window=None):
        """self.all_windowsが真の場合は全てのoperatorを、そうでないなら
        context.windowのoperatorのみを修了させる。
        """
        wm = context.window_manager
        if window:
            addr = window.as_pointer()
            if addr in self.operators:
                if addr not in self._exit_timers:
                    timer = wm.event_timer_add(0.0, window)
                    self._exit_timers[addr] = timer
                del self.operators[addr]
        else:
            for window in wm.windows:
                addr = window.as_pointer()
                if addr in self.operators and addr not in self._exit_timers:
                    timer = wm.event_timer_add(0.0, window)
                    self._exit_timers[addr] = timer
            self.operators.clear()

    def _cleanup(self, context):
        """無効なwindowのoperatorとexit_timerの削除"""
        wm = context.window_manager
        addrs = {win.as_pointer() for win in wm.windows}
        for addr in list(self.operators.keys()):
            if addr not in addrs:
                del self.operators[addr]

        if self._exit_timers:
            for addr in list(self._exit_timers.keys()):
                if addr not in addrs:
                    wm.event_timer_remove(self._exit_timers.pop(addr))

        if not self.operators:
            self.status = self.NORMAL

    def is_running(self, context, window=None):
        wm = context.window_manager
        if window:
            return window.as_pointer() in self.operators
        else:
            addrs = {win.as_pointer() for win in wm.windows}
            if addrs & set(self.operators.keys()):
                return True
            else:
                return False

    @staticmethod
    def active_window(context):
        wm = context.window_manager
        for window in wm.windows:
            addr = window.as_pointer()
            win = cast(c_void_p(addr), POINTER(Structures.wmWindow)).contents
            if win.active:
                return window

    def modal(self, func):
        @functools.wraps(func)
        def _modal(self_, context, event):
            wm = context.window_manager
            window = context.window
            addr = window.as_pointer()

            self._cleanup(context)

            if addr in self._exit_timers:
                wm.event_timer_remove(self._exit_timers.pop(addr))

            if addr not in self.operators or self.operators[addr] != self_:
                logger.debug('Unnecessary operator cancelled')
                return {'CANCELLED', 'PASS_THROUGH'}

            r = func(self_, context, event)
            if r & {'FINISHED', 'CANCELLED'}:
                win = None if self.all_windows else context.window
                self._exit(context, win)
            else:
                if self._is_rendering:
                    # レンダリング中はscene_updateが行われない為、
                    # restart,auto_startはここで行う
                    # Restart
                    if self.restart:
                        self._restart_do(context, window)
                    # Auto Start
                    if self.all_windows:
                        for window in wm.windows:
                            if window != context.window:
                                self._auto_start_do(context, window)
                    # Timer
                    if self.restart or self.all_windows:
                        self._render_timer_add()
            return r

        return _modal

    def invoke(self, func):
        @functools.wraps(func)
        def _invoke(self_, context, event):
            window = context.window
            addr = window.as_pointer()

            self._cleanup(context)

            manage = True
            if (self.is_running(context) and
                    self.status in (self.RESTART, self.AUTO_START)):
                context.window_manager.modal_handler_add(self_)
                if self.callback:
                    if self.status == self.RESTART:
                        op = self.operators[addr]
                        self.callback(context, event, self_, op)
                    elif self.status == self.AUTO_START:
                        self.callback(context, event, self_, None)
                r = {'RUNNING_MODAL', 'PASS_THROUGH'}
            else:
                # Operator.invoke()
                r = func(self_, context, event)
                # 何も処理させたくない場合は return ({'CANCELLED'}, False)
                # のように二つ目にFalseを渡す
                if len(r) == 2 and isinstance(r[0], set):
                    r, manage = r

            if not manage:
                return r
            elif r & {'FINISHED', 'CANCELLED'}:
                win = None if self.all_windows else context.window
                self._exit(context, win)
                return r
            else:
                self.operators[addr] = self_
                self._add_handlers()
                return r

        return _invoke


###############################################################################
def get_display_location(context):
    pref = ScreenCastKeysPreferences.get_prefs()
    mouse_size = pref.mouse_size

    regions = [ar for ar in context.area.regions if ar.type == 'WINDOW']
    i = regions.index(context.region)
    if i >= 2:  # 右下、右上
        return -1, -1

    pos_x = int((context.region.width - mouse_size * MOUSE_RATIO) *
                pref.pos_x / 100)
    pos_y = int((context.region.height - mouse_size) *
                pref.pos_y / 100)

    if i == 1:
        pos_y -= context.region.height

    return pos_x, pos_y


def get_bounding_box(current_width, current_height, new_text):
    w, h = blf.dimensions(0, new_text)
    if w > current_width:
        current_width = w
    current_height += h

    return current_width, current_height


# return the shape that belongs to the given event
def map_mouse_event(event):
    shape = False

    if event == 'LEFTMOUSE':
        shape = "left_button"
    elif event == 'MIDDLEMOUSE':
        shape = "middle_button"
    elif event == 'RIGHTMOUSE':
        shape = "right_button"
    elif event == 'WHEELDOWNMOUSE':
        shape = "middle_down_button"
    elif event == 'WHEELUPMOUSE':
        shape = "middle_up_button"

    return shape


# hardcoded data to draw the graphical represenation of the mouse
def get_shape_data(shape):
    data = []
    if shape == "mouse":
        data = [[[0.404, 0.032, 0.0],
                 [0.096, 0.002, 0.0],
                 [0.059, 0.126, 0.0],
                 [0.04, 0.213, 0.0]],
                [[0.04, 0.213, 0.0],
                 [-0.015, 0.465, 0.0],
                 [-0.005, 0.564, 0.0],
                 [0.032, 0.87, 0.0]],
                [[0.032, 0.87, 0.0],
                 [0.05, 0.973, 0.0],
                 [0.16, 1.002, 0.0],
                 [0.264, 1.002, 0.0]],
                [[0.264, 1.002, 0.0],
                 [0.369, 1.002, 0.0],
                 [0.478, 0.973, 0.0],
                 [0.497, 0.87, 0.0]],
                [[0.497, 0.87, 0.0],
                 [0.533, 0.564, 0.0],
                 [0.554, 0.465, 0.0],
                 [0.499, 0.213, 0.0]],
                [[0.499, 0.213, 0.0],
                 [0.490, 0.126, 0.0],
                 [0.432, 0.002, 0.0],
                 [0.404, 0.032, 0.0]]]
    elif shape == "left_button":
        data = [[[0.154, 0.763, 0.0],
                 [0.126, 0.755, 0.0],
                 [0.12, 0.754, 0.0],
                 [0.066, 0.751, 0.0]],
                [[0.066, 0.751, 0.0],
                 [0.043, 0.75, 0.0],
                 [0.039, 0.757, 0.0],
                 [0.039, 0.767, 0.0]],
                [[0.039, 0.767, 0.0],
                 [0.047, 0.908, 0.0],
                 [0.078, 0.943, 0.0],
                 [0.155, 0.97, 0.0]],
                [[0.155, 0.97, 0.0],
                 [0.174, 0.977, 0.0],
                 [0.187, 0.975, 0.0],
                 [0.191, 0.972, 0.0]],
                [[0.191, 0.972, 0.0],
                 [0.203, 0.958, 0.0],
                 [0.205, 0.949, 0.0],
                 [0.199, 0.852, 0.0]],
                [[0.199, 0.852, 0.0],
                 [0.195, 0.77, 0.0],
                 [0.18, 0.771, 0.0],
                 [0.154, 0.763, 0.0]]]
    elif shape == "middle_button":
        data = [[[0.301, 0.8, 0.0],
                 [0.298, 0.768, 0.0],
                 [0.231, 0.768, 0.0],
                 [0.228, 0.8, 0.0]],
                [[0.228, 0.8, 0.0],
                 [0.226, 0.817, 0.0],
                 [0.225, 0.833, 0.0],
                 [0.224, 0.85, 0.0]],
                [[0.224, 0.85, 0.0],
                 [0.222, 0.873, 0.0],
                 [0.222, 0.877, 0.0],
                 [0.224, 0.9, 0.0]],
                [[0.224, 0.9, 0.0],
                 [0.225, 0.917, 0.0],
                 [0.226, 0.933, 0.0],
                 [0.228, 0.95, 0.0]],
                [[0.228, 0.95, 0.0],
                 [0.231, 0.982, 0.0],
                 [0.298, 0.982, 0.0],
                 [0.301, 0.95, 0.0]],
                [[0.301, 0.95, 0.0],
                 [0.302, 0.933, 0.0],
                 [0.303, 0.917, 0.0],
                 [0.305, 0.9, 0.0]],
                [[0.305, 0.9, 0.0],
                 [0.307, 0.877, 0.0],
                 [0.307, 0.873, 0.0],
                 [0.305, 0.85, 0.0]],
                [[0.305, 0.85, 0.0],
                 [0.303, 0.833, 0.0],
                 [0.302, 0.817, 0.0],
                 [0.301, 0.8, 0.0]]]
    elif shape == "middle_down_button":
        data = [[[0.301, 0.8, 0.0],
                 [0.298, 0.768, 0.0],
                 [0.231, 0.768, 0.0],
                 [0.228, 0.8, 0.0]],
                [[0.228, 0.8, 0.0],
                 [0.226, 0.817, 0.0],
                 [0.225, 0.833, 0.0],
                 [0.224, 0.85, 0.0]],
                [[0.224, 0.85, 0.0],
                 [0.264, 0.873, 0.0],
                 [0.284, 0.873, 0.0],
                 [0.305, 0.85, 0.0]],
                [[0.305, 0.85, 0.0],
                 [0.303, 0.833, 0.0],
                 [0.302, 0.817, 0.0],
                 [0.301, 0.8, 0.0]]]
    elif shape == "middle_up_button":
        data = [[[0.270, 0.873, 0.0],
                 [0.264, 0.873, 0.0],
                 [0.222, 0.877, 0.0],
                 [0.224, 0.9, 0.0]],
                [[0.224, 0.9, 0.0],
                 [0.225, 0.917, 0.0],
                 [0.226, 0.933, 0.0],
                 [0.228, 0.95, 0.0]],
                [[0.228, 0.95, 0.0],
                 [0.231, 0.982, 0.0],
                 [0.298, 0.982, 0.0],
                 [0.301, 0.95, 0.0]],
                [[0.301, 0.95, 0.0],
                 [0.302, 0.933, 0.0],
                 [0.303, 0.917, 0.0],
                 [0.305, 0.9, 0.0]],
                [[0.305, 0.9, 0.0],
                 [0.307, 0.877, 0.0],
                 [0.284, 0.873, 0.0],
                 [0.270, 0.873, 0.0]]]
    elif shape == "right_button":
        data = [[[0.375, 0.763, 0.0],
                 [0.402, 0.755, 0.0],
                 [0.408, 0.754, 0.0],
                 [0.462, 0.751, 0.0]],
                [[0.462, 0.751, 0.0],
                 [0.486, 0.75, 0.0],
                 [0.49, 0.757, 0.0],
                 [0.489, 0.767, 0.0]],
                [[0.489, 0.767, 0.0],
                 [0.481, 0.908, 0.0],
                 [0.451, 0.943, 0.0],
                 [0.374, 0.97, 0.0]],
                [[0.374, 0.97, 0.0],
                 [0.354, 0.977, 0.0],
                 [0.341, 0.975, 0.0],
                 [0.338, 0.972, 0.0]],
                [[0.338, 0.972, 0.0],
                 [0.325, 0.958, 0.0],
                 [0.324, 0.949, 0.0],
                 [0.329, 0.852, 0.0]],
                [[0.329, 0.852, 0.0],
                 [0.334, 0.77, 0.0],
                 [0.348, 0.771, 0.0],
                 [0.375, 0.763, 0.0]]]

    return data


def draw_mouse(context, shape, style, alpha):
    # shape and position
    pref = ScreenCastKeysPreferences.get_prefs()
    mouse_size = pref.mouse_size
    font_size = pref.font_size

    pos_x, pos_y = get_display_location(context)

    if pref.mouse_position == 'left':
        offset_x = pos_x
    if pref.mouse_position == 'right':
        offset_x = context.region.width - pos_x - (mouse_size * MOUSE_RATIO)

    offset_y = pos_y
    if font_size > mouse_size:
        offset_y += (font_size - mouse_size) / 2

    shape_data = get_shape_data(shape)

    bgl.glTranslatef(offset_x, offset_y, 0)

    # color
    r, g, b, a = pref.text_color
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(r, g, b, alpha)

    # inner shape for filled style
    if style == "filled":
        inner_shape = []
        for i in shape_data:
            inner_shape.append(i[0])

    # outer shape
    for i in shape_data:
        shape_segment = i
        shape_segment[0] = [mouse_size * k for k in shape_segment[0]]
        shape_segment[1] = [mouse_size * k for k in shape_segment[1]]
        shape_segment[2] = [mouse_size * k for k in shape_segment[2]]
        shape_segment[3] = [mouse_size * k for k in shape_segment[3]]

        # create the buffer
        shape_buffer = bgl.Buffer(bgl.GL_FLOAT, [4, 3], shape_segment)

        # create the map and draw the triangle fan
        bgl.glMap1f(bgl.GL_MAP1_VERTEX_3, 0.0, 1.0, 3, 4, shape_buffer)
        bgl.glEnable(bgl.GL_MAP1_VERTEX_3)

        if style == "outline":
            bgl.glBegin(bgl.GL_LINE_STRIP)
        else:  # style == "filled"
            bgl.glBegin(bgl.GL_TRIANGLE_FAN)
        for j in range(10):
            bgl.glEvalCoord1f(j / 10.0)
        x, y, z = shape_segment[3]

        # make sure the last vertex is indeed the last one, to avoid gaps
        bgl.glVertex3f(x, y, z)
        bgl.glEnd()
        bgl.glDisable(bgl.GL_MAP1_VERTEX_3)

    # draw interior
    if style == "filled":
        bgl.glBegin(bgl.GL_TRIANGLE_FAN)
        for i in inner_shape:
            j = [mouse_size * k for k in i]
            x, y, z = j
            bgl.glVertex3f(x, y, z)
        bgl.glEnd()

    bgl.glTranslatef(-offset_x, -offset_y, 0)


def draw_callback_px_text(cls, context):
    pref = ScreenCastKeysPreferences.get_prefs()
    if not mm.is_running(context):
        return

    font_size = pref.font_size
    dpi = context.user_preferences.system.dpi
    mouse_size = pref.mouse_size
    pos_x, pos_y = get_display_location(context)
    if pos_x == pos_y == -1:
        return
    label_time_max = pref.fade_time

    # draw text in the 3D View
    blf.size(0, pref.font_size, 72)
    blf.enable(0, blf.SHADOW)
    blf.shadow_offset(0, 1, -1)
    blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)

    font_color_r, font_color_g, font_color_b, font_color_alpha = \
        pref.text_color
    final = 0
    row_count = len(cls.events)

    keypos_x = pos_x

    if pref.mouse_position == 'left':
        keypos_x += mouse_size * MOUSE_RATIO * 1.7
    if pref.mouse != 'icon':
        keypos_x -= mouse_size * MOUSE_RATIO
    if pref.mouse_position == 'right' and pref.mouse != 'icon':
        keypos_x = pos_x

    shift = 0

    # we want to make sure we can shift vertically the text if the mouse is
    # big, but don't care if aligned to right
    if mouse_size > font_size * row_count and \
            not pref.mouse_position == 'right':
        shift = (mouse_size - font_size * row_count) / 2

    text_width, text_height = 0, 0
    row_count = 0

    for i, (t, event_type, mods, count) in enumerate(cls.events):
        label_time = time.time() - t
        # only display key-presses of last 2 seconds
        if label_time > (label_time_max / 1.2):
            blf.blur(0, 1)
        if label_time > (label_time_max / 1.1):
            blf.blur(0, 3)
        keypos_y = pos_y + shift + font_size * (i + 0.1)

        blf.position(0, keypos_x, keypos_y, 0)
        alpha = min(1.0, max(0.0, label_time_max * (label_time_max -
                                                    label_time)))
        bgl.glColor4f(font_color_r, font_color_g, font_color_b,
                      font_color_alpha * alpha)
        text = key_to_text(event_type, mods, count)
        blf.draw(0, text)
        text_width, text_height = get_bounding_box(text_width, text_height,
                                                   text)
        row_count += 1

    # remove blurriness 

    # disable shadows so they don't appear all over blender
    blf.blur(0, 0)
    blf.disable(0, blf.SHADOW)

    # draw graphical representation of the mouse
    if pref.mouse == 'icon':
        for shape in ["mouse", "left_button", "middle_button", "right_button"]:
            draw_mouse(context, shape, "outline", font_color_alpha * 0.4)

        for i, (t, mouse_event) in enumerate(cls.mouse_events):
            click_time = time.time() - t
            shape = map_mouse_event(mouse_event)
            if shape:
                alpha = min(1.0, max(0.0, 2 * (2 - click_time)))
                draw_mouse(context, shape, "filled", alpha)


def draw_modifiers(cls, context, pos_x, pos_y):
    pref = ScreenCastKeysPreferences.get_prefs()
    font_color_r, font_color_g, font_color_b, font_color_alpha = pref.text_color

    keys = []
    active_window = mm.active_window(context)
    if active_window:
        event = cls.window_event[active_window.as_pointer()]
        if event.shift:
            keys.append('Shift')
        if event.ctrl:
            keys.append('Ctrl')
        if event.alt:
            keys.append('Alt')
        if event.oskey:
            keys.append('Cmd')

    blf.size(0, pref.font_size, 54)
    text = ' + '.join(keys)
    if text:
        _, th = blf.dimensions(0, text)
        pos_y -= th + 5
    else:
        _, th = blf.dimensions(0, 'Shift + Ctrl + Alt + Cmd')
        pos_y -= th + 5
    if text:
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
        blf.position(0, pos_x - 14, pos_y, 0)
        bgl.glColor4f(font_color_r, font_color_g, font_color_b,
                      font_color_alpha * 0.8)
        blf.draw(0, text)
        blf.disable(0, blf.SHADOW)
    return pos_y


def draw_last_operator(context, pos_x, pos_y):
    wm = context.window_manager
    pref = ScreenCastKeysPreferences.get_prefs()
    font_color_r, font_color_g, font_color_b, font_color_alpha = pref.text_color

    if wm.operators:
        last_operator = wm.operators[-1].bl_label
        text = "Last: %s" % last_operator
        blf.enable(0, blf.SHADOW)
        blf.shadow_offset(0, 1, -1)
        blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
        blf.size(0, pref.font_size, 36)
        _, th = blf.dimensions(0, text)
        pos_y -= th + 5
        blf.position(0, pos_x - 14, pos_y, 0)
        bgl.glColor4f(font_color_r, font_color_g, font_color_b,
                      font_color_alpha * 0.8)
        blf.draw(0, text)
        blf.disable(0, blf.SHADOW)
    return pos_y


def draw_timer(cls, context, pos_x, pos_y):
    pref = ScreenCastKeysPreferences.get_prefs()
    # calculate overall time
    t = int(time.time() - cls.overall_time)
    overall_time = datetime.timedelta(seconds=t)

    pos_x = context.region.width - (pref.timer_size * 12) + 12
    pos_y = 10

    # draw time
    blf.size(0, pref.timer_size, 72)
    blf.position(0, pos_x, pos_y, 0)
    bgl.glColor4f(*pref.timer_color)
    blf.draw(0, "Elapsed Time: %s" % overall_time)


def draw_callback_px_box(cls, context, event_text):
    pref = ScreenCastKeysPreferences.get_prefs()

    if not mm.is_running(context):
        return

    font_size = pref.font_size
    mouse_size = pref.mouse_size

    if pref.mouse_position == 'right':
        mouse_size = 25

    box_draw = pref.box_draw
    pos_x, pos_y = get_display_location(context)
    if pos_x == pos_y == -1:
        return

    # get text-width/height to resize the box  blf.size(0, pref.font_size, 72)
    box_width, box_height = pref.box_width, 0
    row_count = 0
    box_hide = pref.box_hide

    for i, (t, event_type, mods, count) in enumerate(cls.events):
        # only display key-presses of last 4 seconds
        text = key_to_text(event_type, mods, count)
        box_width, box_height = get_bounding_box(box_width, box_height,
                                                 text)
        row_count += 1
        box_hide = False

    # Got the size right, now draw box using proper colors
    box_color_r, box_color_g, box_color_b, box_color_alpha = pref.box_color

    if box_draw and not box_hide:
        padding_x = 16
        padding_y = 12
        x0 = max(0, pos_x - padding_x)
        y0 = max(0, pos_y - padding_y)
        x1 = pos_x + box_width + mouse_size * MOUSE_RATIO * 1.3 + padding_x
        y1 = pos_y + max(mouse_size, font_size * row_count) + padding_y
        positions = [[x0, y0], [x0, y1], [x1, y1], [x1, y0]]
        settings = [[bgl.GL_QUADS, min(0.0, box_color_alpha)],
                    [bgl.GL_LINE_LOOP, min(0.0, box_color_alpha)]]

        for mode, box_alpha in settings:
            bgl.glEnable(bgl.GL_BLEND)
            bgl.glBegin(mode)
            bgl.glColor4f(box_color_r, box_color_g, box_color_b,
                          box_color_alpha)
            for v1, v2 in positions:
                bgl.glVertex2f(v1, v2)
            bgl.glEnd()

    py = pos_y - 12
    if pref.show_modifiers:
        py = draw_modifiers(cls, context, pos_x, py)

    if pref.show_operator:
        draw_last_operator(context, pos_x, py)

    if pref.timer_show:
        draw_timer(cls, context, pos_x, pos_y)


def key_to_text(event_type, mods, count):
    text = ' + '.join(list(mods) + [event_type])
    if count > 1:
        text += ' x' + str(count)
    return text


def make_event_text(cls, context):
    pref = ScreenCastKeysPreferences.get_prefs()

    # cleanup
    cur_time = time.time()
    for i, (t, event_type, mods, count) in enumerate(cls.events):
        if cur_time - t > pref.fade_time:
            cls.events[i:] = []
            break
    for i, (t, mouse_event) in enumerate(cls.mouse_events):
        click_time = time.time() - t
        if click_time >= 2.0:
            cls.mouse_events[i:] = []
            break

    # make text
    ls = []
    for t, event_type, mods, count in cls.events:
        text = ' + '.join(list(mods) + [event_type])
        if count > 1:
            text += ' x' + str(count)
        ls.append(text)
    return ls


def draw_callback_px(cls, context):
    if not mm.is_running(context):
        return
    window = context.window
    space = context.space_data
    if window != cls.window or space != cls.space:
        return
    # pos_x, pos_y = get_display_location(context)
    # if pos_x == pos_y == -1:
    #     return
    event_text = make_event_text(cls, context)
    draw_callback_px_box(cls, context, event_text)
    draw_callback_px_text(cls, context)


def invoke_callback(context, event, dst, src):
    window = context.window
    dst.__class__.window_event[window.as_pointer()] = event


mm = ModalHandlerManager('view3d.screencast_keys', callback=invoke_callback)


class ScreencastKeysStatus(bpy.types.Operator):
    bl_idname = "view3d.screencast_keys"
    bl_label = "Screencast Keys"
    bl_description = "Display keys pressed in the 3D View"
    last_activity = 'NONE'

    _handle = None
    _timer = None

    events = []  # [[time, event_type, [modifier_keys, count]], ...]
    mouse_events = []  # [[time, event_type], ...]

    prev_time = 0.0  # time of lst event
    overall_time = 0.0

    window_event = {}  # {Window.as_pointer(): Event, ...}

    TIMER_STEP = 0.075

    # 描画対象
    window = None
    space = None  # AreaはCtrl+UP_ARROWで切り替えた際に一致しないのでSpaceを使う

    @classmethod
    def timer_add(cls, context, window):
        wm = context.window_manager
        if cls._timer:
            wm.event_timer_remove(cls._timer)
        cls._timer = wm.event_timer_add(cls.TIMER_STEP, window)

    @classmethod
    def handle_add(cls, context):
        cls._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px, (cls, context), 'WINDOW', 'POST_PIXEL')
        cls.timer_add(context, context.window)

    @classmethod
    def handle_remove(cls, context):
        if cls._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle, 'WINDOW')
            cls._handle = None
        if cls._timer is not None:
            context.window_manager.event_timer_remove(cls._timer)
            cls._timer = None

    @classmethod
    def test_window_space(cls, context):
        # 描画対象の3DViewが無くてもまだ生きているwindowからの切り替えは行わない
        wm = context.window_manager
        windows = list(wm.windows)
        if cls.window:
            for win in windows:
                if win == cls.window:
                    break
            else:
                cls.window = None
        if cls.window:
            if cls.space:
                for area in cls.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        if area.spaces.active == cls.space:
                            break
                else:
                    cls.space = None
            if not cls.space:
                for area in cls.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        cls.space = area.spaces.active
                        return
        else:
            cls.space = None
            for win in windows:
                for area in win.screen.areas:
                    if area.type == 'VIEW_3D':
                        cls.window = win
                        cls.space = area.spaces.active
                        cls.timer_add(context, cls.window)
                        return

    @mm.modal
    def modal(self, context, event):
        pref = ScreenCastKeysPreferences.get_prefs()

        ignore_event = False
        if event.type in ('MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'):
            if (event.mouse_x == event.mouse_prev_x and
                    event.mouse_y == event.mouse_prev_y):
                ignore_event = True
        elif event.type == 'WINDOW_DEACTIVATE':
            ignore_event = True

        # if not ignore_event:
        self.test_window_space(context)

        if (not (event.type.startswith('TIMER') or
                 event.type in ('MOUSEMOVE', 'INBETWEEN_MOUSEMOVE') or
                 ignore_event) or
                time.time() - self.prev_time > self.TIMER_STEP):
            if self.window and self.space:
                for area in self.window.screen.areas:
                    if area.spaces.active == self.space:
                        area.tag_redraw()
                        self.prev_time = time.time()
                        break

        if event.type.startswith('TIMER') or ignore_event:
            # no input, so no need to change the display
            return {'PASS_THROUGH'}

        # keys that shouldn't show up in the 3D View
        mouse_keys = ['MIDDLEMOUSE', 'LEFTMOUSE',
                      'RIGHTMOUSE', 'WHEELDOWNMOUSE', 'WHEELUPMOUSE']
        ignore_keys = ['LEFT_SHIFT', 'RIGHT_SHIFT', 'LEFT_ALT',
                       'RIGHT_ALT', 'LEFT_CTRL', 'RIGHT_CTRL', 'OSKEY',
                       'TIMER',
                       'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE']
        if pref.mouse != 'text':
            ignore_keys.extend(mouse_keys)

        numbers = {'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3',
                   'FOUR': '4', 'FIVE': '5', 'SIX': '6', 'SEVEN': '7',
                   'EIGHT': '8', 'NINE': '9'}
        if event.value == 'PRESS' or (event.value == 'RELEASE' and
                self.last_activity == 'KEYBOARD' and event.type in mouse_keys):
            # add key-press to display-list
            mods = []
            if event.shift:
                mods.append("Shift")
            if event.ctrl:
                mods.append("Ctrl")
            if event.alt:
                mods.append("Alt")
            if event.oskey:
                mods.append("Cmd")

            if event.type not in ignore_keys:
                event_type = event.type
                if event_type in numbers:
                    event_type = numbers[event_type]
                # print("Recorded as key")
                if (self.events and self.events[0][1] == event_type and
                        self.events[0][2] == mods):
                    self.events[0][3] += 1
                    self.events[0][0] = time.time()
                else:
                    self.events.insert(0, [time.time(), event_type, mods, 1])

            elif event.type in mouse_keys and pref.mouse == 'icon':
                # print("Recorded as mouse press")
                self.mouse_events.insert(0, [time.time(), event.type])

            if event.type in mouse_keys:
                self.last_activity = 'MOUSE'
            else:
                self.last_activity = 'KEYBOARD'
            # print("Last activity set to:", self.last_activity)

        return {'PASS_THROUGH'}

    # def cancel(self, context):
    #     self.handle_remove(context)

    def redraw_all_ui_panels(self, context):
        wm = context.window_manager
        for win in wm.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            region.tag_redraw()

    def init(self):
        cls = self.__class__
        cls.events.clear()
        cls.mouse_events.clear()
        cls.overall_time = time.time()
        cls.prev_time = time.time()
        cls.window_event.clear()

    @mm.invoke
    def invoke(self, context, event):
        cls = self.__class__
        if mm.is_running(context):
            if cls.window != context.window or cls.space != context.space_data:
                # 描画対象のwindow,spaceの切り替え
                if cls.window and cls.space:
                    for area in cls.window.screen.areas:
                        if area.spaces.active == cls.space:
                            area.tag_redraw()
                cls.window = context.window
                if context.area.type == 'VIEW_3D':
                    cls.space = context.space_data
                else:
                    cls.space = None
                self.test_window_space(context)
                return {'CANCELLED', 'PASS_THROUGH'}, False
            else:
                # 同window,同spaceで呼び出された場合は終了
                self.handle_remove(context)
                if cls.window and cls.space:
                    for area in cls.window.screen.areas:
                        if area.spaces.active == cls.space:
                            area.tag_redraw()
                self.redraw_all_ui_panels(context)
            return {'CANCELLED'}
        else:
            if context.area.type == 'VIEW_3D':
                # operator is called for the first time, start everything
                self.init()
                self.window_event[context.window.as_pointer()] = event
                self.handle_add(context)
                context.window_manager.modal_handler_add(self)
                self.redraw_all_ui_panels(context)
                return {'RUNNING_MODAL'}
            else:
                self.report({'WARNING'},
                            "3D View not found, can't run Screencast Keys")
                return {'CANCELLED'}


class ScreencastKeysTimerReset(bpy.types.Operator):
    """Reset Timer"""
    bl_idname = "view3d.screencast_keys_timer_reset"
    bl_label = "Reset Timer"
    bl_description = "Set the timer back to zero"

    def execute(self, context):
        ScreencastKeysStatus.overall_time = time.time()
        return {'FINISHED'}


# properties used by the script
class ScreenCastKeysPreferences(
        AddonPreferences,
        bpy.types.PropertyGroup if '.' in __name__ else
        bpy.types.AddonPreferences):
    bl_idname = __name__

    pos_x = bpy.props.IntProperty(
        name="Position X",
        description="Margin on the X axis",
        default=3,
        min=0,
        max=100)
    pos_y = bpy.props.IntProperty(
        name="Position Y",
        description="Margin on the Y axis",
        default=10,
        min=0,
        max=100)
    font_size = bpy.props.IntProperty(
        name="Text Size",
        description="Text size displayed on 3D View",
        default=24, min=10, max=150)
    mouse_size = bpy.props.IntProperty(
        name="Mouse Size",
        description="Mouse size displayed on 3D View",
        default=33, min=10, max=150)
    text_color = bpy.props.FloatVectorProperty(
        name="Text / Icon Color",
        description="Color for the text and mouse icon",
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.1,
        max=1,
        subtype='COLOR_GAMMA',
        size=4)
    box_color = bpy.props.FloatVectorProperty(
        name="Box Color",
        description="Box color",
        default=(0.0, 0.0, 0.0, 0.3),
        min=0,
        max=1,
        subtype='COLOR_GAMMA',
        size=4)
    box_width = bpy.props.IntProperty(
        name="Box Width",
        description="Box default width (resizes with text if needed)",
        default=0,
        min=0,
        max=2048,
        soft_max=1024)
    mouse = bpy.props.EnumProperty(
        items=(("none", "No Mouse", "Don't display mouse events"),
               ("icon", "Icon", "Display graphical representation of "
                                "the mouse"),
               ("text", "Text", "Display mouse events as text lines")),
        name="Mouse Display",
        description="Display mouse events",
        default='icon')
    mouse_position = bpy.props.EnumProperty(
        items=(("left", "Left", "Align to the left"),
               ("right", "Right", "Align to the right")),
        name="Icon Position",
        description="Align the mouse icon on the 3D View",
        default='left')
    box_draw = bpy.props.BoolProperty(
        name="Display Box",
        description="Display a bounding box behind the text",
        default=True)
    box_hide = bpy.props.BoolProperty(
        name="Hide Box",
        description="Hide the box when no key is pressed",
        default=False)
    fade_time = bpy.props.FloatProperty(
        name="Fade Out Time",
        description="Time in seconds for keys to last on screen",
        default=3.5,
        min=0.5,
        max=10.0,
        soft_max=5.0,
        step=10,
        subtype='TIME')
    show_modifiers = bpy.props.BoolProperty(
        name="Display Modifier Keys",
        description="Display holding modifier keys",
        default=True)
    show_operator = bpy.props.BoolProperty(
        name="Display Last Operator",
        description="Display the last operator used",
        default=True)
    timer_show = bpy.props.BoolProperty(
        name="Display Timer",
        description="Counter of the elapsed time in H:MM:SS "
                    "since the script started",
        default=False)
    timer_size = bpy.props.IntProperty(
        name="Time Size",
        description="Time size displayed on 3D View",
        default=12, min=8, max=100)
    timer_color = bpy.props.FloatVectorProperty(
        name="Time Color",
        description="Color for the time display",
        default=(1.0, 1.0, 1.0, 0.3),
        min=0,
        max=1,
        subtype='COLOR_GAMMA',
        size=4)

    def draw(self, context):
        pref = ScreenCastKeysPreferences.get_prefs()
        layout = self.layout
        split = layout.split()

        # 1
        column = split.column()

        sp = column.split()
        col = sp.column()
        sub = col.column(align=True)
        sub.label(text="Size:")
        sub.prop(pref, "font_size", text="Text")
        sub.prop(pref, "mouse_size", text="Mouse")

        col = sp.column()
        sub = col.column(align=True)
        sub.label(text="Position:")
        sub.prop(pref, "pos_x", text="X")
        sub.prop(pref, "pos_y", text="Y")

        row = column.row(align=True)
        row.prop(pref, "text_color")
        row = column.row(align=True)
        row.prop(pref, "fade_time")

        # 2
        column = split.column()

        row = column.row(align=True)
        row.prop(pref, "mouse", text="Mouse")
        row = column.row(align=True)
        row.enabled = pref.mouse == 'icon'
        row.prop(pref, "mouse_position", expand=True)

        column.label(text="Display:")
        row = column.row(align=True)
        row.prop(pref, "box_draw", text="Box")
        row = column.row(align=True)
        row.active = pref.box_draw
        row.prop(pref, "box_color", text="")
        row.prop(pref, "box_hide", text="Hide")
        row = column.row(align=True)
        row.active = pref.box_draw
        row.prop(pref, "box_width")
        row = column.row(align=True)
        row.prop(pref, "show_modifiers", text="Modifier Keys")
        row = column.row(align=True)
        row.prop(pref, "show_operator", text="Last Operator")

        # 3
        column = split.column()
        sp = column.split()

        col = sp.column()
        sub = col.column(align=True)
        sub.prop(pref, "timer_show", text="Time")
        col = sp.column()
        sub = col.column(align=True)
        sub.active = pref.timer_show
        sub.prop(pref, "timer_color", text="")

        row = column.row(align=True)
        row.enabled = pref.timer_show
        row.prop(pref, "timer_size")
        row = column.row(align=True)
        row.enabled = pref.timer_show
        row.operator("view3d.screencast_keys_timer_reset", text="Reset")


# defining the panel
class OBJECT_PT_keys_status(bpy.types.Panel):
    bl_label = "Screencast Keys"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        pref = ScreenCastKeysPreferences.get_prefs()
        layout = self.layout

        if not mm.is_running(context):
            layout.operator("view3d.screencast_keys", text="Start Display",
                            icon="PLAY")
        else:
            cls = ScreencastKeysStatus
            if cls.window != context.window or cls.space != context.space_data:
                text = "Switch Display"
                icon = "PLAY"
            else:
                text = "Stop Display"
                icon = "PAUSE"
            layout.operator("view3d.screencast_keys", text=text, icon=icon)

            split = layout.split()

            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Size:")
            sub.prop(pref, "font_size", text="Text")
            sub.prop(pref, "mouse_size", text="Mouse")

            col = split.column()
            sub = col.column(align=True)
            sub.label(text="Position:")
            sub.prop(pref, "pos_x", text="X")
            sub.prop(pref, "pos_y", text="Y")

            row = layout.row(align=True)
            row.prop(pref, "text_color")
            row = layout.row(align=True)
            row.prop(pref, "fade_time")

            layout.separator()

            row = layout.row(align=True)
            row.prop(pref, "mouse", text="Mouse")
            row = layout.row(align=True)
            row.enabled = pref.mouse == 'icon'
            row.prop(pref, "mouse_position", expand=True)

            layout.label(text="Display:")
            row = layout.row(align=True)
            row.prop(pref, "box_draw", text="Box")
            row = layout.row(align=True)
            row.active = pref.box_draw
            row.prop(pref, "box_color", text="")
            row.prop(pref, "box_hide", text="Hide")
            row = layout.row(align=True)
            row.active = pref.box_draw
            row.prop(pref, "box_width")
            row = layout.row(align=True)
            row.prop(pref, "show_modifiers", text="Modifier Keys")
            row = layout.row(align=True)
            row.prop(pref, "show_operator", text="Last Operator")

            split = layout.split()

            col = split.column()
            sub = col.column(align=True)
            sub.prop(pref, "timer_show", text="Time")
            col = split.column()
            sub = col.column(align=True)
            sub.active = pref.timer_show
            sub.prop(pref, "timer_color", text="")

            row = layout.row(align=True)
            row.enabled = pref.timer_show
            row.prop(pref, "timer_size")
            row = layout.row(align=True)
            row.enabled = pref.timer_show
            row.operator("view3d.screencast_keys_timer_reset", text="Reset")


classes = (ScreencastKeysStatus,
           ScreencastKeysTimerReset,
           OBJECT_PT_keys_status,
           ScreenCastKeysPreferences)


# store keymaps here to access after registration
addon_keymaps = []


def register():
    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('view3d.screencast_keys', 'C', 'PRESS',
                                  shift=True, alt=True)
        addon_keymaps.append((km, kmi))




def unregister():
    # incase its enabled
    ScreencastKeysStatus.handle_remove(bpy.context)

    for c in classes:
        bpy.utils.unregister_class(c)

    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
