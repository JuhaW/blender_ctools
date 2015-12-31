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
MeshのEditModeに於いて、右クリックで選択される頂点/辺/面を強調表示する。
"""

bl_info = {
    'name': 'Edit Mesh Draw Nearest',
    'author': 'chromoly',
    'version': (0, 3),
    'blender': (2, 76, 0),
    'location': 'View3D > Properties Panel > Mesh Display',
    'wiki_url': 'https://github.com/chromoly/blender-EditMeshDrawNearest',
    'category': '3D View',
}


import math
import platform
import ctypes
from ctypes import Structure, POINTER, addressof, byref, cast, c_bool, c_char,\
    c_int, c_int8, c_float, c_short, c_void_p, py_object, sizeof
import re
import numpy as np

import bpy
import bmesh
import mathutils
from mathutils import Matrix, Vector
import bgl
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d as project

from .utils import AddonPreferences, SpaceProperty


def test_platform():
    return (platform.platform().split('-')[0].lower()
            not in {'darwin', 'windows'})


class VIEW3D_PG_DrawNearest(bpy.types.PropertyGroup):
    def update(self, context):
        arg = 'ENABLE' if self.enable else 'DISABLE'
        bpy.ops.view3d.draw_nearest_element('INVOKE_DEFAULT', type=arg)

    enable = bpy.props.BoolProperty(
        name='Enable', update=update)


space_prop = SpaceProperty(
    [bpy.types.SpaceView3D, 'drawnearest',
     VIEW3D_PG_DrawNearest])


###############################################################################
# Addon Preferences
###############################################################################
class DrawNearestPreferences(
        AddonPreferences,
        bpy.types.PropertyGroup if '.' in __name__ else
        bpy.types.AddonPreferences):
    bl_idname = __name__

    select_color = bpy.props.FloatVectorProperty(
        name='Select Color',
        default=(0.0, 0.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        subtype='COLOR_GAMMA',
        size=4
    )
    vertex_size = bpy.props.IntProperty(
        name='Vertex Size',
        default=8,
        min=0,
        max=30,
    )
    vertex_line_width = bpy.props.IntProperty(
        name='Vertex Line Width',
        default=2,
        min=1,
        max=10,
    )
    edge_line_width = bpy.props.IntProperty(
        name='Edge Line Width',
        default=2,
        min=0,
        max=10,
    )
    edge_line_stipple = bpy.props.IntProperty(
        name='Line Stipple',
        default=5,
        min=0,
        max=20,
    )
    face_center_size = bpy.props.IntProperty(
        name='Face Center Size',
        default=12,
        min=0,
        max=30,
    )
    face_center_line_width = bpy.props.IntProperty(
        name='Face Center Line Width',
        default=1,
        min=0,
        max=10,
    )

    use_loop_select = bpy.props.BoolProperty(
        name='Loop Select',
        default=True,
    )
    loop_select_color = bpy.props.FloatVectorProperty(
        name='Loop Select Color',
        default=(0.0, 0.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        subtype='COLOR_GAMMA',
        size=4
    )
    loop_select_line_width = bpy.props.IntProperty(
        name='Loop Select Line Width',
        default=3,
        min=0,
        max=10,
    )
    loop_select_line_stipple = bpy.props.IntProperty(
        name='Loop Select Line Stipple',
        default=4,
        min=0,
        max=20,
    )
    loop_select_face_stipple = bpy.props.IntProperty(
        name='Loop Select Face Stipple',
        description='available: 1, 2, 4, 8',
        default=2,
        min=1,
        max=8,
    )

    redraw_all = bpy.props.BoolProperty(
        name='Redraw All 3D View',
        default=True,
    )
    use_ctypes = bpy.props.BoolProperty(
        name='Use ctypes',
        description='Use ctypes python module (faster)',
        default=test_platform(),
    )

    def draw(self, context):
        split = self.layout.split()
        col = split.column()
        col.prop(self, 'select_color')
        col.prop(self, 'vertex_size')
        col.prop(self, 'vertex_line_width')
        col.prop(self, 'edge_line_width')
        col.prop(self, 'edge_line_stipple')
        col.prop(self, 'face_center_size')
        col.prop(self, 'face_center_line_width')
        col = split.column()
        col.prop(self, 'use_loop_select')
        sub = col.column()
        sub.active = self.use_loop_select
        sub.prop(self, 'loop_select_color')
        sub.prop(self, 'loop_select_line_width')
        sub.prop(self, 'loop_select_line_stipple')
        sub.prop(self, 'loop_select_face_stipple')
        col = split.column()
        col.prop(self, 'redraw_all')
        col.prop(self, 'use_ctypes')


###############################################################################
# BGL
###############################################################################
class Buffer:
    def __new__(self, type, dimensions=0, template=None):
        """
        :param type: GL_BYTE('bool','byte'), GL_SHORT('short'),
            GL_INT('int'), GL_FLOAT('float') or GL_DOUBLE('double')
        :type type: int | str
        :param dimensions: array size.
            e.g. 3:      [0, 0, 0]
                 [4, 2]: [(0, 0), (0, 0), (0, 0), (0, 0)]
        :type dimensions: int | list | tuple
        :param template: Used to initialize the Buffer
            e.g. list: [1, 2, 3], int: bgl.GL_BLEND
        :type template: None | sequence | int
        :return:
        :rtype:
        """

        if isinstance(type, str):
            type = type.lower()
            if type in ('bool', 'byte'):
                type = bgl.GL_BYTE
            elif type == 'short':
                type = bgl.GL_SHORT
            elif type == 'int':
                type = bgl.GL_INT
            elif type == 'float':
                type = bgl.GL_FLOAT
            elif type == 'double':
                type = bgl.GL_DOUBLE
            else:
                type = None

        return_int = isinstance(dimensions, int) and dimensions < 1
        if return_int:
            dim = 1
        else:
            dim = dimensions
        if template is None:
            buf = bgl.Buffer(type, dim)
        elif isinstance(template, int):
            if type == bgl.GL_BYTE:
                glGet = bgl.glGetBooleanv
            elif type == bgl.GL_SHORT:
                glGet = bgl.glGetIntegerv
            elif type == bgl.GL_INT:
                glGet = bgl.glGetIntegerv
            elif type == bgl.GL_FLOAT:
                glGet = bgl.glGetFloatv
            elif type == bgl.GL_DOUBLE:
                glGet = bgl.glGetDoublev
            else:
                msg = "invalid first argument type, should be one of " \
                      "GL_BYTE('bool','byte'), GL_SHORT('short'), " \
                      "GL_INT('int'), GL_FLOAT('float') or GL_DOUBLE('double')"
                raise AttributeError(msg)
            buf = bgl.Buffer(type, dim)
            glGet(template, buf)
        else:
            buf = bgl.Buffer(type, dim, template)

        if return_int:
            return buf[0]
        else:
            return buf


def glSwitch(attr, value):
    if value:
        bgl.glEnable(attr)
    else:
        bgl.glDisable(attr)


class GLSettings:
    def __init__(self, context, view_matrix=None, perspective_matrix=None):
        rv3d = context.region_data
        if view_matrix is None:
            if rv3d:
                view_matrix = rv3d.view_matrix
            else:
                view_matrix = Matrix.Identity(4)
        if perspective_matrix is None:
            if rv3d:
                perspective_matrix = rv3d.perspective_matrix
            else:
                perspective_matrix = Matrix.Identity(4)
        window_matrix = perspective_matrix * view_matrix.inverted()

        # type: <mathutils.Matrix>
        self.view_matrix = view_matrix
        self.window_matrix = window_matrix
        self.perspective_matrix = perspective_matrix

        # type: <bgl.Buffer>
        self.modelview_matrix = Buffer(
            'double', (4, 4), bgl.GL_MODELVIEW_MATRIX)
        self.projection_matrix = Buffer(
            'double', (4, 4), bgl.GL_PROJECTION_MATRIX)

        self._modelview_stack = []
        self._projection_stack = []
        self._modelview_bak_2d = None
        self._projection_bak_2d = None
        self._modelview_bak_3d = None
        self._projection_bak_3d = None

        region = context.region
        self.region_size = region.width, region.height

        # staticmethod
        self.Buffer = Buffer
        self.glSwitch = glSwitch

    @staticmethod
    def mul_4x4_matrixd(m1, m2):
        """double型で大きさが16のBuffer同士の積"""
        matrix_mode = Buffer('int', 0, bgl.GL_MATRIX_MODE)
        bgl.glMatrixMode(bgl.GL_MODELVIEW)  # GL_MAX_MODELVIEW_STACK_DEPTH: 32
        bgl.glPushMatrix()
        bgl.glLoadMatrixd(m1)
        bgl.glMultMatrixd(m2)
        mat = Buffer('double', (4, 4), bgl.GL_MODELVIEW_MATRIX)
        bgl.glPopMatrix()
        bgl.glMatrixMode(matrix_mode)
        return mat

    @classmethod
    def get_matrix(cls, matrix_type, buffer=False):
        """GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX を元にしたMatrixを返す。
        self.modelview_matrix等のインスタンス属性は使用しない。
        Spaceのコールバック関数の中でこのメソッドを呼んだ場合、
        PRE_VIEW / POST_VIEW と POST_PIXEL で違いがあるので十分注意すること。
        :param buffer: TrueだとBufferオブジェクトを返す。
        :rtype: Matrix | Buffer
        """
        if isinstance(matrix_type, int):
            if matrix_type == bgl.GL_MODELVIEW_MATRIX:
                matrix_type = 'modelview'
            elif matrix_type == bgl.GL_PROJECTION_MATRIX:
                matrix_type = 'projection'
            else:
                return None
        elif isinstance(matrix_type, str):
            matrix_type = matrix_type.lower()
        else:
            return None

        modelview = Buffer('double', (4, 4), bgl.GL_MODELVIEW_MATRIX)
        vmat = Matrix(modelview).transposed()
        if matrix_type.startswith(('model', 'view')):
            if buffer:
                return modelview
            else:
                return vmat
        else:
            projection = Buffer('double', (4, 4), bgl.GL_PROJECTION_MATRIX)
            wmat = Matrix(projection).transposed()
            if matrix_type.startswith(('proj', 'win')):
                if buffer:
                    return projection
                else:
                    return wmat
            elif matrix_type.startswith('pers'):
                if buffer:
                    return cls.mul_4x4_matrixd(projection, modelview)
                else:
                    return wmat * vmat

    @staticmethod
    def font_size(id=0, size=11, dpi=None):
        if dpi is None:
            dpi = bpy.context.user_preferences.system.dpi
        blf.size(id, size, dpi)

    def _load_matrix(self, modelview=None, projection=None):
        matrix_mode = Buffer('int', 0, bgl.GL_MATRIX_MODE)
        if modelview:
            bgl.glMatrixMode(bgl.GL_MODELVIEW)
            bgl.glLoadIdentity()  # glLoadMatrix()にも必須
            if isinstance(modelview, bgl.Buffer):
                bgl.glLoadMatrixd(modelview)
        if projection:
            bgl.glMatrixMode(bgl.GL_PROJECTION)
            bgl.glLoadIdentity()  # glLoadMatrix()にも必須
            if isinstance(projection, bgl.Buffer):
                bgl.glLoadMatrixd(projection)
        bgl.glMatrixMode(matrix_mode)

    def push(self, mask=bgl.GL_ALL_ATTRIB_BITS):
        """glPushAttrib()で状態変数を保存しておく。
        glPushMatrix(), glPopMatrix() は GL_MAX_MODELVIEW_STACK_DEPTH が 32
        なのに対し、GL_MAX_PROJECTION_STACK_DEPTH が 4 しか無い為、使用しない。
        """
        bgl.glPushAttrib(mask)
        self._modelview_stack.append(
            Buffer('double', (4, 4), bgl.GL_MODELVIEW_MATRIX))
        self._projection_stack.append(
            Buffer('double', (4, 4), bgl.GL_PROJECTION_MATRIX))

    def pop(self):
        """push()時の状態に戻す。"""
        self._load_matrix(self._modelview_stack.pop(),
                          self._projection_stack.pop())
        bgl.glPopAttrib()

    def prepare_3d(self):
        """POST_PIXELのcallbackでworld座標系を用いて描画する場合に使用する。"""
        self._modelview_bak_3d = Buffer('double', (4, 4),
                                        bgl.GL_MODELVIEW_MATRIX)
        self._projection_bak_3d = Buffer('double', (4, 4),
                                         bgl.GL_PROJECTION_MATRIX)
        view_mat = Buffer('double', (4, 4), self.view_matrix.transposed())
        win_mat = Buffer('double', (4, 4), self.window_matrix.transposed())
        self._load_matrix(view_mat, win_mat)

    def restore_3d(self):
        """prepare_3d()での変更を戻す"""
        self._load_matrix(self._modelview_bak_3d, self._projection_bak_3d)

    def prepare_2d(self):
        """PRE_VIEW,POST_VIEWのcallbackでscreen座標系を用いて描画する場合に
        使用する。
        参照: ED_region_do_draw() -> ED_region_pixelspace() ->
        wmOrtho2_region_pixelspace()

        """
        self._modelview_bak_2d = Buffer('double', (4, 4),
                                        bgl.GL_MODELVIEW_MATRIX)
        self._projection_bak_2d = Buffer('double', (4, 4),
                                         bgl.GL_PROJECTION_MATRIX)
        matrix_mode = Buffer('int', 0, bgl.GL_MATRIX_MODE)

        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glLoadIdentity()  # 必須
        w, h = self.region_size
        # wmOrtho2_region_pixelspace(), wmOrtho2() 参照
        ofs = -0.01
        bgl.glOrtho(ofs, w + ofs, ofs, h + ofs, -100, 100)

        bgl.glMatrixMode(bgl.GL_MODELVIEW)
        bgl.glLoadIdentity()

        bgl.glMatrixMode(matrix_mode)

    def restore_2d(self):
        """prepare_2d()での変更を戻す"""
        self._load_matrix(self._modelview_bak_2d, self._projection_bak_2d)


def draw_circle(x, y, radius, subdivide, poly=False):
    r = 0.0
    dr = math.pi * 2 / subdivide
    if poly:
        subdivide += 1
        bgl.glBegin(bgl.GL_TRIANGLE_FAN)
        bgl.glVertex2f(x, y)
    else:
        bgl.glBegin(bgl.GL_LINE_LOOP)
    for _ in range(subdivide):
        bgl.glVertex2f(x + radius * math.cos(r), y + radius * math.sin(r))
        r += dr
    bgl.glEnd()


def draw_box(xmin, ymin, w, h, poly=False):
    bgl.glBegin(bgl.GL_QUADS if poly else bgl.GL_LINE_LOOP)
    bgl.glVertex2f(xmin, ymin)
    bgl.glVertex2f(xmin + w, ymin)
    bgl.glVertex2f(xmin + w, ymin + h)
    bgl.glVertex2f(xmin, ymin + h)
    bgl.glEnd()


###############################################################################
# ctypes
###############################################################################
class Context(Structure):
    pass


class BMEditMesh(Structure):
    _fields_ = [
        ('bm', c_void_p),
    ]


class ViewContext(Structure):
    _fields_ = [
        ('scene', c_void_p),
        ('obact', c_void_p),
        ('obedit', c_void_p),
        ('ar', c_void_p),
        ('v3d', c_void_p),
        ('rv3d', c_void_p),
        ('em', POINTER(BMEditMesh)),
        ('mval', c_int * 2),
    ]


class c_int8_(c_int8):
    """サブクラス化することでPython型へ透過的に変換しなくなる"""
    pass


class BMHeader(Structure):
    _fields_ = [
        ('data', c_void_p),
        ('index', c_int),
        ('htype', c_char),
        # ('hflag', c_char),
        ('hflag', c_int8_),  # ビット演算の為int型にする
        ('api_flag', c_char)
    ]


class BMElem(Structure):
    _fields_ = [
        ('head', BMHeader),
    ]


class BMVert(Structure):
    pass


class BMEdge(Structure):
    pass


class BMFace(Structure):
    pass


class BMLoop(Structure):
    pass


class BMDiskLink(Structure):
    _fields_ = [
        ('next', POINTER(BMEdge)),
        ('prev', POINTER(BMEdge)),
    ]


BMVert._fields_ = [
    ('head', BMHeader),
    ('oflags', c_void_p),  # BMFlagLayer
    ('co', c_float * 3),
    ('no', c_float * 3),
    ('e', POINTER(BMEdge))
]

BMEdge._fields_ = [
    ('head', BMHeader),
    ('oflags', c_void_p),  # BMFlagLayer
    ('v1', POINTER(BMVert)),
    ('v2', POINTER(BMVert)),
    ('l', POINTER(BMLoop)),
    ('v1_disk_link', BMDiskLink),
    ('v2_disk_link', BMDiskLink),
]

BMLoop._fields_ = [
    ('head', BMHeader),

    ('v', POINTER(BMVert)),
    ('e', POINTER(BMEdge)),
    ('f', POINTER(BMFace)),

    ('radial_next', POINTER(BMLoop)),
    ('radial_prev', POINTER(BMLoop)),

    ('next', POINTER(BMLoop)),
    ('prev', POINTER(BMLoop)),
]

class BMFace(Structure):
    _fields_ = [
        ('head', BMHeader),
        ('oflags', c_void_p),  # BMFlagLayer
        ('l_first', c_void_p),  # BMLoop
        ('len', c_int),
        ('no', c_float * 3),
        ('mat_nr', c_short)
    ]


class BMesh(Structure):
    _fields_ = [
        ('totvert', c_int),
        ('totedge', c_int),
        ('totloop', c_int),
        ('totface', c_int),

        ('totvertsel', c_int),
        ('totedgesel', c_int),
        ('totfacesel', c_int),

        ('elem_index_dirty', c_char),

        ('elem_table_dirty', c_char),

        ('vpool', c_void_p),  # BLI_mempool
        ('epool', c_void_p),  # BLI_mempool
        ('lpool', c_void_p),  # BLI_mempool
        ('fpool', c_void_p),  # BLI_mempool

        ('vtable', POINTER(POINTER(BMVert))),
        ('etable', POINTER(POINTER(BMEdge))),
        ('ftable', POINTER(POINTER(BMFace))),

        ('vtable_tot', c_int),
        ('etable_tot', c_int),
        ('ftable_tot', c_int),
    ]


class ListBase(Structure):
    """source/blender/makesdna/DNA_listBase.h: 59"""
    _fields_ = [
        ('first', c_void_p),
        ('last', c_void_p)
    ]


class BMWalker(Structure):
    _fields_ = [
        ('begin_htype', c_char),      # only for validating input
        ('begin', c_void_p),  # void  (*begin) (struct BMWalker *walker, void *start)
        ('step', c_void_p),  # void *(*step)  (struct BMWalker *walker)
        ('yield ', c_void_p),  # void *(*yield) (struct BMWalker *walker)
        ('structsize', c_int),
        ('order', c_int),  # enum BMWOrder
        ('valid_mask', c_int),

        # runtime
        ('layer', c_int),

        ('bm', POINTER(BMesh)),
        ('worklist', c_void_p),  # BLI_mempool
        ('states', ListBase),

        # these masks are to be tested against elements BMO_elem_flag_test(),
        # should never be accessed directly only through BMW_init() and bmw_mask_check_*() functions
        ('mask_vert', c_short),
        ('mask_edge', c_short),
        ('mask_face', c_short),

        ('flag', c_int),  # enum BMWFlag

        ('visit_set', c_void_p),  # struct GSet *visit_set
        ('visit_set_alt', c_void_p),  # struct GSet *visit_set_alt
        ('depth', c_int),

        ('dummy', c_int * 4)  # enumのサイズが不明な為
    ]



BMW_VERT_SHELL = 0
BMW_LOOP_SHELL = 1
BMW_LOOP_SHELL_WIRE = 2
BMW_FACE_SHELL = 3
BMW_EDGELOOP = 4
BMW_FACELOOP = 5
BMW_EDGERING = 6
BMW_EDGEBOUNDARY = 7
# BMW_RING
BMW_LOOPDATA_ISLAND = 8
BMW_ISLANDBOUND = 9
BMW_ISLAND = 10
BMW_CONNECTED_VERTEX = 11
# end of array index enum vals

# do not intitialze function pointers and struct size in BMW_init
BMW_CUSTOM = 12
BMW_MAXWALKERS = 13


def context_py_dict_get(context):
    if not test_platform():
        raise OSError('Linux only')
    blend_cdll = ctypes.CDLL('')
    CTX_py_dict_get = blend_cdll.CTX_py_dict_get
    CTX_py_dict_get.restype = c_void_p
    C = cast(c_void_p(context.as_pointer()), POINTER(Context))
    ptr = CTX_py_dict_get(C)
    if ptr is not None:  # int
        return cast(c_void_p(ptr), py_object).value
    else:
        return None


def context_py_dict_set(context, py_dict):
    if not test_platform():
        raise OSError('Linux only')
    blend_cdll = ctypes.CDLL('')
    CTX_py_dict_set = blend_cdll.CTX_py_dict_set
    C = cast(c_void_p(context.as_pointer()), POINTER(Context))
    if py_dict is not None:
        CTX_py_dict_set(C, py_object(py_dict))
    else:
        CTX_py_dict_set(C, py_object())


mval_prev = [-1, -1]


def unified_findnearest(context, bm, mval):
    """Mesh編集モードに於いて、次の右クリックで選択される要素を返す。
    Linux限定。
    NOTE: bmeshは外部から持ってこないと関数を抜ける際に開放されて
          返り値のBMVert等がdead扱いになってしまう。
    :type context: bpy.types.Context
    :param mval: mouse region coordinates. [x, y]
    :type mval: list[int] | tuple[int]
    :rtype: (bool,
             (bmesh.types.BMVert, bmesh.types.BMEdge, bmesh.types.BMFace))
    """

    if not test_platform():
        raise OSError('Linux only')

    if context.mode != 'EDIT_MESH':
        return None, (None, None, None)

    # Load functions ------------------------------------------------
    blend_cdll = ctypes.CDLL('')

    view3d_operator_needs_opengl = blend_cdll.view3d_operator_needs_opengl

    em_setup_viewcontext = blend_cdll.em_setup_viewcontext
    ED_view3d_backbuf_validate = blend_cdll.ED_view3d_backbuf_validate
    ED_view3d_select_dist_px = blend_cdll.ED_view3d_select_dist_px
    ED_view3d_select_dist_px.restype = c_float

    EDBM_face_find_nearest_ex = blend_cdll.EDBM_face_find_nearest_ex
    EDBM_face_find_nearest_ex.restype = POINTER(BMFace)
    EDBM_edge_find_nearest_ex = blend_cdll.EDBM_edge_find_nearest_ex
    EDBM_edge_find_nearest_ex.restype = POINTER(BMEdge)
    EDBM_vert_find_nearest_ex = blend_cdll.EDBM_vert_find_nearest_ex
    EDBM_vert_find_nearest_ex.restype = POINTER(BMVert)

    BPy_BMVert_CreatePyObject = blend_cdll.BPy_BMVert_CreatePyObject
    BPy_BMVert_CreatePyObject.restype = py_object
    BPy_BMEdge_CreatePyObject = blend_cdll.BPy_BMEdge_CreatePyObject
    BPy_BMEdge_CreatePyObject.restype = py_object
    BPy_BMFace_CreatePyObject = blend_cdll.BPy_BMFace_CreatePyObject
    BPy_BMFace_CreatePyObject.restype = py_object

    # view3d_select_exec() ------------------------------------------
    C = cast(c_void_p(context.as_pointer()), POINTER(Context))
    view3d_operator_needs_opengl(C)

    # EDBM_select_pick() --------------------------------------------

    vc_obj = ViewContext()
    vc = POINTER(ViewContext)(vc_obj)  # same as pointer(vc_obj)

    # setup view context for argument to callbacks
    em_setup_viewcontext(C, vc)
    vc_obj.mval[0] = mval[0]
    vc_obj.mval[1] = mval[1]

    # unified_findnearest() -----------------------------------------

    # only cycle while the mouse remains still
    use_cycle = c_bool(mval_prev[0] == vc_obj.mval[0] and
                       mval_prev[1] == vc_obj.mval[1])
    dist_init = ED_view3d_select_dist_px()  # float
    # since edges select lines, we give dots advantage of ~20 pix
    dist_margin = c_float(dist_init / 2)
    dist = c_float(dist_init)
    efa_zbuf = POINTER(BMFace)()
    eed_zbuf = POINTER(BMEdge)()

    eve = POINTER(BMVert)()
    eed = POINTER(BMEdge)()
    efa = POINTER(BMFace)()

    # no afterqueue (yet), so we check it now,
    # otherwise the em_xxxofs indices are bad
    ED_view3d_backbuf_validate(vc)

    if dist.value > 0.0 and bm.select_mode & {'FACE'}:
        dist_center = c_float(0.0)
        if bm.select_mode & {'EDGE', 'VERT'}:
            dist_center_p = POINTER(c_float)(dist_center)
        else:
            dist_center_p = POINTER(c_float)()  # 引数無しでNULLポインタになる
        efa = EDBM_face_find_nearest_ex(vc, byref(dist), dist_center_p,
                                        c_bool(1), use_cycle, byref(efa_zbuf))
        if efa and dist_center_p:
            dist.value = min(dist_margin.value, dist_center.value)

    if dist.value > 0.0 and bm.select_mode & {'EDGE'}:
        dist_center = c_float(0.0)
        if bm.select_mode & {'VERT'}:
            dist_center_p = POINTER(c_float)(dist_center)
        else:
            dist_center_p = POINTER(c_float)()
        eed = EDBM_edge_find_nearest_ex(vc, byref(dist), dist_center_p,
                                        c_bool(1), use_cycle, byref(eed_zbuf))
        if eed and dist_center_p:
            dist.value = min(dist_margin.value, dist_center.value)

    if dist.value > 0.0 and bm.select_mode & {'VERT'}:
        eve = EDBM_vert_find_nearest_ex(vc, byref(dist), c_bool(1), use_cycle)

    if eve:
        efa = POINTER(BMFace)()
        eed = POINTER(BMEdge)()
    elif eed:
        efa = POINTER(BMFace)()

    if not (eve or eed or efa):
        if eed_zbuf:
            eed = eed_zbuf
        elif efa_zbuf:
            efa = efa_zbuf

    mval_prev[0] = vc_obj.mval[0]
    mval_prev[1] = vc_obj.mval[1]

    bm_p = c_void_p(vc_obj.em.contents.bm)
    v = BPy_BMVert_CreatePyObject(bm_p, eve) if eve else None
    e = BPy_BMEdge_CreatePyObject(bm_p, eed) if eed else None
    f = BPy_BMFace_CreatePyObject(bm_p, efa) if efa else None

    r = bool(eve or eed or efa), (v, e, f)

    return r


def walker_select_count(em, walkercode, start, select, select_mix):
    tot = [0, 0]

    blend_cdll = ctypes.CDLL('')
    BMW_init = blend_cdll.BMW_init
    BMW_begin = blend_cdll.BMW_begin
    BMW_begin.restype = POINTER(BMElem)
    BMW_step = blend_cdll.BMW_step
    BMW_step.restype = POINTER(BMElem)
    BMW_end = blend_cdll.BMW_end
    BM_ELEM_SELECT = 1 << 0

    def BM_elem_flag_test_bool(ele, flag):
        return ele.contents.head.hflag.value & flag != 0

    BMW_MASK_NOP = 0
    BMW_FLAG_TEST_HIDDEN = 1 << 0
    BMW_NIL_LAY = 0

    bm = c_void_p(em.contents.bm)
    walker = BMWalker()
    BMW_init(byref(walker), bm, walkercode,
             BMW_MASK_NOP, BMW_MASK_NOP, BMW_MASK_NOP,
             BMW_FLAG_TEST_HIDDEN,
             BMW_NIL_LAY)
    ele = BMW_begin(byref(walker), start)
    while ele:
        i = BM_elem_flag_test_bool(ele, BM_ELEM_SELECT) != select
        tot[i] += 1
        ele = BMW_step(byref(walker))
    BMW_end(byref(walker))

    return tot


def walker_select(em, walkercode, start, select):
    """mesh/editmesh_select.c: 1402
    選択ではなく要素を返すように変更
    """
    r_elems = []

    blend_cdll = ctypes.CDLL('')
    BMW_init = blend_cdll.BMW_init
    BMW_begin = blend_cdll.BMW_begin
    BMW_begin.restype = POINTER(BMElem)
    BMW_step = blend_cdll.BMW_step
    BMW_step.restype = POINTER(BMElem)
    BMW_end = blend_cdll.BMW_end

    BMW_MASK_NOP = 0
    BMW_FLAG_TEST_HIDDEN = 1 << 0
    BMW_NIL_LAY = 0

    bm = c_void_p(em.contents.bm)
    walker = BMWalker()
    BMW_init(byref(walker), bm, walkercode,
             BMW_MASK_NOP, BMW_MASK_NOP, BMW_MASK_NOP,
             BMW_FLAG_TEST_HIDDEN,
             BMW_NIL_LAY)
    ele = BMW_begin(byref(walker), start)
    while ele:
        r_elems.append(ele)
        ele = BMW_step(byref(walker))
    BMW_end(byref(walker))

    return r_elems


def mouse_mesh_loop_face(em, eed, select, select_clear):
    return walker_select(em, BMW_FACELOOP, eed, select)


def mouse_mesh_loop_edge_ring(em, eed, select, select_clear):
    return walker_select(em, BMW_EDGERING, eed, select)


def mouse_mesh_loop_edge(em, eed, select, select_clear, select_cycle):
    def BM_edge_is_boundary(e):
        l = e.contents.l
        return (l and addressof(l.contents.radial_next.contents) ==
                addressof(l.contents))

    edge_boundary = False

    if select_cycle and BM_edge_is_boundary(eed):
        tot = walker_select_count(em, BMW_EDGELOOP, eed, select, False)
        if tot[int(select)] == 0:
            edge_boundary = True
            tot = walker_select_count(em, BMW_EDGEBOUNDARY, eed, select, False)
            if tot[int(select)] == 0:
                edge_boundary = False

    if edge_boundary:
        return walker_select(em, BMW_EDGEBOUNDARY, eed, select)
    else:
        return walker_select(em, BMW_EDGELOOP, eed, select)


def mouse_mesh_loop(context, bm, mval, extend, deselect, toggle, ring):
    """Mesh編集モードに於いて、次の右クリックで選択される要素を返す。
    Linux限定。
    NOTE: bmeshは外部から持ってこないと関数を抜ける際に開放されて
          返り値のBMVert等がdead扱いになってしまう。
    :type context: bpy.types.Context
    :param mval: mouse region coordinates. [x, y]
    :type mval: list[int] | tuple[int]
    :rtype: (bool,
             (bmesh.types.BMVert, bmesh.types.BMEdge, bmesh.types.BMFace))
    """

    if not test_platform():
        raise OSError('Linux only')

    if context.mode != 'EDIT_MESH':
        return None, None

    # Load functions ------------------------------------------------
    blend_cdll = ctypes.CDLL('')

    view3d_operator_needs_opengl = blend_cdll.view3d_operator_needs_opengl

    em_setup_viewcontext = blend_cdll.em_setup_viewcontext
    ED_view3d_backbuf_validate = blend_cdll.ED_view3d_backbuf_validate
    ED_view3d_select_dist_px = blend_cdll.ED_view3d_select_dist_px
    ED_view3d_select_dist_px.restype = c_float

    EDBM_edge_find_nearest_ex = blend_cdll.EDBM_edge_find_nearest_ex
    EDBM_edge_find_nearest_ex.restype = POINTER(BMEdge)

    BPy_BMEdge_CreatePyObject = blend_cdll.BPy_BMEdge_CreatePyObject
    BPy_BMEdge_CreatePyObject.restype = py_object
    BPy_BMElem_CreatePyObject = blend_cdll.BPy_BMElem_CreatePyObject
    BPy_BMElem_CreatePyObject.restype = py_object

    # edbm_select_loop_invoke() -------------------------------------
    C = cast(c_void_p(context.as_pointer()), POINTER(Context))
    view3d_operator_needs_opengl(C)

    # mouse_mesh_loop() ---------------------------------------------
    vc_obj = ViewContext()
    vc = POINTER(ViewContext)(vc_obj)  # same as pointer(vc_obj)
    dist = c_float(ED_view3d_select_dist_px() * 0.6666)
    em_setup_viewcontext(C, vc)
    vc_obj.mval[0] = mval[0]
    vc_obj.mval[1] = mval[1]

    ED_view3d_backbuf_validate(vc)

    eed = EDBM_edge_find_nearest_ex(vc, byref(dist), None, True, True, None)
    if not eed:
        return None, None

    bm_p = c_void_p(vc_obj.em.contents.bm)
    edge = BPy_BMEdge_CreatePyObject(bm_p, eed)

    select = True
    select_clear = False
    select_cycle = True
    if not extend and not deselect and not toggle:
        select_clear = True
    if extend:
        select = True
    elif deselect:
        select = False
    elif select_clear or not edge.select:
        select = True
    elif toggle:
        select = False
        select_cycle = False

    em = vc_obj.em
    if bm.select_mode & {'FACE'}:
        c_elems = mouse_mesh_loop_face(em, eed, select, select_clear)
    else:
        if ring:
            c_elems = mouse_mesh_loop_edge_ring(em, eed, select, select_clear)
        else:
            c_elems = mouse_mesh_loop_edge(em, eed, select, select_clear,
                                           select_cycle)

    elems = [BPy_BMElem_CreatePyObject(bm_p, elem) for elem in c_elems]
    return edge, elems


###############################################################################
# ctypes for windows
###############################################################################
def get_bmesh_address(bm):
    m = re.match('<BMesh\((.*)\)', repr(bm))
    return int(m.group(1), 16)


def get_selected_indices(bm, elem='VERT'):
    BM_ELEM_SELECT = 1 << 0
    bm_p = cast(c_void_p(get_bmesh_address(bm)), POINTER(BMesh))
    if elem == 'VERT':
        # bm_p.contents.vtable.contents.contentsでBMVert
        table = bm_p.contents.vtable
        tot = bm_p.contents.totvert
    elif elem == 'EDGE':
        table = bm_p.contents.etable
        tot = bm_p.contents.totedge
    else:
        table = bm_p.contents.ftable
        tot = bm_p.contents.totface
    if tot == 0:
        return set()
    a = addressof(table[0].contents)
    b = addressof(table[0].contents.head.hflag)
    ofs = int((b - a) / sizeof(c_int8))
    t = cast(table, POINTER(POINTER(c_int8)))
    return {i for i in range(tot) if t[i][ofs] & BM_ELEM_SELECT}


###############################################################################
# Main
###############################################################################
def redraw_areas(context, force=False):
    actob = context.active_object
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            v3d = area.spaces.active
            prop = space_prop.get(v3d)
            if force:
                area.tag_redraw()
            elif prop.enable and not v3d.viewport_shade == 'RENDERED':
                if any([a & b for a, b in zip(actob.layers, v3d.layers)]):
                    area.tag_redraw()


def bglPolygonOffset(viewdist, dist):
    """screen/glutil.c: 954
    :type viewdist: float
    :type dist: float
    """
    bgl.glMatrixMode(bgl.GL_PROJECTION)
    if dist != 0.0:
        bgl.glGetFloatv(bgl.GL_PROJECTION_MATRIX, bglPolygonOffset.winmat)
        if bglPolygonOffset.winmat[15] > 0.5:
            offs = 0.00001 * dist * viewdist
        else:
            offs = 0.0005 * dist
        bglPolygonOffset.winmat[14] -= offs
        bglPolygonOffset.offset += offs
    else:
        bglPolygonOffset.winmat[14] += bglPolygonOffset.offset
        bglPolygonOffset.offset = 0.0
    bgl.glLoadMatrixf(bglPolygonOffset.winmat)
    bgl.glMatrixMode(bgl.GL_MODELVIEW)

bglPolygonOffset.winmat = bgl.Buffer(bgl.GL_FLOAT, 16)
bglPolygonOffset.offset = 0.0


def ED_view3d_polygon_offset(rv3d, dist):
    """space_view3d/view3d_view.c: 803
    :type rv3d: bpy.types.RegionView3D
    :type dist: float
    """
    # if rv3d->rflag & RV3D_ZOFFSET_DISABLED:
    #     return
    viewdist = rv3d.view_distance
    if dist != 0.0:
        if rv3d.view_perspective == 'CAMERA':
            if not rv3d.is_perspective:
                winmat = rv3d.window_matrix
                viewdist = 1.0 / max(abs(winmat[0][0]), abs(winmat[1][1]))
    bglPolygonOffset(viewdist, dist)


def polygon_offset_pers_mat(rv3d, dist):
    viewdist = rv3d.view_distance
    if dist != 0.0:
        if rv3d.view_perspective == 'CAMERA':
            if not rv3d.is_perspective:
                winmat = rv3d.window_matrix
                viewdist = 1.0 / max(abs(winmat[0][0]), abs(winmat[1][1]))

    winmat = rv3d.window_matrix.copy()
    if dist != 0.0:
        if winmat.col[3][3] > 0.5:
            offs = 0.00001 * dist * viewdist
        else:
            offs = 0.0005 * dist
        winmat.col[3][2] -= offs

    return winmat * rv3d.view_matrix


def setlinestyle(nr):
    """screen/glutil.c:270
    :type nr: int
    """
    if nr == 0:
        bgl.glDisable(bgl.GL_LINE_STIPPLE)
    else:
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        if False:  # if U.pixelsize > 1.0f
            bgl.glLineStipple(nr, 0xCCCC)
        else:
            bgl.glLineStipple(nr, 0xAAAA)


def face_stipple_pattern(size):
    stipple_quattone_base = np.array(
            [[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]])

    def conv(arr):
        arr = [int(''.join([str(k) for k in arr[i][j*8:j*8+8]]), 2)
           for i in range(32) for j in range(4)]
        return bgl.Buffer(bgl.GL_BYTE, 128, arr)

    if size >= 8:
        buf = face_stipple_pattern.x8
        if not buf:
            buf = face_stipple_pattern.x8 = \
                conv(np.repeat(np.repeat(stipple_quattone_base, 8, axis=0), 8,
                               axis=1))
    elif size >= 4:
        buf = face_stipple_pattern.x4
        if not buf:
            buf = face_stipple_pattern.x4 = \
                conv(np.tile(np.repeat(np.repeat(
                        stipple_quattone_base, 4, axis=0), 4, axis=1), (2, 2)))
    elif size >= 2:
        buf = face_stipple_pattern.x2
        if not buf:
            buf = face_stipple_pattern.x2 = \
                conv(np.tile(np.repeat(np.repeat(
                        stipple_quattone_base, 2, axis=0), 2, axis=1), (4, 4)))
    else:
        # glutil.cのものと重ならないようにずらしたもの
        buf = face_stipple_pattern.x1
        if not buf:
            buf = face_stipple_pattern.x1 = \
                conv(np.tile(np.roll(stipple_quattone_base, 2, 1), (8, 8)))
    return buf

face_stipple_pattern.x1 = None
face_stipple_pattern.x2 = None
face_stipple_pattern.x4 = None
face_stipple_pattern.x8 = None


def setpolygontone(enable, size=1):
    """
    :type enable: bool
    :type size: int
    """
    if enable:
        bgl.glEnable(bgl.GL_POLYGON_STIPPLE)
        bgl.glPolygonStipple(face_stipple_pattern(size))
    else:
        bgl.glDisable(bgl.GL_POLYGON_STIPPLE)


def get_depth(x, y, fatten=0):
    size = fatten * 2 + 1
    buf = bgl.Buffer(bgl.GL_FLOAT, size ** 2)
    bgl.glReadPixels(x - fatten, y - fatten, size, size,
                     bgl.GL_DEPTH_COMPONENT, bgl.GL_FLOAT, buf)
    return list(buf)


PROJECT_MIN_NUMBER = 1E-5


def project(region, rv3d, vec):
    """World Coords (3D) -> Window Coords (3D).
    Window座標は左手系で、Zのクリッピング範囲は0~1。
    """
    v = rv3d.perspective_matrix * vec.to_4d()
    if abs(v[3]) > PROJECT_MIN_NUMBER:
        v /= v[3]
    x = (1 + v[0]) * region.width * 0.5
    y = (1 + v[1]) * region.height * 0.5
    z = (1 + v[2]) * 0.5
    return Vector((x, y, z))


def project_v3(sx, sy, persmat, vec) -> "3D Vector":
    """World Coords -> Window Coords. projectより少しだけ速い。"""
    v = persmat * vec.to_4d()
    if abs(v[3]) > PROJECT_MIN_NUMBER:
        v /= v[3]
    x = (1 + v[0]) * sx * 0.5
    y = (1 + v[1]) * sy * 0.5
    z = (1 + v[2]) * 0.5
    return Vector((x, y, z))


def unproject(region, rv3d, vec, depth_location:"world coords"=None):
    """Window Coords (2D / 3D) -> World Coords (3D).
    Window座標は左手系で、Zのクリッピング範囲は0~1。
    """
    x = vec[0] * 2.0 / region.width - 1.0
    y = vec[1] * 2.0 / region.height - 1.0
    if depth_location:
        z = (project(region, rv3d, depth_location)[2] - 0.5) * 2
    else:
        z = 0.0 if len(vec) == 2 else (vec[2] - 0.5) * 2
    v = rv3d.perspective_matrix.inverted() * Vector((x, y, z, 1.0))
    if abs(v[3]) > PROJECT_MIN_NUMBER:
        v /= v[3]
    return v.to_3d()


class VIEW3D_OT_draw_nearest_element(bpy.types.Operator):
    bl_label = 'Draw Nearest Element'
    bl_idname = 'view3d.draw_nearest_element'
    bl_options = {'REGISTER'}

    data = {}
    handle = None

    type = bpy.props.EnumProperty(
        items=(('ENABLE', 'Enable', ''),
               ('DISABLE', 'Disable', ''),
               ('TOGGLE', 'Toggle', ''),
               ('KILL', 'Kill', '')),
        default='TOGGLE',
    )

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    @classmethod
    def draw_func(cls, context):
        cls.remove_invalid_windows()

        if not cls.data:
            cls.remove_handler()
            return

        win = context.window
        if win not in cls.data:
            return

        prefs = DrawNearestPreferences.get_prefs()
        data = cls.data[win]
        event = data['event']
        area = context.area
        region = context.region
        rv3d = context.region_data
        v3d = context.space_data

        prop = space_prop.get(v3d)
        if not prop.enable or v3d.viewport_shade == 'RENDERED':
            return

        mco = (event.mouse_x, event.mouse_y)
        # target: [type, vert_coords, median]
        target = data['target']
        # targets: [vert_coords, edge_coords, face_coords, medians]
        targets = data['targets']

        draw = data['draw_flags'].get(rv3d, True)
        data['draw_flags'][rv3d] = False
        if draw:
            if context.mode != 'EDIT_MESH' or not (target or targets):
                draw = False
            elif data['mco'] != mco:  # 別のOperatorがRUNNING_MODAL
                draw = False
            elif not prefs.redraw_all:
                # if not (region.x <= mco[0] <= region.x + region.width and
                #         region.y <= mco[1] <= region.y + region.height):
                if not (area.x <= mco[0] <= area.x + area.width and
                        area.y <= mco[1] <= area.y + area.height):
                    draw = False
        if not draw:
            return

        # use_depth = get_depth(mco[0], mco[1], 1)
        # print(['{:.12f}'.format(f) for f in use_depth])

        ob = context.active_object
        if not ob:
            return
        mat = ob.matrix_world

        vert_size = prefs.vertex_size / 2
        vnum = 16

        glsettings = GLSettings(context)
        glsettings.push()
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glDepthMask(0)
        bgl.glLineWidth(1)

        if (v3d.viewport_shade in {'BOUNDBOX', 'WIREFRAME'} or
                v3d.viewport_shade == 'SOLID' and
                not v3d.use_occlude_geometry):
            use_depth = False
        else:
            use_depth = True
        # if target:
        #     if (region.x <= mco[0] <= region.x + region.width and
        #             region.y <= mco[1] <= region.y + region.height):
        #         use_depth = False

        if target:
            bgl.glDisable(bgl.GL_DEPTH_TEST)
            bgl.glColor4f(*prefs.select_color)

            target_type = target[0]
            coords = [mat * v for v in target[1]]
            median = mat * target[2]

            offs_pmat = polygon_offset_pers_mat(rv3d, 1)
            def depth_test(vec):
                v = project_v3(region.width, region.height,
                               offs_pmat, vec)
                x = int(v[0]) + region.x
                y = int(v[1]) + region.y
                depth3x3 = get_depth(x, y, 1)
                if not (0.0 < v[2] < 1.0):
                    return False
                for f in depth3x3:
                    if not (0.0 < f < 1.0):  # オブジェクト中心マークが0.0
                        return True
                    if v[2] <= f:
                        return True
                return False

            # Face
            if target_type == bmesh.types.BMFace:
                if prefs.face_center_size and prefs.face_center_line_width:
                    glsettings.prepare_2d()
                    bgl.glLineWidth(prefs.face_center_line_width)
                    if not use_depth or depth_test(median):
                        r2 = prefs.face_center_size / 2
                        v = project(region, rv3d, median)
                        draw_box(v[0] - r2, v[1] - r2, r2 * 2, r2 * 2)
                    bgl.glLineWidth(1)
                    glsettings.restore_2d()

            # Edges (draw with 3d coordinates and GL_DEPTH_TEST)
            if target_type in {bmesh.types.BMEdge, bmesh.types.BMFace}:
                if prefs.edge_line_width:
                    bgl.glLineWidth(prefs.edge_line_width)
                    setlinestyle(prefs.edge_line_stipple)
                    if use_depth:
                        bgl.glEnable(bgl.GL_DEPTH_TEST)
                        ED_view3d_polygon_offset(rv3d, 1)
                    if target_type == bmesh.types.BMEdge:
                        bgl.glBegin(bgl.GL_LINES)
                    else:
                        bgl.glBegin(bgl.GL_LINE_LOOP)
                    for vec in coords:
                        bgl.glVertex3f(*vec)
                    bgl.glEnd()
                    bgl.glLineWidth(1)
                    setlinestyle(0)
                    if use_depth:
                        bgl.glDisable(bgl.GL_DEPTH_TEST)
                        ED_view3d_polygon_offset(rv3d, 0)

            # Verts
            if vert_size:
                bgl.glLineWidth(prefs.vertex_line_width)
                glsettings.prepare_2d()
                for vec in coords:
                    if not use_depth or depth_test(vec):
                        v = project(region, rv3d, vec)
                        draw_circle(v[0], v[1], vert_size, vnum,
                                    poly=False)
                glsettings.restore_2d()
                bgl.glLineWidth(1)

        else:
            # draw loop selection

            if use_depth:
                bgl.glEnable(bgl.GL_DEPTH_TEST)
            else:
                bgl.glDisable(bgl.GL_DEPTH_TEST)
            bgl.glColor4f(*prefs.loop_select_color)

            glsettings.prepare_3d()

            vert_coords, edge_coords, face_coords, median_coords = targets

            if face_coords:
                if use_depth:
                    ED_view3d_polygon_offset(rv3d, 1)
                setpolygontone(True, prefs.loop_select_face_stipple)
                bgl.glBegin(bgl.GL_TRIANGLES)
                for v_coords in face_coords:
                    if len(v_coords) == 3:
                        tris = [(0, 1, 2)]
                    elif len(v_coords) == 4:
                        tris = [(0, 1, 2), (0, 2, 3)]
                    else:
                        tris = mathutils.geometry.tessellate_polygon(
                                [v_coords])
                    for tri in tris:
                        for i in tri:
                            v = mat * v_coords[i]
                            bgl.glVertex3f(*v)
                bgl.glEnd()
                setpolygontone(False)
                if use_depth:
                    ED_view3d_polygon_offset(rv3d, 0)

            elif edge_coords:
                if use_depth:
                    ED_view3d_polygon_offset(rv3d, 1)
                bgl.glLineWidth(prefs.loop_select_line_width)
                setlinestyle(prefs.loop_select_line_stipple)
                bgl.glBegin(bgl.GL_LINES)
                for v_coords in edge_coords:
                    for vec in v_coords:
                        bgl.glVertex3f(*(mat * vec))
                bgl.glEnd()
                setlinestyle(0)
                bgl.glLineWidth(1)
                if use_depth:
                    ED_view3d_polygon_offset(rv3d, 0)

            glsettings.restore_3d()

        glsettings.pop()
        glsettings.font_size()

    @classmethod
    def remove_handler(cls):
        bpy.types.SpaceView3D.draw_handler_remove(cls.handle, 'WINDOW')
        cls.handle = None

    @classmethod
    def remove_invalid_windows(cls):
        """存在しないWindowを除去"""
        exist_windows = []
        for wm in bpy.data.window_managers:
            for win in wm.windows:
                exist_windows.append(win)

        for win in list(cls.data.keys()):
            if win not in exist_windows:
                del cls.data[win]

    def get_selected(self, bm, use_ctypes=False):
        """ctypesを使う場合はインデックスのリスト、
        そうでないならBMElemのリストを返す
        """
        # TODO: ctypesを使ったほうが遅い
        if use_ctypes:
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            selected_verts = get_selected_indices(bm, 'VERT')
            selected_edges = get_selected_indices(bm, 'EDGE')
            selected_faces = get_selected_indices(bm, 'FACE')

        else:
            selected_verts = {elem for elem in bm.verts if elem.select}
            selected_edges = {elem for elem in bm.edges if elem.select}
            selected_faces = {elem for elem in bm.faces if elem.select}

        return selected_verts, selected_edges, selected_faces

    def find_loop_selection(self, context, context_dict,
                            mco_region, ring, toggle, use_ctypes):

        mesh = context.active_object.data
        bm = bmesh.from_edit_mesh(mesh)

        ts = context.tool_settings
        mode = ts.mesh_select_mode[:]
        if mode[2]:
            ring = True

        select_history = list(bm.select_history)
        active_face = bm.faces.active

        verts_pre, edges_pre, faces_pre = self.get_selected(bm, use_ctypes)
        if use_ctypes:
            verts_pre = [bm.verts[i] for i in verts_pre]
            edges_pre = [bm.edges[i] for i in edges_pre]
            faces_pre = [bm.faces[i] for i in faces_pre]

        if ring:
            if mode[2]:
                bpy.ops.mesh.select_mode(False, type='FACE')
            else:
                bpy.ops.mesh.select_mode(False, type='EDGE')
            r = bpy.ops.mesh.edgering_select(
                    context_dict, 'INVOKE_DEFAULT', False,
                    extend=False, deselect=False, toggle=False, ring=True)
        else:
            bpy.ops.mesh.select_mode(False, type='EDGE')
            r = bpy.ops.mesh.loop_select(
                    context_dict, 'INVOKE_DEFAULT', False,
                    extend=False, deselect=False, toggle=False, ring=False)
        if r == {'CANCELLED'}:
            return [], [], [], []

        verts, edges, faces = self.get_selected(bm, use_ctypes)
        if use_ctypes:
            verts = [bm.verts[i] for i in verts]
            edges = [bm.edges[i] for i in edges]
            faces = [bm.faces[i] for i in faces]
        if not ring:
            faces.clear()

        vert_coords = [v.co.copy() for v in verts]
        edge_coords = [[v.co.copy() for v in e.verts] for e in edges]
        face_coords = [[v.co.copy() for v in f.verts] for f in faces]
        medians = [f.calc_center_median() for f in faces]

        bpy.ops.mesh.select_all(context_dict, action='DESELECT')
        context.tool_settings.mesh_select_mode = mode
        if mode == [False, False, True]:
            for f in faces_pre:
                f.select = True
        elif not mode[0]:
            for f in faces_pre:
                f.select = True
            for e in edges_pre:
                e.select = True
        else:
            for f in faces_pre:
                f.select = True
            for e in edges_pre:
                e.select = True
            for v in verts_pre:
                v.select = True

        # restore
        bm.select_history.clear()
        for elem in select_history:
            bm.select_history.add(elem)
        bm.faces.active = active_face

        return vert_coords, edge_coords, face_coords, medians

    def find_nearest(self, context_dict, bm, mco_region, use_ctypes):
        select_history = list(bm.select_history)
        active_face = bm.faces.active

        selected_verts, selected_edges, selected_faces = self.get_selected(
                bm, use_ctypes)
        if use_ctypes:
            bm.verts.index_update()
            bm.edges.index_update()
            bm.faces.index_update()

            def test_select(elem):
                if isinstance(elem, bmesh.types.BMVert):
                    return elem.index in selected_verts
                elif isinstance(elem, bmesh.types.BMEdge):
                    return elem.index in selected_edges
                else:
                    return elem.index in selected_faces

        else:
            def test_select(elem):
                if isinstance(elem, bmesh.types.BMVert):
                    return elem in selected_verts
                elif isinstance(elem, bmesh.types.BMEdge):
                    return elem in selected_edges
                else:
                    return elem in selected_faces

        def set_select(elem):
            elem.select = test_select(elem)

        bm.select_history.clear()
        bpy.ops.view3d.select(context_dict, False, extend=True,
                              location=mco_region)

        active = bm.select_history.active

        if active:
            if isinstance(active, bmesh.types.BMFace):
                # faces
                set_select(active)
                for eve in active.verts:
                    for efa in eve.link_faces:
                        set_select(efa)
                # edges
                for eed in active.edges:
                    set_select(eed)
                for eve in active.verts:
                    for efa in eve.link_faces:
                        for eed in efa.edges:
                            set_select(eed)
                    for eed in eve.link_edges:
                        set_select(eed)
                # verts
                for eve in active.verts:
                    set_select(eve)
                for eve in active.verts:
                    for efa in eve.link_faces:
                        for v in efa.verts:
                            set_select(v)
                    for eed in eve.link_edges:
                        for v in eed.verts:
                            set_select(v)

            elif isinstance(active, bmesh.types.BMEdge):
                # faces
                for eve in active.verts:
                    for efa in eve.link_faces:
                        set_select(efa)
                # edges
                for eve in active.verts:
                    for efa in eve.link_faces:
                        for eed in efa.edges:
                            set_select(eed)
                    for eed in eve.link_edges:
                        set_select(eed)
                set_select(active)
                # verts
                for eve in active.verts:
                    for efa in eve.link_faces:
                        for v in efa.verts:
                            set_select(v)
                    for eed in eve.link_edges:
                        for v in eed.verts:
                            set_select(v)
                    set_select(eve)

            else:
                # faces
                for efa in active.link_faces:
                    set_select(efa)
                #edges
                for efa in active.link_faces:
                    for eed in efa.edges:
                        set_select(eed)
                for eed in active.link_edges:
                    set_select(eed)
                # verts
                for efa in active.link_faces:
                    for eve in efa.verts:
                        set_select(eve)
                for eed in active.link_edges:
                    for eve in eed.verts:
                        set_select(eve)
                set_select(active)

        # restore
        bm.select_history.clear()
        for elem in select_history:
            bm.select_history.add(elem)
        bm.faces.active = active_face

        return active

    def modal(self, context, event):
        """
        :param context:
        :type context: bpy.types.Context
        :param event:
        :type event: bpy.types.Event
        """
        self.remove_invalid_windows()

        # 終了
        win = context.window
        if win not in self.data:
            if not self.data:
                self.remove_handler()
            redraw_areas(context, True)
            return {'FINISHED'}

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                p = space_prop.get(area.spaces.active)
                if p.enable:
                    break
        else:
            return {'PASS_THROUGH'}

        prefs = DrawNearestPreferences.get_prefs()
        data = self.data[win]
        mco = (event.mouse_x, event.mouse_y)
        mco_prev = data.get('mco')
        data['mco'] = mco
        data['target'] = None
        data['targets'] = None
        data['draw_flags'] = {}

        if event.type == 'INBETWEEN_MOUSEMOVE' or context.mode != 'EDIT_MESH':
            return {'PASS_THROUGH'}
        elif event.type == 'MOUSEMOVE':
            if mco == mco_prev:
                return {'PASS_THROUGH'}

        # modal中はcontext.area等は更新されないので手動で求める
        area = region = None
        for sa in context.window.screen.areas:
            if sa.type == 'VIEW_3D':
                if (sa.x <= mco[0] <= sa.x + sa.width and
                        sa.y <= mco[1] <= sa.y + sa.height):
                    area = sa
                    break
        if area:
            for ar in area.regions:
                if ar.type == 'WINDOW':
                    if (ar.x <= mco[0] <= ar.x + ar.width and
                            ar.y <= mco[1] <= ar.y + ar.height):
                        region = ar
                        break

        if not (area and region):
            return {'PASS_THROUGH'}

        v3d = area.spaces.active
        if v3d.viewport_shade == 'RENDERED':
            return {'PASS_THROUGH'}

        bm = bmesh.from_edit_mesh(context.active_object.data)
        context_dict = context.copy()
        context_dict.update({'area': area, 'region': region})
        mco_region = [mco[0] - region.x, mco[1] - region.y]

        shift = event.shift
        ctrl = event.ctrl
        alt = event.alt
        oskey = event.oskey
        if event.type in {'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            if event.value == 'PRESS':
                shift = True
            elif event.value == 'RELEASE':
                shift = False
        if event.type in {'LEFT_CTRL', 'RIGHT_CTRL'}:
            if event.value == 'PRESS':
                ctrl = True
            elif event.value == 'RELEASE':
                ctrl = False
        if event.type in {'LEFT_ALT', 'RIGHT_ALT'}:
            if event.value == 'PRESS':
                alt = True
            elif event.value == 'RELEASE':
                alt = False
        if event.type in {'OSKEY'}:
            if event.value == 'PRESS':
                oskey = True
            elif event.value == 'RELEASE':
                oskey = False

        mode = ''
        ring = False
        toggle = False
        for kmi in self.keymap_items['loop_select']:
            if (kmi.shift == shift and kmi.ctrl == ctrl and
                    kmi.alt == alt and kmi.oskey == oskey):
                mode = 'loop_select'
                toggle = kmi.properties.toggle
                break
        for kmi in self.keymap_items['edgering_select']:
            if (kmi.shift == shift and kmi.ctrl == ctrl and
                    kmi.alt == alt and kmi.oskey == oskey):
                mode = 'edgering_select'
                toggle = kmi.properties.toggle
                ring = True
        if not mode:
            mode = 'select'

        # オペレータ実行時にScene.update()が実行され
        # lockcoordsのまで呼び出されてしまうから無効化しておく
        scene_pre = list(bpy.app.handlers.scene_update_pre)
        bpy.app.handlers.scene_update_pre.clear()
        scene_post = list(bpy.app.handlers.scene_update_post)
        bpy.app.handlers.scene_update_post.clear()

        if mode == 'select':
            if test_platform() and prefs.use_ctypes:
                context_dict_bak = context_py_dict_get(context)
                context_py_dict_set(context, context_dict)
                find, (eve, eed, efa) = unified_findnearest(
                    context, bm, mco_region)
                context_py_dict_set(context, context_dict_bak)
                if find:
                    elem = eve or eed or efa
                else:
                    elem = None
            else:
                elem = self.find_nearest(context_dict, bm, mco_region,
                                         False)
            if elem:
                if isinstance(elem, bmesh.types.BMVert):
                    coords = [elem.co.copy()]
                    median = elem.co.copy()
                else:
                    coords = [v.co.copy() for v in elem.verts]
                    if isinstance(elem, bmesh.types.BMEdge):
                        median = (coords[0] + coords[1]) / 2
                    else:
                        median = elem.calc_center_median()
                data['target'] = [type(elem), coords, median]

        elif prefs.use_loop_select:
            if test_platform() and prefs.use_ctypes:
                r = mouse_mesh_loop(context, bm, mco_region, False, False, toggle, ring)
                vert_coords = []
                edge_coords = []
                face_coords = []
                medians = []
                if r[0]:
                    elems = r[1]
                    if elems:
                        if isinstance(elems[0], bmesh.types.BMEdge):
                            edge_coords = [[v.co.copy() for v in e.verts] for e in elems]
                        elif isinstance(elems[0], bmesh.types.BMFace):
                            face_coords = [[v.co.copy() for v in f.verts] for f in elems]
                            medians = [f.calc_center_median() for f in elems]
            else:
                vert_coords, edge_coords, face_coords, medians = \
                    self.find_loop_selection(
                        context, context_dict, mco_region, ring, toggle,
                        False)
            if vert_coords or edge_coords or face_coords:
                data['targets'] = [vert_coords, edge_coords, face_coords,
                                   medians]

        bpy.app.handlers.scene_update_pre[:] = scene_pre
        bpy.app.handlers.scene_update_post[:] = scene_post

        # 存在しないrv3dを除去し、全ての値をTrueとする
        data['draw_flags'] = {}
        for sa in context.window.screen.areas:
            if sa.type == 'VIEW_3D':
                space_data = sa.spaces.active
                """:type: bpy.types.SpaceView3D"""
                data['draw_flags'][space_data.region_3d] = True
                for rv3d in space_data.region_quadviews:
                    data['draw_flags'][rv3d] = True

        # 再描画
        if data['target'] or data['targets']:
            # ctypesを使わない、又はtargetsを探す場合は
            # オペレータを使用しているのでどの道再描画される
            if prefs.use_ctypes:
                redraw = True
                if data['target']:
                    if data['target'] != data['target_prev']:
                        redraw = True
                else:
                    if not data['targets_prev']:
                        redraw = True
                    else:
                        vert_coords_prev = data['targets_prev'][0]
                        if len(vert_coords) != len(vert_coords_prev):
                            redraw = True
                        else:
                            for v1, v2 in zip(vert_coords, vert_coords_prev):
                                if v1 != v2:
                                    redraw = True
                                    break
                if redraw:
                    if prefs.redraw_all:
                        redraw_areas(context)
                    else:
                        area.tag_redraw()
        else:
            if self.fond_area_prev:
                self.fond_area_prev.tag_redraw()
        data['target_prev'] = data['target']
        data['targets_prev'] = data['targets']
        if data['target'] or data['targets']:
            self.fond_area_prev = area
        else:
            self.fond_area_prev = None

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if self.type == 'KILL':
            self.data.clear()
            redraw_areas(context, True)
            return {'FINISHED'}

        win = context.window
        v3d = context.space_data
        prop = space_prop.get(v3d)
        type = self.type
        if self.type == 'TOGGLE':
            if prop.enable:
                type = 'DISABLE'
            else:
                type = 'ENABLE'

        self.__class__.keymap_items = {
            'loop_select': [], 'edgering_select': []}
        kc = bpy.context.window_manager.keyconfigs.user
        km = kc.keymaps['Mesh']
        for kmi in km.keymap_items:
            if kmi.type == 'SELECTMOUSE':
                if kmi.idname in {'mesh.loop_select', 'mesh.edgering_select'}:
                    if kmi.properties.ring:
                        self.keymap_items['edgering_select'].append(kmi)
                    else:
                        self.keymap_items['loop_select'].append(kmi)

        if type == 'DISABLE':
            # modalを終了すると自動起動の為の監視関数が必要になる為何もしない
            return {'FINISHED'}
        else:
            if win in self.data:
                return {'FINISHED'}
            self.data[win] = d = {}
            d['event'] = event
            d['target'] = None
            d['target_prev'] = None
            d['targets'] = None
            d['targets_prev'] = None
            d['draw_flags'] = {}
            if not self.handle:
                self.__class__.handle = bpy.types.SpaceView3D.draw_handler_add(
                    self.draw_func, (context,), 'WINDOW', 'POST_VIEW')
            self.fond_area_prev = False
            context.window_manager.modal_handler_add(self)

            return {'RUNNING_MODAL'}

    @classmethod
    def unregister(cls):
        cls.data.clear()
        try:
            cls.remove_handler()
        except:
            pass


def menu_func(self, context):
    prop = space_prop.get(context.space_data)
    self.layout.separator()
    col = self.layout.column(align=True)
    """:type: bpy.types.UILayout"""
    v3d = context.space_data
    if context.mode != 'EDIT_MESH' or v3d.viewport_shade == 'RENDERED':
        col.active = False
    col.prop(prop, 'enable', text='Draw Nearest')
    # col.active = context.window in VIEW3D_OT_draw_nearest_element.data
    # col.operator('view3d.draw_nearest_element', text='Draw Nearest')


def operator_call(op, *args, _scene_update=True, **kw):
    """vawmより
    operator_call(bpy.ops.view3d.draw_nearest_element,
                  'INVOKE_DEFAULT', type='ENABLE', _scene_update=False)
    """
    import bpy
    from _bpy import ops as ops_module

    BPyOpsSubModOp = op.__class__
    op_call = ops_module.call
    context = bpy.context

    # Get the operator from blender
    wm = context.window_manager

    # run to account for any rna values the user changes.
    if _scene_update:
        BPyOpsSubModOp._scene_update(context)

    if args:
        C_dict, C_exec, C_undo = BPyOpsSubModOp._parse_args(args)
        ret = op_call(op.idname_py(), C_dict, kw, C_exec, C_undo)
    else:
        ret = op_call(op.idname_py(), None, kw)

    if 'FINISHED' in ret and context.window_manager == wm:
        if _scene_update:
            BPyOpsSubModOp._scene_update(context)

    return ret


@bpy.app.handlers.persistent
def scene_update_pre(scene):
    win = bpy.context.window
    if not win:  # アニメーションレンダリング時にて
        return
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            v3d = area.spaces.active
            p = space_prop.get(v3d)
            if p.enable:
                if win not in VIEW3D_OT_draw_nearest_element.data:
                    c = bpy.context.copy()
                    c['area'] = area
                    c['region'] = area.regions[-1]
                    operator_call(
                        bpy.ops.view3d.draw_nearest_element,
                        c, 'INVOKE_DEFAULT', type='ENABLE',
                        _scene_update=False)
                break
    else:
        # disable ?
        pass


@bpy.app.handlers.persistent
def load_pre(dummy):
    VIEW3D_OT_draw_nearest_element.unregister()


classes = [
    DrawNearestPreferences,
    VIEW3D_PG_DrawNearest,
    VIEW3D_OT_draw_nearest_element,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    space_prop.register()
    bpy.types.VIEW3D_PT_view3d_meshdisplay.append(menu_func)
    bpy.app.handlers.scene_update_pre.append(scene_update_pre)
    bpy.app.handlers.load_pre.append(load_pre)


def unregister():
    bpy.app.handlers.scene_update_pre.remove(scene_update_pre)
    bpy.app.handlers.load_pre.remove(load_pre)
    bpy.types.VIEW3D_PT_view3d_meshdisplay.remove(menu_func)
    space_prop.unregister()
    for cls in classes[::-1]:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
