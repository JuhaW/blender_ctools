# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import platform
from ctypes import CDLL, Structure, POINTER, cast, \
    c_char, c_char_p, c_double, c_float, c_short, c_int, c_void_p, \
    py_object, c_uint


def fields(*field_items):
    _fields_ = []

    member_type = None
    for item in field_items:
        if isinstance(item, (list, tuple)):
            t = None
            i = 0
            for sub_item in item:
                if not isinstance(sub_item, str):
                    t = sub_item
                    i += 1
            if len(item) < 2 or t is None:
                raise ValueError('tuple/list内には型とメンバ名が必要')
            if i != 1:
                raise ValueError('tuple/list内には型は一個のみ必要')
            for sub_item in item:
                if isinstance(sub_item, str):
                    _fields_.append((sub_item, t))
        elif isinstance(item, str):
            if member_type is None:
                raise ValueError('最初の要素は型でないといけない')
            _fields_.append((item, member_type))
        else:
            member_type = item

    return _fields_


class ListBase(Structure):
    """source/blender/makesdna/DNA_listBase.h: 59"""
    _fields_ = fields(
        c_void_p, 'first', 'last',
    )


class rcti(Structure):
    """DNA_vec_types.h: 86
    NOTE: region.width == ar.winrct.xmax - ar.winrct.xmin + 1
    """
    _fields_ = fields(
        c_int, 'xmin', 'xmax',
        c_int, 'ymin', 'ymax',
    )


class rctf(Structure):
    """DNA_vec_types.h: 92"""
    _fields_ = fields(
        c_float, 'xmin', 'xmax',
        c_float, 'ymin', 'ymax',
    )


class View2D(Structure):
    """DNA_view2d_types.h: 40"""

View2D._fields_ = fields(
    rctf, 'tot', 'cur',  # tot - area that data can be drawn in cur - region of tot that is visible in viewport
    rcti, 'vert', 'hor',  # vert - vertical scrollbar region hor - horizontal scrollbar region
    rcti, 'mask',  # region (in screenspace) within which 'cur' can be viewed

    c_float * 2, 'min', 'max',  # min/max sizes of 'cur' rect (only when keepzoom not set)
    c_float, 'minzoom', 'maxzoom',  # allowable zoom factor range (only when (keepzoom & V2D_LIMITZOOM)) is set

    c_short, 'scroll',  # scroll - scrollbars to display (bitflag)
    c_short, 'scroll_ui',  # scroll_ui - temp settings used for UI drawing of scrollers

    c_short, 'keeptot',  # keeptot - 'cur' rect cannot move outside the 'tot' rect?
    c_short, 'keepzoom',  # keepzoom - axes that zooming cannot occur on, and also clamp within zoom-limits
    c_short, 'keepofs',  # keepofs - axes that translation is not allowed to occur on

    c_short, 'flag',  # settings
    c_short, 'align',  # alignment of content in totrect

    c_short, 'winx', 'winy',  # storage of current winx/winy values, set in UI_view2d_size_update
    c_short, 'oldwinx', 'oldwiny',  # storage of previous winx/winy values encountered by UI_view2d_curRect_validate(), for keepaspect

    c_short, 'around',  # pivot point for transforms (rotate and scale)

    POINTER(c_float), 'tab_offset',  # different offset per tab, for buttons
    c_int, 'tab_num',  # number of tabs stored
    c_int, 'tab_cur',  # current tab

    # animated smooth view
    c_void_p, 'sms',  # struct SmoothView2DStore
    c_void_p, 'smooth_timer',  # struct wmTimer
)


class ARegionType(Structure):
    """BKE_screen.h: 116"""

ARegionType._fields_ = fields(
    POINTER(ARegionType), 'next', 'prev',

    c_int, 'regionid',  # unique identifier within this space, defines RGN_TYPE_xxxx

    # add handlers, stuff you only do once or on area/region type/size changes
    c_void_p, 'init',
    # exit is called when the region is hidden or removed
    c_void_p, 'exit',
    # draw entirely, view changes should be handled here
    c_void_p, 'draw',
    # contextual changes should be handled here
    c_void_p, 'listener',

    c_void_p, 'free',

    # split region, copy data optionally
    c_void_p, 'duplicate',

    # register operator types on startup
    c_void_p, 'operatortypes',
    # add own items to keymap
    c_void_p, 'keymap',
    # allows default cursor per region
    c_void_p, 'cursor',

    # return context data
    c_void_p, 'context',

    # custom drawing callbacks
    ListBase, 'drawcalls',

    # panels type definitions
    ListBase, 'paneltypes',

    # header type definitions
    ListBase, 'headertypes',

    # hardcoded constraints, smaller than these values region is not visible
    c_int, 'minsizex', 'minsizey',
    # when new region opens (region prefsizex/y are zero then
    c_int, 'prefsizex', 'prefsizey',
    # default keymaps to add
    c_int, 'keymapflag',
    # return without drawing. lock is set by region definition, and copied to do_lock by render. can become flag
    c_short, 'do_lock', 'lock',
    # call cursor function on each move event
    c_short, 'event_cursor',
)


class SpaceType(Structure):
    """BKE_screen.h: 66"""

SpaceType._fields_ = fields(
    # struct SpaceType *next, *prev
    #
    # char name[BKE_ST_MAXNAME]                  # for menus
    # int spaceid                                # unique space identifier
    # int iconid                                 # icon lookup for menus
    #
    # # initial allocation, after this WM will call init() too
    # struct SpaceLink    *(*new)(const struct bContext *C)
    # # not free spacelink itself
    # void (*free)(struct SpaceLink *)
    #
    # # init is to cope with file load, screen (size) changes, check handlers
    # void (*init)(struct wmWindowManager *, struct ScrArea *)
    # # exit is called when the area is hidden or removed
    # void (*exit)(struct wmWindowManager *, struct ScrArea *)
    # # Listeners can react to bContext changes
    # void (*listener)(struct bScreen *sc, struct ScrArea *, struct wmNotifier *)
    #
    # # refresh context, called after filereads, ED_area_tag_refresh()
    # void (*refresh)(const struct bContext *, struct ScrArea *)
    #
    # # after a spacedata copy, an init should result in exact same situation
    # struct SpaceLink    *(*duplicate)(struct SpaceLink *)
    #
    # # register operator types on startup
    # void (*operatortypes)(void)
    # # add default items to WM keymap
    # void (*keymap)(struct wmKeyConfig *)
    # # on startup, define dropboxes for spacetype+regions
    # void (*dropboxes)(void)
    #
    # # return context data
    # int (*context)(const struct bContext *, const char *, struct bContextDataResult *)
    #
    # # region type definitions
    # ListBase regiontypes
    #
    # # tool shelf definitions
    # ListBase toolshelf
    #
    # # read and write...
    #
    # # default keymaps to add
    # int keymapflag
)


class ScrArea(Structure):
    """DNA_screen_types.h: 202"""

ScrArea._fields_ = fields(
    POINTER(ScrArea), 'next', 'prev',

    c_void_p, 'v1', 'v2', 'v3', 'v4',  # ordered (bl, tl, tr, br)

    c_void_p, 'full',  # <bScreen> if area==full, this is the parent

    rcti, 'totrct',  # rect bound by v1 v2 v3 v4

    c_char, 'spacetype', 'butspacetype',  # SPACE_..., butspacetype is button arg
    c_short, 'winx', 'winy',  # size

    c_short, 'headertype',  # OLD! 0=no header, 1= down, 2= up
    c_short, 'do_refresh',  # private, for spacetype refresh callback
    c_short, 'flag',
    c_short, 'region_active_win',  # index of last used region of 'RGN_TYPE_WINDOW'
                                   # runtime variable, updated by executing operators
    c_char, 'temp', 'pad',

    POINTER(SpaceType), 'type',  # callbacks for this space type

    ListBase, 'spacedata',  # SpaceLink
    ListBase, 'regionbase',  # ARegion
    ListBase, 'handlers',  # wmEventHandler

    ListBase, 'actionzones',  # AZone
)


class ARegion(Structure):
    """DNA_screen_types.h: 229"""

ARegion._fields_ = fields(
    POINTER(ARegion), 'next', 'prev',

    View2D, 'v2d',  # 2D-View scrolling/zoom info (most regions are 2d anyways)
    rcti, 'winrct',  # coordinates of region
    rcti, 'drawrct',  # runtime for partial redraw, same or smaller than winrct
    c_short, 'winx', 'winy',  # size

    c_short, 'swinid',
    c_short, 'regiontype',  # window, header, etc. identifier for drawing
    c_short, 'alignment',  # how it should split
    c_short, 'flag',  # hide, ...

    c_float, 'fsize',  # current split size in float (unused)
    c_short, 'sizex', 'sizey',  # current split size in pixels (if zero it uses regiontype)

    c_short, 'do_draw',  # private, cached notifier events
    c_short, 'do_draw_overlay',  # private, cached notifier events
    c_short, 'swap',  # private, indicator to survive swap-exchange
    c_short, 'overlap',  # private, set for indicate drawing overlapped
    c_short, 'flagfullscreen',  # temporary copy of flag settings for clean fullscreen
    c_short, 'pad',

    POINTER(ARegionType), 'type',  # callbacks for this region type

    ListBase, 'uiblocks',  # uiBlock
    ListBase, 'panels',  # Panel
    ListBase, 'panels_category_active',  # Stack of panel categories
    ListBase, 'ui_lists',  # uiList
    ListBase, 'ui_previews',  # uiPreview
    ListBase, 'handlers',  # wmEventHandler
    ListBase, 'panels_category',  # Panel categories runtime

    c_void_p, 'regiontimer',  # <struct wmTimer>  # blend in/out

    c_char_p, 'headerstr',  # use this string to draw info
    c_void_p, 'regiondata',  # XXX 2.50, need spacedata equivalent?
)


class RegionView3D(Structure):
    """DNA_view3d_types.h: 86"""

RegionView3D._fields_ = fields(
    c_float * 4 * 4, 'winmat',  # GL_PROJECTION matrix
    c_float * 4 * 4, 'viewmat',  # GL_MODELVIEW matrix
    c_float * 4 * 4, 'viewinv',  # inverse of viewmat
    c_float * 4 * 4, 'persmat',  # viewmat*winmat
    c_float * 4 * 4, 'persinv',  # inverse of persmat
    c_float * 4, 'viewcamtexcofac',  # offset/scale for camera glsl texcoords

    # viewmat/persmat multiplied with object matrix, while drawing and selection
    c_float * 4 * 4, 'viewmatob',
    c_float * 4 * 4, 'persmatob',

    # user defined clipping planes
    c_float * 4 * 6, 'clip',  # clip[6][4]
    c_float * 4 * 6, 'clip_local',  # clip_local[6][4]  clip in object space, means we can test for clipping in editmode without first going into worldspace
    c_void_p, 'clipbb',  # struct BoundBox

    POINTER(RegionView3D), 'localvd',  # allocated backup of its self while in localview
    c_void_p, 'render_engine',  # struct RenderEngine
    c_void_p, 'depths',  # struct ViewDepths
    c_void_p, 'gpuoffscreen',

    # animated smooth view
    c_void_p, 'sms',  # struct SmoothView3DStore
    c_void_p, 'smooth_timer',  # struct wmTimer

    # transform widget matrix
    c_float * 4 * 4, 'twmat',

    c_float * 4, 'viewquat',  # view rotation, must be kept normalized
    c_float, 'dist',  # distance from 'ofs' along -viewinv[2] vector, where result is negative as is 'ofs'
    c_float, 'camdx', 'camdy',  # camera view offsets, 1.0 = viewplane moves entire width/height
    c_float, 'pixsize',  # runtime only
    c_float * 3, 'ofs',  # view center & orbit pivot, negative of worldspace location, also matches -viewinv[3][0:3] in ortho mode.*/
    c_float, 'camzoom',  # viewport zoom on the camera frame, see BKE_screen_view3d_zoom_to_fac
    c_char, 'is_persp',   # check if persp/ortho view, since 'persp' cant be used for this since
                            # it can have cameras assigned as well. (only set in view3d_winmatrix_set)
    c_char, 'persp',
    c_char, 'view',
    c_char, 'viewlock',
    c_char, 'viewlock_quad',  # options for quadview (store while out of quad view)
    c_char * 3, 'pad',
    c_float * 2, 'ofs_lock',  # normalized offset for locked view: (-1, -1) bottom left, (1, 1) upper right

    c_short, 'twdrawflag',
    c_short, 'rflag',

    # last view (use when switching out of camera view)
    c_float * 4, 'lviewquat',
    c_short, 'lpersp', 'lview',  # lpersp can never be set to 'RV3D_CAMOB'

    c_float, 'gridview',
    c_float * 3, 'tw_idot',  # manipulator runtime: (1 - dot) product with view vector (used to check view alignment)

    # active rotation from NDOF or elsewhere
    c_float, 'rot_angle',
    c_float * 3, 'rot_axis',

    c_void_p, 'compositor',  # struct GPUFX
)


class GPUFXSettings(Structure):
    """DNA_gpu_types.h"""
    _fields_ = fields(
        c_void_p, 'dof',  # GPUDOFSettings
        c_void_p, 'ssao',  # GPUSSAOSettings
        c_char, 'fx_flag',  # eGPUFXFlags
        c_char * 7, 'pad',
        )


class View3D(Structure):
    """DNA_view3d_types.h: 153"""

View3D._fields_ = fields(
    c_void_p, 'next', 'prev',  # struct SpaceLink *next, *prev
    ListBase, 'regionbase',  # storage of regions for inactive spaces
    c_int, 'spacetype',
    c_float, 'blockscale',
    c_short * 8, 'blockhandler',

    c_float * 4, 'viewquat',  # DNA_DEPRECATED
    c_float, 'dist',  # DNA_DEPRECATED

    c_float, 'bundle_size',  # size of bundles in reconstructed data
    c_char, 'bundle_drawtype',  # display style for bundle
    c_char * 3, 'pad',

    c_uint, 'lay_prev',  # for active layer toggle
    c_uint, 'lay_used',  # used while drawing

    c_short, 'persp',  # DNA_DEPRECATED
    c_short, 'view',  # DNA_DEPRECATED

    c_void_p, 'camera', 'ob_centre',  # struct Object
    rctf, 'render_border',

    ListBase, 'bgpicbase',
    c_void_p, 'bgpic',  # <struct BGpic> DNA_DEPRECATED # deprecated, use bgpicbase, only kept for do_versions(...)

    POINTER(View3D), 'localvd',  # allocated backup of its self while in localview

    c_char * 64, 'ob_centre_bone',  # optional string for armature bone to define center, MAXBONENAME

    c_uint, 'lay',
    c_int, 'layact',

    #  * The drawing mode for the 3d display. Set to OB_BOUNDBOX, OB_WIRE, OB_SOLID,
    #  * OB_TEXTURE, OB_MATERIAL or OB_RENDER
    c_short, 'drawtype',
    c_short, 'ob_centre_cursor',        # optional bool for 3d cursor to define center
    c_short, 'scenelock', 'around',
    c_short, 'flag', 'flag2',

    c_float, 'lens', 'grid',
    c_float, 'near', 'far',
    c_float * 3, 'ofs',  #  DNA_DEPRECATED  # XXX deprecated
    c_float * 3, 'cursor',

    c_short, 'matcap_icon',  # icon id

    c_short, 'gridlines',
    c_short, 'gridsubdiv',  # Number of subdivisions in the grid between each highlighted grid line
    c_char, 'gridflag',

    # transform widget info
    c_char, 'twtype', 'twmode', 'twflag',

    c_short, 'flag3',

    # afterdraw, for xray & transparent
    ListBase, 'afterdraw_transp',
    ListBase, 'afterdraw_xray',
    ListBase, 'afterdraw_xraytransp',

    # drawflags, denoting state
    c_char, 'zbuf', 'transp', 'xray',

    c_char, 'multiview_eye',  # multiview current eye - for internal use

    # built-in shader effects (eGPUFXFlags)
    c_char * 4, 'pad3',

    # note, 'fx_settings.dof' is currently _not_ allocated,
    # instead set (temporarily) from camera
    GPUFXSettings, 'fx_settings',

    c_void_p, 'properties_storage',  # Nkey panel stores stuff here (runtime only!)
    c_void_p, 'defmaterial',    # <struct Material> used by matcap now

    # # XXX deprecated?
    # struct bGPdata *gpd  DNA_DEPRECATED        # Grease-Pencil Data (annotation layers)
    # 
    # short usewcol, dummy3[3]
    # 
    #  # multiview - stereo 3d
    # short stereo3d_flag
    # char stereo3d_camera
    # char pad4
    # float stereo3d_convergence_factor
    # float stereo3d_volume_alpha
    # float stereo3d_convergence_alpha
    # 
    # # local grid
    # char localgrid, cursor_snap_grid, dummy[2]
    # float lg_loc[3], dummy2[2] // orign(x,y,z)
    # float lg_quat[4] // rotation(x,y,z)
)


class wmSubWindow(Structure):
    """windowmanager/intern/wm_subwindow.c: 67"""

wmSubWindow._fields_ = fields(
    POINTER(wmSubWindow), 'next', 'prev',
    rcti, 'winrct',
    c_int, 'swinid',
)


class wmEvent(Structure):
    """windowmanager/WM_types.h: 431"""

wmEvent._fields_ = fields(
    POINTER(wmEvent), 'next', 'prev',

    c_short, 'type',
    c_short, 'val',
    c_int, 'x', 'y',
    c_int * 2, 'mval',
    c_char * 6, 'utf8_buf',

    c_char, 'ascii',
    c_char, 'pad',

    c_short, 'prevtype',
    c_short, 'prevval',
    c_int, 'prevx', 'prevy',
    c_double, 'prevclick_time',
    c_int, 'prevclickx', 'prevclicky',

    c_short, 'shift', 'ctrl', 'alt', 'oskey',
    c_short, 'keymodifier',

    c_short, 'check_click',

    c_char_p, 'keymap_idname',  # const char

    c_void_p, 'tablet_data',  # const struct wmTabletData

    c_short, 'custom',
    c_short, 'customdatafree',
    c_int, 'pad2',
    c_void_p, 'customdata',
)


class wmOperatorType(Structure):
    """source/blender/windowmanager/WM_types.h: 518"""
    _fields_ = fields(
        c_char_p, 'name',
        c_char_p, 'idname',
        c_char_p, 'translation_context',
        c_char_p, 'description',
        # 以下略
    )


class wmOperator(Structure):
    """source/blender/makesdna/DNA_windowmanager_types.h: 344"""

wmOperator._fields_ = fields(
    POINTER(wmOperator), 'next', 'prev',

    c_char * 64, 'idname',
    c_void_p, 'properties',  # IDProperty

    POINTER(wmOperatorType), 'type',
    c_void_p, 'customdata',
    py_object, 'py_instance',  # python stores the class instance here

    c_void_p, 'ptr',  # PointerRNA
    c_void_p, 'reports',  # ReportList

    ListBase, 'macro',
    POINTER(wmOperator), 'opm',
    c_void_p, 'layout',  # uiLayout
    c_short, 'flag', c_short * 3, 'pad',
)


class wmEventHandler(Structure):
    """source/blender/windowmanager/wm_event_system.h: 45"""

wmEventHandler._fields_ = fields(
    POINTER(wmEventHandler), 'next', 'prev',

    c_char, 'type',  # WM_HANDLER_DEFAULT, ...
    c_char, 'flag',  # WM_HANDLER_BLOCKING, ...

    # keymap handler
    c_void_p, 'keymap',  # <wmKeyMap> pointer to builtin/custom keymaps
    c_void_p, 'bblocal', 'bbwin',  # <const rcti> optional local and windowspace bb

    # modal operator handler
    POINTER(wmOperator), 'op',  # for derived/modal handlers
    POINTER(ScrArea), 'op_area',  # for derived/modal handlers
    POINTER(ARegion), 'op_region',  # for derived/modal handlers
    c_short, 'op_region_type',  # for derived/modal handlers

    # ui handler
    c_void_p, 'ui_handle',  # <function: wmUIHandlerFunc> callback receiving events
    c_void_p, 'ui_remove',  # <function: wmUIHandlerRemoveFunc> callback when handler is removed
    c_void_p, 'ui_userdata',  # user data pointer
    POINTER(ScrArea), 'ui_area',  # for derived/modal handlers
    POINTER(ARegion), 'ui_region',  # for derived/modal handlers
    POINTER(ARegion), 'ui_menu',  # for derived/modal handlers

    # drop box handler
    POINTER(ListBase), 'dropboxes',
)


class wmWindow(Structure):
    """source/blender/makesdna/DNA_windowmanager_types.h: 175"""

wmWindow._fields_ = fields(
    POINTER(wmWindow), 'next', 'prev',

    c_void_p, 'ghostwin',

    c_void_p, 'screen',  # struct bScreen
    c_void_p, 'newscreen',  # struct bScreen
    c_char * 64, 'screenname',

    c_short, 'posx', 'posy', 'sizex', 'sizey',
    c_short, 'windowstate',
    c_short, 'monitor',
    c_short, 'active',
    c_short, 'cursor',
    c_short, 'lastcursor',
    c_short, 'modalcursor',
    c_short, 'grabcursor',  # GHOST_TGrabCursorMode
    c_short, 'addmousemove',

    c_int, 'winid',

    # internal, lock pie creation from this event until released
    c_short, 'lock_pie_event',
    # exception to the above rule for nested pies, store last pie event for operators
    # that spawn a new pie right after destruction of last pie
    c_short, 'last_pie_event',

    POINTER(wmEvent), 'eventstate',

    POINTER(wmSubWindow), 'curswin',

    c_void_p, 'tweak',  # struct wmGesture

    c_void_p, 'ime_data',  # struct wmIMEData

    c_int, 'drawmethod', 'drawfail',
    ListBase, 'drawdata',

    ListBase, 'queue',
    ListBase, 'handlers',
    ListBase, 'modalhandlers',  # wmEventHandler

    ListBase, 'subwindows',
    ListBase, 'gesture',

    c_void_p, 'stereo3d_format',  # struct Stereo3dFormat
)


class SpaceText(Structure):
    """source/blender/makesdna/DNA_space_types.h: 981"""

SpaceText._fields_ = fields(
    POINTER(SpaceText), 'next', 'prev',
    ListBase, 'regionbase',  # storage of regions for inactive spaces
    c_int, 'spacetype',
    c_float, 'blockscale',  # DNA_DEPRECATED
    c_short * 8, 'blockhandler',  # DNA_DEPRECATED

    c_void_p, 'text',  # struct Text

    c_int, 'top', 'viewlines',
    c_short, 'flags', 'menunr',

    c_short, 'lheight',  # user preference, is font_size!
    c_char, 'cwidth', 'linenrs_tot',  # runtime computed, character width and the number of chars to use when showing line numbers
    c_int, 'left',
    c_int, 'showlinenrs',
    c_int, 'tabnumber',

    c_short, 'showsyntax',
    c_short, 'line_hlight',
    c_short, 'overwrite',
    c_short, 'live_edit',  # run python while editing, evil
    c_float, 'pix_per_line',

    rcti, 'txtscroll', 'txtbar',

    c_int, 'wordwrap', 'doplugins',

    c_char * 256, 'findstr',  # ST_MAX_FIND_STR
    c_char * 256, 'replacestr',  # ST_MAX_FIND_STR

    c_short, 'margin_column',  # column number to show right margin at
    c_short, 'lheight_dpi',  # actual lineheight, dpi controlled
    c_char * 4, 'pad',

    c_void_p, 'drawcache',  # cache for faster drawing

    c_float * 2, 'scroll_accum',  # runtime, for scroll increments smaller than a line
)


class bContext(Structure):
    """source/blender/blenkernel/intern/context.c:61"""
    class bContext_wm(Structure):
        _fields_ = fields(
            c_void_p, 'manager',  # struct wmWindowManager
            POINTER(wmWindow), 'window',
            c_void_p, 'screen',  # struct bScreen
            POINTER(ScrArea), 'area',
            POINTER(ARegion), 'region',
            POINTER(ARegion), 'menu',
            c_void_p, 'store',  # struct bContextStore
            c_char_p, 'operator_poll_msg',  # reason for poll failing
        )

    class bContext_data(Structure):
        _fields_ = fields(
            c_void_p, 'main',  # struct Main
            c_void_p, 'scene',  # struct Scene

            c_int, 'recursion',
            c_int, 'py_init',  # true if python is initialized
            c_void_p, 'py_context',
        )

    _fields_ = fields(
        c_int, 'thread',

        # windowmanager context
        bContext_wm, 'wm',

        # data context
        bContext_data, 'data',
    )


class ID(Structure):
    """DNA_ID.h"""

ID._fields_ = fields(
    c_void_p, 'next', 'prev',
    POINTER(ID), 'newid',
    c_void_p, 'lib',  # <struct Library>
    c_char * 66, 'name',  # MAX_ID_NAME
    c_short, 'flag',
    c_int, 'us',
    c_int, 'icon_id', 'pad2',
    c_void_p, 'properties',  # <IDProperty>
)


class Text(Structure):
    """makesdna/DNA_text_types.h: 50"""
    _fields_ = fields(
        ID, 'id',

        c_char_p, 'name',

        c_int, 'flags', 'nlines',

        ListBase, 'lines',
        c_void_p, 'curl', 'sell',  # <TextLine>
        c_int, 'curc', 'selc',

        c_char_p, 'undo_buf',
        c_int, 'undo_pos', 'undo_len',

        c_void_p, 'compiled',
        c_double, 'mtime',
    )


# 未使用
'''
class Material(Structure):
    """DNA_material_types.h"""

Material._fields_ = fields(
    ID, 'id',
)
'''


###############################################################################
def context_py_dict_get(context):
    """CTX_py_dict_get
    :type context: bpy.types.Context
    """
    addr = c_void_p(context.as_pointer())
    C = cast(addr, POINTER(bContext)).contents
    if C.data.py_context is None:  # NULL
        return None
    else:
        return cast(C.data.py_context, py_object).value


def context_py_dict_set(context, py_dict):
    """CTX_py_dict_set
    :type context: bpy.types.Context
    :type py_dict: dict | None
    :rtype: dict
    """
    py_dict_bak = context_py_dict_get(context)

    addr = c_void_p(context.as_pointer())
    C = cast(addr, POINTER(bContext)).contents
    if isinstance(py_dict, dict):
        C.data.py_context = c_void_p(id(py_dict))
    else:
        C.data.py_context = None  # NULL
    return py_dict_bak


def test_platform():
    return (platform.platform().split('-')[0].lower()
            not in {'darwin', 'windows'})


def context_py_dict_get_linux(context):
    """ctypes.CDLLを用いる方法"""
    class bContext(Structure):
        pass

    if not test_platform():
        raise OSError('Linux only')
    blend_cdll = CDLL('')
    CTX_py_dict_get = blend_cdll.CTX_py_dict_get
    CTX_py_dict_get.restype = c_void_p
    C = cast(c_void_p(context.as_pointer()), POINTER(bContext))
    ptr = CTX_py_dict_get(C)
    if ptr is not None:  # int
        return cast(c_void_p(ptr), py_object).value
    else:
        return None


def context_py_dict_set_linux(context, py_dict):
    """ctypes.CDLLを用いる方法"""
    class bContext(Structure):
        pass

    if not test_platform():
        raise OSError('Linux only')
    blend_cdll = CDLL('')
    CTX_py_dict_set = blend_cdll.CTX_py_dict_set
    C = cast(c_void_p(context.as_pointer()), POINTER(bContext))
    if py_dict is not None:
        CTX_py_dict_set(C, py_object(py_dict))
    else:
        CTX_py_dict_set(C, py_object())


###############################################################################
# ポインタアドレスからpythonオブジェクトを生成する。
# bpy.context.active_object.as_pointer() -> int の逆の動作。

# class BlenderRNA(Structure):
#     _fields_ = [
#         ('structs', ListBase),
#     ]

# 未使用
'''
class _PointerRNA_id(Structure):
    _fields_ = [
        ('data', c_void_p),
    ]


class PointerRNA(Structure):
    _fields_ = [
        ('id', _PointerRNA_id),
        ('type', c_void_p),  # StructRNA
        ('data', c_void_p),
    ]


def create_python_object(id_addr, type_name, addr):
    """アドレスからpythonオブジェクトを作成する。
    area = create_python_object(C.screen.as_pointer(), 'Area',
                                C.area.as_pointer())
    obj = create_python_object(C.active_object.as_pointer(), 'Object',
                               C.active_object.as_pointer())

    :param id_addr: id_dataのアドレス。自身がIDオブジェクトならそれを指定、
        そうでないなら所属するIDオブジェクトのアドレスを指定する。
        AreaならScreen、ObjectならObjectのアドレスとなる。無い場合はNone。
        正しく指定しないと予期しない動作を起こすので注意。
    :type id_addr: int | None
    :param type_name: 型名。'Area', 'Object' 等。
        SpaceView3D等のSpaceのサブクラスは'Space'でよい。
    :type type_name: str
    :param addr: オブジェクトのアドレス。
    :type addr: int
    :rtype object
    """
    if (not isinstance(id_addr, (int, type(None))) or
            not isinstance(type_name, str) or
            not isinstance(addr, int)):
        raise TypeError('引数の型が間違ってる。(int, str, int)')

    blend_cdll = CDLL('')
    RNA_pointer_create = blend_cdll.RNA_pointer_create
    RNA_pointer_create.restype = None
    pyrna_struct_CreatePyObject = blend_cdll.pyrna_struct_CreatePyObject
    pyrna_struct_CreatePyObject.restype = py_object
    try:
        RNA_type = getattr(blend_cdll, 'RNA_' + type_name)
    except AttributeError:
        raise ValueError("型名が間違ってる。'{}'".format(type_name))

    ptr = PointerRNA()
    RNA_pointer_create(c_void_p(id_addr), RNA_type, c_void_p(addr), byref(ptr))
    return pyrna_struct_CreatePyObject(byref(ptr))
'''
