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

# Another Noise Tool - Functions
# Jimmy Hazevoet

# ErosionR:
# Michel Anders, Ian Huish

# import modules
import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        IntProperty,
        PointerProperty,
        )
from math import (
        sin, cos, pi,
        )
from .ant_noise import noise_gen

# ------------------------------------------------------------
# Create a new mesh (object) from verts/edges/faces.
# verts/edges/faces ... List of vertices/edges/faces for the
#                    new mesh (as used in from_pydata).
# name ... Name of the new mesh (& object)

from bpy_extras import object_utils

def create_mesh_object(context, verts, edges, faces, name):
    # Create new mesh
    mesh = bpy.data.meshes.new(name)
    # Make a mesh from a list of verts/edges/faces.
    mesh.from_pydata(verts, [], faces)
    # Update mesh geometry after adding stuff.
    mesh.update()
    return object_utils.object_data_add(context, mesh, operator=None)


# Generate XY Grid
def grid_gen(sub_d_x, sub_d_y, tri, meshsize_x, meshsize_y, props, water_plane, water_level):
    verts = []
    faces = []
    vappend = verts.append
    fappend = faces.append
    for i in range (0, sub_d_x):
        x = meshsize_x * (i / (sub_d_x - 1) - 1 / 2)
        for j in range(0, sub_d_y):
            y = meshsize_y * (j / (sub_d_y - 1) - 1 / 2)
            if not water_plane:
                z = noise_gen((x, y, 0), props)
            else:
                z = water_level
            vappend((x,y,z))

            if i > 0 and j > 0:
                A = i * sub_d_y + (j - 1)
                B = i * sub_d_y + j
                C = (i - 1) * sub_d_y + j
                D = (i - 1) * sub_d_y + (j - 1)
                if not tri:
                    fappend((A, B, C, D))
                else:
                    fappend((A, B, D))
                    fappend((B, C, D))

    return verts, faces


# Generate UV Sphere
def sphere_gen(sub_d_x, sub_d_y, tri, meshsize, props, water_plane, water_level):
    verts = []
    faces = []
    vappend = verts.append
    fappend = faces.append
    sub_d_x += 1
    sub_d_y += 1
    for i in range(0, sub_d_x):
        for j in range(0, sub_d_y):
            u = sin(j * pi * 2 / (sub_d_y - 1)) * cos(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            v = cos(j * pi * 2 / (sub_d_y - 1)) * cos(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            w = sin(-pi / 2 + i * pi / (sub_d_x - 1)) * meshsize / 2
            if water_plane:
                h = water_level
            else:
                h = 0.0
                #noise_gen((u, v, w), props) / meshsize
            vappend(((u + u * h), (v + v * h), (w + w * h)))

    count = 0
    for i in range (0, sub_d_y * (sub_d_x - 1)):
        if count < sub_d_y - 1 :
            A = i + 1
            B = i
            C = (i + sub_d_y)
            D = (i + sub_d_y) + 1
            if tri:
                fappend((A, B, D))
                fappend((B, C, D))
            else:
                fappend((A, B, C, D))
            count = count + 1
        else:
            count = 0

    return verts, faces


# ------------------------------------------------------------
# Do refresh - redraw
class FilmSetRefresh(bpy.types.Operator):
    bl_idname = "mesh.fsb_filmset_refresh"
    bl_label = "Refresh"
    bl_description = "Refresh landscape with current settings"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        ob = bpy.context.active_object
        return (ob.fsb_filmset and not ob.fsb_filmset.sphere_mesh)

    def execute(self, context):
        # ant object items
        obj = bpy.context.active_object

        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.object.mode_set(mode = 'OBJECT')

        keys = obj.fsb_filmset.keys()
        if keys:
            ob = obj.fsb_filmset
            prop = []
            for key in keys:
                prop.append(getattr(ob, key))

            # redraw verts
            mesh = obj.data

            if ob['vert_group'] != "" and ob['vert_group'] in obj.vertex_groups:
                vertex_group = obj.vertex_groups[ob['vert_group']]
                gi = vertex_group.index
                for v in mesh.vertices:
                    for g in v.groups:
                        if g.group == gi:
                            v.co[2] = 0.0
                            v.co[2] = vertex_group.weight(v.index) * noise_gen(v.co, prop)
            else:
                for v in mesh.vertices:
                    v.co[2] = 0.0
                    v.co[2] = noise_gen(v.co, prop)
            mesh.update()
        else:
            pass

        return {'FINISHED'}

# ------------------------------------------------------------
# Do regenerate
class FilmSetRegenerate(bpy.types.Operator):
    bl_idname = "mesh.fsb_filmset_regenerate"
    bl_label = "Regenerate"
    bl_description = "Regenerate landscape with current settings"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        ob = bpy.context.active_object
        if ob.mode == 'EDIT':
            return False
        return ob.fsb_filmset


    def execute(self, context):

        view_layer = bpy.context.view_layer
        # ant object items
        obj = bpy.context.active_object

        keys = obj.fsb_filmset.keys()
        if keys:
            ob = obj.fsb_filmset
            ant_props = []
            for key in keys:
                ant_props.append(getattr(ob, key))

            new_name = obj.name

            # Main function, create landscape mesh object
            if ob['sphere_mesh']:
                # sphere
                verts, faces = sphere_gen(
                        ob['subdivision_y'],
                        ob['subdivision_x'],
                        ob['tri_face'],
                        ob['mesh_size'],
                        ant_props,
                        False,
                        0.0
                        )
                new_ob = create_mesh_object(context, verts, [], faces, new_name)
                if ob['remove_double']:
                    new_ob.select_set(True)
                    bpy.ops.object.mode_set(mode = 'EDIT')
                    bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False)
                    bpy.ops.object.mode_set(mode = 'OBJECT')
            else:
                # grid
                verts, faces = grid_gen(
                        ob['subdivision_x'],
                        ob['subdivision_y'],
                        ob['tri_face'],
                        ob['mesh_size_x'],
                        ob['mesh_size_y'],
                        ant_props,
                        False,
                        0.0
                        )
                new_ob = create_mesh_object(context, verts, [], faces, new_name)

            new_ob.select_set(True)

            if ob['smooth_mesh']:
                bpy.ops.object.shade_smooth()

            # Landscape Material
            if ob['land_material'] != "" and ob['land_material'] in bpy.data.materials:
                mat = bpy.data.materials[ob['land_material']]
                bpy.context.object.data.materials.append(mat)

            # Water plane
            if ob['water_plane']:
                if ob['sphere_mesh']:
                    # sphere
                    verts, faces = sphere_gen(
                            ob['subdivision_y'],
                            ob['subdivision_x'],
                            ob['tri_face'],
                            ob['mesh_size'],
                            ant_props,
                            ob['water_plane'],
                            ob['water_level']
                            )
                    wobj = create_mesh_object(context, verts, [], faces, new_name+"_plane")
                    if ob['remove_double']:
                        wobj.select_set(True)
                        bpy.ops.object.mode_set(mode = 'EDIT')
                        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False)
                        bpy.ops.object.mode_set(mode = 'OBJECT')
                else:
                    # grid
                    verts, faces = grid_gen(
                            2,
                            2,
                            ob['tri_face'],
                            ob['mesh_size_x'],
                            ob['mesh_size_y'],
                            ant_props,
                            ob['water_plane'],
                            ob['water_level']
                            )
                    wobj = create_mesh_object(context, verts, [], faces, new_name+"_plane")

                wobj.select_set(True)

                if ob['smooth_mesh']:
                    bpy.ops.object.shade_smooth()

                # Water Material
                if ob['water_material'] != "" and ob['water_material'] in bpy.data.materials:
                    mat = bpy.data.materials[ob['water_material']]
                    bpy.context.object.data.materials.append(mat)

            # Loc Rot Scale
            if ob['water_plane']:
                wobj.location = obj.location
                wobj.rotation_euler = obj.rotation_euler
                wobj.scale = obj.scale
                wobj.select_set(False)

            new_ob.location = obj.location
            new_ob.rotation_euler = obj.rotation_euler
            new_ob.scale = obj.scale

            # Store props
            new_ob = store_properties(ob, new_ob)

            # Delete old object
            new_ob.select_set(False)

            obj.select_set(True)
            view_layer.objects.active = obj
            bpy.ops.object.delete(use_global=False)

            # Select landscape and make active
            new_ob.select_set(True)
            view_layer.objects.active = new_ob

        return {'FINISHED'}


# ------------------------------------------------------------
# Z normal value to vertex group (Slope map)
class AntVgSlopeMap(bpy.types.Operator):
    bl_idname = "mesh.ant_slope_map"
    bl_label = "Weight from Slope"
    bl_description = "A.N.T. Slope Map - z normal value to vertex group weight"
    bl_options = {'REGISTER', 'UNDO'}

    z_method: EnumProperty(
            name="Method:",
            default='SLOPE_Z',
            items=[
                ('SLOPE_Z', "Z Slope", "Slope for planar mesh"),
                ('SLOPE_XYZ', "Sphere Slope", "Slope for spherical mesh")
                ])
    group_name: StringProperty(
            name="Vertex Group Name:",
            default="Slope",
            description="Name"
            )
    select_flat: BoolProperty(
            name="Vert Select:",
            default=True,
            description="Select vertices on flat surface"
            )
    select_range: FloatProperty(
            name="Vert Select Range:",
            default=0.0,
            min=0.0,
            max=1.0,
            description="Increase to select more vertices on slopes"
            )

    @classmethod
    def poll(cls, context):
        ob = context.object
        return (ob and ob.type == 'MESH')


    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


    def execute(self, context):
        message = "Popup Values: %d, %f, %s, %s" % \
            (self.select_flat, self.select_range, self.group_name, self.z_method)
        self.report({'INFO'}, message)

        bpy.ops.object.mode_set(mode='OBJECT')
        ob = bpy.context.active_object
        dim = ob.dimensions

        if self.select_flat:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.context.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.vertex_group_add()
        vg_normal = ob.vertex_groups.active

        for v in ob.data.vertices:
            if self.z_method == 'SLOPE_XYZ':
                zval = (v.co.normalized() * v.normal.normalized()) * 2 - 1
            else:
                zval = v.normal[2]

            vg_normal.add([v.index], zval, 'REPLACE')

            if self.select_flat:
                if zval >= (1.0 - self.select_range):
                    v.select = True

        vg_normal.name = self.group_name

        bpy.ops.paint.weight_paint_toggle()
        return {'FINISHED'}


# ------------------------------------------------------------
# draw properties

def draw_ant_refresh(self, context):
    layout = self.layout
    if self.auto_refresh is False:
        self.refresh = False
    elif self.auto_refresh is True:
        self.refresh = True
    row = layout.box().row()
    split = row.split()
    split.scale_y = 1.5
    split.prop(self, "auto_refresh", toggle=True, icon_only=True, icon='AUTO')
    split.prop(self, "refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')


def draw_ant_main(self, context, generate=True):
    layout = self.layout
    box = layout.box()
    box.prop(self, "show_main_settings", toggle=True)
    if self.show_main_settings:
        if generate:
            row = box.row(align=True)
            split = row.split(align=True)

            split.prop(self, "at_cursor", toggle=True, icon_only=True, icon='PIVOT_CURSOR')

            split.prop(self, "smooth_mesh", toggle=True, icon_only=True, icon='SHADING_SOLID')
            split.prop(self, "tri_face", toggle=True, text="Triangulate", icon='MESH_DATA')

            if not self.sphere_mesh:
                row = box.row(align=True)
                row.prop(self, "sphere_mesh", toggle=True)
            else:
                row = box.row(align=True)
                split = row.split(factor=0.5, align=True)
                split.prop(self, "sphere_mesh", toggle=True)
                split.prop(self, "remove_double", toggle=True)

            box.prop(self, "ant_terrain_name")
            box.prop_search(self, "land_material",  bpy.data, "materials")

        col = box.column(align=True)
        col.prop(self, "subdivision_x")
        col.prop(self, "subdivision_y")
        col = box.column(align=True)
        if self.sphere_mesh:
            col.prop(self, "mesh_size")
        else:
            col.prop(self, "mesh_size_x")
            col.prop(self, "mesh_size_y")


def draw_ant_noise(self, context, generate=True):
    layout = self.layout
    box = layout.box()
    box.prop(self, "show_noise_settings", toggle=True)
    if self.show_noise_settings:
        box.prop(self, "noise_type")
        if self.noise_type == "blender_texture":
            box.prop_search(self, "texture_block", bpy.data, "textures")
        else:
            box.prop(self, "basis_type")

        col = box.column(align=True)
        col.prop(self, "random_seed")
        col = box.column(align=True)
        col.prop(self, "noise_offset_x")
        col.prop(self, "noise_offset_y")
        if self.sphere_mesh == True or generate == False:
            col.prop(self, "noise_offset_z")
        col.prop(self, "noise_size_x")
        col.prop(self, "noise_size_y")
        if self.sphere_mesh == True or generate == False:
            col.prop(self, "noise_size_z")

        col = box.column(align=True)
        col.prop(self, "noise_size")

        col = box.column(align=True)
        if self.noise_type == "multi_fractal":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
        elif self.noise_type == "ridged_multi_fractal":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "gain")
        elif self.noise_type == "hybrid_multi_fractal":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "gain")
        elif self.noise_type == "hetero_terrain":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
        elif self.noise_type == "fractal":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
        elif self.noise_type == "turbulence_vector":
            col.prop(self, "noise_depth")
            col.prop(self, "amplitude")
            col.prop(self, "frequency")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)
        elif self.noise_type == "variable_lacunarity":
            box.prop(self, "vl_basis_type")
            box.prop(self, "distortion")
        elif self.noise_type == "marble_noise":
            box.prop(self, "marble_shape")
            box.prop(self, "marble_bias")
            box.prop(self, "marble_sharp")
            col = box.column(align=True)
            col.prop(self, "distortion")
            col.prop(self, "noise_depth")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)
        elif self.noise_type == "shattered_hterrain":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "distortion")
        elif self.noise_type == "strata_hterrain":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "distortion", text="Strata")
        elif self.noise_type == "ant_turbulence":
            col.prop(self, "noise_depth")
            col.prop(self, "amplitude")
            col.prop(self, "frequency")
            col.prop(self, "distortion")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)
        elif self.noise_type == "vl_noise_turbulence":
            col.prop(self, "noise_depth")
            col.prop(self, "amplitude")
            col.prop(self, "frequency")
            col.prop(self, "distortion")
            col.separator()
            box.prop(self, "vl_basis_type")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)
        elif self.noise_type == "vl_hTerrain":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "distortion")
            col.separator()
            box.prop(self, "vl_basis_type")
        elif self.noise_type == "distorted_heteroTerrain":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "distortion")
            col.separator()
            box.prop(self, "vl_basis_type")
        elif self.noise_type == "double_multiFractal":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "offset")
            col.prop(self, "gain")
            col.separator()
            box.prop(self, "vl_basis_type")
        elif self.noise_type == "rocks_noise":
            col.prop(self, "noise_depth")
            col.prop(self, "distortion")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)
        elif self.noise_type == "slick_rock":
            col.prop(self, "noise_depth")
            col.prop(self, "dimension")
            col.prop(self, "lacunarity")
            col.prop(self, "gain")
            col.prop(self, "offset")
            col.prop(self, "distortion")
            col.separator()
            box.prop(self, "vl_basis_type")
        elif self.noise_type == "planet_noise":
            col.prop(self, "noise_depth")
            col.separator()
            row = col.row(align=True)
            row.prop(self, "hard_noise", expand=True)

        # Effects mix
        col = box.column(align=False)
        box.prop(self, "fx_type")
        if self.fx_type != "0":
            if int(self.fx_type) <= 12:
                box.prop(self, "fx_bias")

            box.prop(self, "fx_mix_mode")
            col = box.column(align=True)
            col.prop(self, "fx_mixfactor")

            col = box.column(align=True)
            col.prop(self, "fx_loc_x")
            col.prop(self, "fx_loc_y")
            col.prop(self, "fx_size")

            col = box.column(align=True)
            col.prop(self, "fx_depth")
            if self.fx_depth != 0:
                col.prop(self, "fx_frequency")
                col.prop(self, "fx_amplitude")
            col.prop(self, "fx_turb")

            col = box.column(align=True)
            row = col.row(align=True).split(factor=0.92, align=True)
            row.prop(self, "fx_height")
            row.prop(self, "fx_invert", toggle=True, text="", icon='ARROW_LEFTRIGHT')
            col.prop(self, "fx_offset")


def draw_ant_displace(self, context, generate=True):
    layout = self.layout
    box = layout.box()
    box.prop(self, "show_displace_settings", toggle=True)
    if self.show_displace_settings:
        if not generate:
            col = box.column(align=False)
            col.prop(self, "direction", toggle=True)

        col = box.column(align=True)
        row = col.row(align=True).split(factor=0.92, align=True)
        row.prop(self, "height")
        row.prop(self, "height_invert", toggle=True, text="", icon='ARROW_LEFTRIGHT')
        col.prop(self, "height_offset")
        col.prop(self, "maximum")
        col.prop(self, "minimum")
        if generate:
            if not self.sphere_mesh:
                col = box.column()
                col.prop(self, "edge_falloff")
                if self.edge_falloff != "0":
                    col = box.column(align=True)
                    col.prop(self, "edge_level")
                    if self.edge_falloff in ["2", "3"]:
                        col.prop(self, "falloff_x")
                    if self.edge_falloff in ["1", "3"]:
                        col.prop(self, "falloff_y")

        col = box.column()
        col.prop(self, "strata_type")
        if self.strata_type != "0":
            col = box.column()
            col.prop(self, "strata")

        if not generate:
            col = box.column(align=False)
            col.prop_search(self, "vert_group",  bpy.context.object, "vertex_groups")


def draw_ant_water(self, context):
    layout = self.layout
    box = layout.box()
    col = box.column()
    col.prop(self, "water_plane", toggle=True)
    if self.water_plane:
        col = box.column(align=True)
        col.prop_search(self, "water_material",  bpy.data, "materials")
        col = box.column()
        col.prop(self, "water_level")


# Store propereties
def store_properties(operator, ob):
    ob.fsb_filmset.ant_terrain_name = operator.ant_terrain_name
    ob.fsb_filmset.at_cursor = operator.at_cursor
    ob.fsb_filmset.smooth_mesh = operator.smooth_mesh
    ob.fsb_filmset.tri_face = operator.tri_face
    ob.fsb_filmset.sphere_mesh = operator.sphere_mesh
    ob.fsb_filmset.land_material = operator.land_material
    ob.fsb_filmset.water_material = operator.water_material
    ob.fsb_filmset.texture_block = operator.texture_block
    ob.fsb_filmset.subdivision_x = operator.subdivision_x
    ob.fsb_filmset.subdivision_y = operator.subdivision_y
    ob.fsb_filmset.mesh_size_x = operator.mesh_size_x
    ob.fsb_filmset.mesh_size_y = operator.mesh_size_y
    ob.fsb_filmset.mesh_size = operator.mesh_size
    ob.fsb_filmset.random_seed = operator.random_seed
    ob.fsb_filmset.noise_offset_x = operator.noise_offset_x
    ob.fsb_filmset.noise_offset_y = operator.noise_offset_y
    ob.fsb_filmset.noise_offset_z = operator.noise_offset_z
    ob.fsb_filmset.noise_size_x = operator.noise_size_x
    ob.fsb_filmset.noise_size_y = operator.noise_size_y
    ob.fsb_filmset.noise_size_z = operator.noise_size_z
    ob.fsb_filmset.noise_size = operator.noise_size
    ob.fsb_filmset.noise_type = operator.noise_type
    ob.fsb_filmset.basis_type = operator.basis_type
    ob.fsb_filmset.vl_basis_type = operator.vl_basis_type
    ob.fsb_filmset.distortion = operator.distortion
    ob.fsb_filmset.hard_noise = operator.hard_noise
    ob.fsb_filmset.noise_depth = operator.noise_depth
    ob.fsb_filmset.amplitude = operator.amplitude
    ob.fsb_filmset.frequency = operator.frequency
    ob.fsb_filmset.dimension = operator.dimension
    ob.fsb_filmset.lacunarity = operator.lacunarity
    ob.fsb_filmset.offset = operator.offset
    ob.fsb_filmset.gain = operator.gain
    ob.fsb_filmset.marble_bias = operator.marble_bias
    ob.fsb_filmset.marble_sharp = operator.marble_sharp
    ob.fsb_filmset.marble_shape = operator.marble_shape
    ob.fsb_filmset.height = operator.height
    ob.fsb_filmset.height_invert = operator.height_invert
    ob.fsb_filmset.height_offset = operator.height_offset
    ob.fsb_filmset.maximum = operator.maximum
    ob.fsb_filmset.minimum = operator.minimum
    ob.fsb_filmset.edge_falloff = operator.edge_falloff
    ob.fsb_filmset.edge_level = operator.edge_level
    ob.fsb_filmset.falloff_x = operator.falloff_x
    ob.fsb_filmset.falloff_y = operator.falloff_y
    ob.fsb_filmset.strata_type = operator.strata_type
    ob.fsb_filmset.strata = operator.strata
    ob.fsb_filmset.water_plane = operator.water_plane
    ob.fsb_filmset.water_level = operator.water_level
    ob.fsb_filmset.vert_group = operator.vert_group
    ob.fsb_filmset.remove_double = operator.remove_double
    ob.fsb_filmset.fx_mixfactor = operator.fx_mixfactor
    ob.fsb_filmset.fx_mix_mode = operator.fx_mix_mode
    ob.fsb_filmset.fx_type = operator.fx_type
    ob.fsb_filmset.fx_bias = operator.fx_bias
    ob.fsb_filmset.fx_turb = operator.fx_turb
    ob.fsb_filmset.fx_depth = operator.fx_depth
    ob.fsb_filmset.fx_frequency = operator.fx_frequency
    ob.fsb_filmset.fx_amplitude = operator.fx_amplitude
    ob.fsb_filmset.fx_size = operator.fx_size
    ob.fsb_filmset.fx_loc_x = operator.fx_loc_x
    ob.fsb_filmset.fx_loc_y = operator.fx_loc_y
    ob.fsb_filmset.fx_height = operator.fx_height
    ob.fsb_filmset.fx_offset = operator.fx_offset
    ob.fsb_filmset.fx_invert = operator.fx_invert
    return ob


# ------------------------------------------------------------
# "name": "ErosionR"
# "author": "Michel Anders, Ian Huish"

from random import random as rand
from math import tan, radians
from .eroder import Grid
from .stats import Stats
from .utils import numexpr_available


def availableVertexGroupsOrNone(self, context):
    groups = [ ('None', 'None', 'None', 1) ]
    return groups + [(name, name, name, n+1) for n,name in enumerate(context.active_object.vertex_groups.keys())]


class Eroder(bpy.types.Operator):
    bl_idname = "mesh.eroder"
    bl_label = "ErosionR"
    bl_description = "Apply various kinds of erosion to a square ANT-Landscape grid. Also available in Weight Paint mode > Weights menu"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    Iterations: IntProperty(
            name="Iterations",
            description="Number of overall iterations",
            default=1,
            min=1,
            soft_max=100
            )
    IterRiver: IntProperty(
            name="River Iterations",
            description="Number of river iterations",
            default=30,
            min=1,
            soft_max=1000
            )
    IterAva: IntProperty(
            name="Avalanche Iterations",
            description="Number of avalanche iterations",
            default=5,
            min=1,
            soft_max=10
            )
    IterDiffuse: IntProperty(
            name="Diffuse Iterations",
            description="Number of diffuse iterations",
            default=5,
            min=1,
            soft_max=10
            )
    Ef: FloatProperty(
            name="Rain on Plains",
            description="1 gives equal rain across the terrain, 0 rains more at the mountain tops",
            default=0.0,
            min=0,
            max=1
            )
    Kd: FloatProperty(
            name="Kd",
            description="Thermal diffusion rate (1.0 is a fairly high rate)",
            default=0.1,
            min=0,
            soft_max=100
            )
    Kt: FloatProperty(
            name="Kt",
            description="Maximum stable talus angle",
            default=radians(60),
            min=0,
            max=radians(90),
            subtype='ANGLE'
            )
    Kr: FloatProperty(
            name="Rain amount",
            description="Total Rain amount",
            default=.01,
            min=0,
            soft_max=1,
            precision=3
            )
    Kv: FloatProperty(
            name="Rain variance",
            description="Rain variance (0 is constant, 1 is uniform)",
            default=0,
            min=0,
            max=1
            )
    userainmap: BoolProperty(
            name="Use rain map",
            description="Use active vertex group as a rain map",
            default=True
            )
    Ks: FloatProperty(
            name="Soil solubility",
            description="Soil solubility - how quickly water quickly reaches saturation point",
            default=0.5,
            min=0,
            soft_max=1
            )
    Kdep: FloatProperty(
            name="Deposition rate",
            description="Sediment deposition rate - how quickly silt is laid down once water stops flowing quickly",
            default=0.1,
            min=0,
            soft_max=1
            )
    Kz: FloatProperty(name="Fluvial Erosion Rate",
            description="Amount of sediment moved each main iteration - if 0, then rivers are formed but the mesh is not changed",
            default=0.3,
            min=0,
            soft_max=20
            )
    Kc: FloatProperty(
            name="Carrying capacity",
            description="Base sediment carrying capacity",
            default=0.9,
            min=0,
            soft_max=1
            )
    Ka: FloatProperty(
            name="Slope dependence",
            description="Slope dependence of carrying capacity (not used)",
            default=1.0,
            min=0,
            soft_max=2
            )
    Kev: FloatProperty(
            name="Evaporation",
            description="Evaporation Rate per grid square in % - causes sediment to be dropped closer to the hills",
            default=.5,
            min=0,
            soft_max=2
            )
    numexpr: BoolProperty(
            name="Numexpr",
            description="Use numexpr module (if available)",
            default=True
            )
    Pd: FloatProperty(
            name="Diffusion Amount",
            description="Diffusion probability",
            default=0.2,
            min=0,
            max=1
            )
    Pa: FloatProperty(
            name="Avalanche Amount",
            description="Avalanche amount",
            default=0.5,
            min=0,
            max=1
            )
    Pw: FloatProperty(
            name="River Amount",
            description="Water erosion probability",
            default=1,
            min=0,
            max=1
            )
    smooth: BoolProperty(
            name="Smooth",
            description="Set smooth shading",
            default=True
            )
    showiterstats: BoolProperty(
            name="Iteration Stats",
            description="Show iteraration statistics",
            default=False
            )
    showmeshstats: BoolProperty(name="Mesh Stats",
            description="Show mesh statistics",
            default=False
            )

    stats = Stats()
    counts= {}

    def execute(self, context):

        ob = context.active_object
        me = ob.data
        self.stats.reset()
        try:
            vgActive = ob.vertex_groups.active.name
        except:
            vgActive = "capacity"
        print("ActiveGroup", vgActive)
        try:
            vg=ob.vertex_groups["rainmap"]
        except:
            vg=ob.vertex_groups.new(name="rainmap")
        try:
            vgscree=ob.vertex_groups["scree"]
        except:
            vgscree=ob.vertex_groups.new(name="scree")
        try:
            vgavalanced=ob.vertex_groups["avalanced"]
        except:
            vgavalanced=ob.vertex_groups.new(name="avalanced")
        try:
            vgw=ob.vertex_groups["water"]
        except:
            vgw=ob.vertex_groups.new(name="water")
        try:
            vgscour=ob.vertex_groups["scour"]
        except:
            vgscour=ob.vertex_groups.new(name="scour")
        try:
            vgdeposit=ob.vertex_groups["deposit"]
        except:
            vgdeposit=ob.vertex_groups.new(name="deposit")
        try:
            vgflowrate=ob.vertex_groups["flowrate"]
        except:
            vgflowrate=ob.vertex_groups.new(name="flowrate")
        try:
            vgsediment=ob.vertex_groups["sediment"]
        except:
            vgsediment=ob.vertex_groups.new(name="sediment")
        try:
            vgsedimentpct=ob.vertex_groups["sedimentpct"]
        except:
            vgsedimentpct=ob.vertex_groups.new(name="sedimentpct")
        try:
            vgcapacity=ob.vertex_groups["capacity"]
        except:
            vgcapacity=ob.vertex_groups.new(name="capacity")

        g = Grid.fromBlenderMesh(me, vg, self.Ef)

        me = bpy.data.meshes.new(me.name)

        self.counts['diffuse'] = 0
        self.counts['avalanche'] = 0
        self.counts['water'] = 0
        for i in range(self.Iterations):
            if self.IterRiver > 0:
                for i in range(self.IterRiver):
                    g.rivergeneration(self.Kr, self.Kv, self.userainmap, self.Kc, self.Ks, self.Kdep, self.Ka, self.Kev/100, 0,0,0,0, self.numexpr)

            if self.Kd > 0.0:
                for k in range(self.IterDiffuse):
                    g.diffuse(self.Kd / 5, self.IterDiffuse, self.numexpr)
                    self.counts['diffuse']+=1

            if self.Kt < radians(90) and self.Pa > 0:
                for k in range(self.IterAva):
                    # since dx and dy are scaled to 1, tan(Kt) is the height for a given angle
                    g.avalanche(tan(self.Kt), self.IterAva, self.Pa, self.numexpr)
                    self.counts['avalanche']+=1
            if self.Kz > 0:
                g.fluvial_erosion(self.Kr, self.Kv, self.userainmap, self.Kc, self.Ks, self.Kz*50, self.Ka, 0,0,0,0, self.numexpr)
                self.counts['water']+=1

        g.toBlenderMesh(me)
        ob.data = me

        if vg:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vg.add([i],g.rainmap[row,col],'ADD')
        if vgscree:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgscree.add([i],g.avalanced[row,col],'ADD')
        if vgavalanced:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgavalanced.add([i],-g.avalanced[row,col],'ADD')
        if vgw:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgw.add([i],g.water[row,col]/g.watermax,'ADD')
        if vgscour:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgscour.add([i],g.scour[row,col]/max(g.scourmax, -g.scourmin),'ADD')
        if vgdeposit:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgdeposit.add([i],g.scour[row,col]/min(-g.scourmax, g.scourmin),'ADD')
        if vgflowrate:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgflowrate.add([i],g.flowrate[row,col],'ADD')
        if vgsediment:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgsediment.add([i],g.sediment[row,col],'ADD')
        if vgsedimentpct:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgsedimentpct.add([i],g.sedimentpct[row,col],'ADD')
        if vgcapacity:
            for row in range(g.rainmap.shape[0]):
                for col in range(g.rainmap.shape[1]):
                    i = row * g.rainmap.shape[1] + col
                    vgcapacity.add([i],g.capacity[row,col],'ADD')
        try:
            vg = ob.vertex_groups["vgActive"]
        except:
            vg = vgcapacity
        ob.vertex_groups.active = vg

        if self.smooth:
            bpy.ops.object.shade_smooth()
        self.stats.time()
        self.stats.memory()
        if self.showmeshstats:
            self.stats.meshstats = g.analyze()

        return {'FINISHED'}


    def draw(self,context):
        layout = self.layout

        layout.operator('screen.repeat_last', text="Repeat", icon='FILE_REFRESH' )

        layout.prop(self, 'Iterations')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Thermal (Diffusion)")
        col.prop(self, 'Kd')
        col.prop(self, 'IterDiffuse')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Avalanche (Talus)")
        col.prop(self, 'Pa')
        col.prop(self, 'IterAva')
        col.prop(self, 'Kt')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="River erosion")
        col.prop(self, 'IterRiver')
        col.prop(self, 'Kz')
        col.prop(self, 'Ks')
        col.prop(self, 'Kc')
        col.prop(self, 'Kdep')
        col.prop(self, 'Kr')
        col.prop(self, 'Kv')
        col.prop(self, 'Kev')

        col.prop(self, 'Ef')

        layout.prop(self,'smooth')
