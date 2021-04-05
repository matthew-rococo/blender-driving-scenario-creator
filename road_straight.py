# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_line_plane

from math import pi

from . import helpers


class DSC_OT_road_straight(bpy.types.Operator):
    bl_idname = 'dsc.road_straight'
    bl_label = 'Straight'
    bl_description = 'Create a straight road'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def create_object_xodr(self, context, point_start, point_end):
        '''
            Create a straight road object
        '''
        if point_end == point_start:
            self.report({"WARNING"}, "Impossible to create zero length road!")
            return
        mesh = bpy.data.meshes.new('road_straight')
        obj = bpy.data.objects.new(mesh.name, mesh)
        helpers.link_object_opendrive(context, obj)

        vertices = [(0.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (4.0, 1.0, 0.0),
                    (4.0, 0.0, 0.0),
                    (-4.0, 0.0, 0.0),
                    (-4.0, 1.0, 0.0)
                    ]
        edges = [[0, 1],[1, 2],[2, 3],[3, 4],
                    [0, 4,],[4, 5],[5, 1]]
        faces = [[0, 1, 2, 3],[0, 4, 5, 1]]
        mesh.from_pydata(vertices, edges, faces)

        helpers.select_activate_object(context, obj)

        # Rotate, translate, scale to according to selected points
        self.transform_object_wrt_start(obj, point_start, heading_start=0)
        self.transform_object_wrt_end(obj, point_end)

        # Remember connecting points for road snapping
        obj['point_start'] = point_start
        obj['point_end'] = point_end

        # Set OpenDRIVE custom properties
        obj['id_opendrive'] = helpers.get_new_id_opendrive(context)
        obj['t_road_planView_geometry'] = 'line'
        obj['t_road_planView_geometry_s'] = 0
        obj['t_road_planView_geometry_x'] = point_start.x
        obj['t_road_planView_geometry_y'] = point_end.y
        vector_start_end = point_end - point_start
        obj['t_road_planView_geometry_hdg'] = vector_start_end.to_2d().angle_signed(Vector((0.0, 1.0)))
        obj['t_road_planView_geometry_length'] = vector_start_end.length

        return obj

    def create_stencil(self, context, point_start, heading_start):
        '''
            Create a stencil object with fake user or find older one in bpy data and
            relink to scene currently only support OBJECT mode.
        '''
        stencil = bpy.data.objects.get('dsc_stencil_object')
        if stencil is not None:
            if context.scene.objects.get('dsc_stencil_object') is None:
                context.scene.collection.objects.link(stencil)
        else:
            # Create object from mesh
            mesh = bpy.data.meshes.new("dsc_stencil_object")
            vertices = [(0.0, 0.0, 0.0),
                        (0.0, 0.01, 0.0),
                        (4.0, 0.01, 0.0),
                        (4.0, 0.0, 0.0),
                        (-4.0, 0.0, 0.0),
                        (-4.0, 0.01, 0.0)
                        ]
            edges = [[0, 1],[1, 2],[2, 3],[3, 4],
                     [0, 4,],[4, 5],[5, 1]]
            faces = []
            mesh.from_pydata(vertices, edges, faces)
            self.stencil = bpy.data.objects.new("dsc_stencil_object", mesh)
            self.transform_object_wrt_start(self.stencil, point_start, heading_start)
            # Link
            context.scene.collection.objects.link(self.stencil)
            self.stencil.use_fake_user = True
            self.stencil.data.use_fake_user = True

    def remove_stencil(self):
        '''
            Unlink stencil, needs to be in OBJECT mode.
        '''
        stencil = bpy.data.objects.get('dsc_stencil_object')
        if stencil is not None:
            bpy.data.objects.remove(stencil, do_unlink=True)

    def update_stencil(self, point_end, heading_fixed):
        # Transform stencil object to follow the mouse pointer
        if self.snapped_start:
            self.transform_object_wrt_end(self.stencil, point_end, heading_fixed=True)
        else:
            self.transform_object_wrt_end(self.stencil, point_end, heading_fixed=False)

    def transform_object_wrt_start(self, obj, point_start, heading_start):
        '''
            Rotate and translate origin to start point and rotate to start heading.
        '''
        obj.location = point_start
        mat_rotation = Matrix.Rotation(heading_start, 4, 'Z')
        obj.data.transform(mat_rotation)
        obj.data.update()

    def transform_object_wrt_end(self, obj, point_end, heading_fixed=False):
        '''
            Transform object according to selected end point (keep start point fixed).
        '''
        vector_selected = point_end - obj.location
        vector_object = obj.data.vertices[1].co - obj.data.vertices[0].co
        if vector_selected.length > 0 and vector_object.length > 0:
            mat_scale = Matrix.Scale(vector_selected.length/vector_object.length, 4, vector_object)
            # Apply transformation
            if heading_fixed:
                obj.data.transform(mat_scale)
            else:
                mat_rotation = vector_object.rotation_difference(vector_selected).to_matrix().to_4x4()
                obj.data.transform(mat_rotation @ mat_scale)
            obj.data.update()

    def project_point_end(self, point_start, heading_start, point_selected):
        '''
            Project selected point to road end point.
        '''
        print(point_selected)
        print('start',point_start)
        vector_selected = point_selected - point_start
        print(vector_selected)
        if vector_selected.length > 0:
            vector_object = Vector((0.0, 1.0, 0.0))
            vector_object.rotate(Matrix.Rotation(heading_start, 4, 'Z'))
            print(vector_object)
            print('r',vector_selected.project(vector_object))
            return point_start + vector_selected.project(vector_object)
        else:
            return point_start

    def modal(self, context, event):
        # Display help text
        if self.state == 'INIT':
            context.area.header_text_set("Place road by clicking, press ESCAPE, RIGHTMOUSE to exit.")
            # Set custom cursor
            bpy.context.window.cursor_modal_set('CROSSHAIR')
            # Reset road snap
            self.snapped_start = False
            self.state = 'SELECT_BEGINNING'
        if event.type in {'NONE', 'TIMER', 'TIMER_REPORT', 'EVT_TWEAK_L', 'WINDOW_DEACTIVATE'}:
            return {'PASS_THROUGH'}
        # Update on move
        if event.type == 'MOUSEMOVE':
            hit, point_selected_end, heading_end = self.raycast_mouse_to_road_else_xy(context, event)
            context.scene.cursor.location = point_selected_end
            if self.state == 'SELECT_END':
                if self.snapped_start:
                    point_end = self.project_point_end(self.point_selected_start, self.heading_start,
                        point_selected_end)
                    self.update_stencil(point_end, heading_fixed=True)
                else:
                    self.update_stencil(point_selected_end, heading_fixed=False)
        # Select start and end
        elif event.type == 'LEFTMOUSE':
            if event.value == 'RELEASE':
                if self.state == 'SELECT_BEGINNING':
                    # Find clickpoint in 3D and create stencil mesh
                    hit, self.point_selected_start, self.heading_start = \
                        self.raycast_mouse_to_road_else_xy(context, event)
                    self.snapped_start = hit
                    self.create_stencil(context, self.point_selected_start, self.heading_start)
                    # Make stencil active object
                    helpers.select_activate_object(context, self.stencil)
                    context.scene.cursor.location = self.point_selected_start
                    self.state = 'SELECT_END'
                    return {'RUNNING_MODAL'}
                if self.state == 'SELECT_END':
                    # Set cursor to endpoint
                    hit, point_selected_end, heading_end = self.raycast_mouse_to_road_else_xy(context, event)
                    # Create the final object
                    if self.snapped_start:
                        point_end = self.project_point_end(self.point_selected_start, self.heading_start,
                            point_selected_end)
                    else:
                        point_end = point_selected_end
                    self.create_object_xodr(context, self.point_selected_start, point_end)
                    # Remove stencil and go back to initial state to draw again
                    self.remove_stencil()
                    context.scene.cursor.location = point_selected_end
                    self.state = 'INIT'
                    return {'RUNNING_MODAL'}
        # Cancel
        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            # Make sure stencil is removed
            self.remove_stencil()
            # Remove header text with 'None'
            context.area.header_text_set(None)
            # Set custom cursor
            bpy.context.window.cursor_modal_restore()
            # Make sure to exit edit mode
            if bpy.context.active_object:
                if bpy.context.active_object.mode == 'EDIT':
                    bpy.ops.object.mode_set(mode='OBJECT')
            self.state = 'INIT'
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.init_loc_x = context.region.x
        self.value = event.mouse_x
        # For operator state machine
        # possible states: {'INIT','SELECTE_BEGINNING', 'SELECT_END'}
        self.state = 'INIT'

        bpy.ops.object.select_all(action='DESELECT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def mouse_to_xy_plane(self, context, event):
        '''
            Convert mouse pointer position to 3D point in xy-plane.
        '''
        region = context.region
        rv3d = context.region_data
        co2d = (event.mouse_region_x, event.mouse_region_y)
        view_vector_mouse = region_2d_to_vector_3d(region, rv3d, co2d)
        ray_origin_mouse = region_2d_to_origin_3d(region, rv3d, co2d)
        point = intersect_line_plane(ray_origin_mouse, ray_origin_mouse + view_vector_mouse,
           (0, 0, 0), (0, 0, 1), False)
        # Fix parallel plane issue
        if point is None:
            point = intersect_line_plane(ray_origin_mouse, ray_origin_mouse + view_vector_mouse,
                (0, 0, 0), view_vector_mouse, False)
        return point

    def raycast_mouse_to_road(self, context, event, obj_type):
        '''
            Convert mouse pointer position to specified hit obj.
        '''
        region = context.region
        rv3d = context.region_data
        co2d = (event.mouse_region_x, event.mouse_region_y)
        view_vector_mouse = region_2d_to_vector_3d(region, rv3d, co2d)
        ray_origin_mouse = region_2d_to_origin_3d(region, rv3d, co2d)
        hit, point, normal, index_face, obj, matrix_world = context.scene.ray_cast(
            depsgraph=context.view_layer.depsgraph,
            origin=ray_origin_mouse,
            direction=view_vector_mouse)
        # Filter object type
        if hit and obj['t_road_planView_geometry'] is obj_type:
            return hit, obj
        else:
            return hit, obj

    def raycast_mouse_to_road_else_xy(self, context, event):
        '''
            Get a snapping point from an existing road or just an xy-plane intersection
            point.
        '''
        hit, obj = self.raycast_mouse_to_road(context, event, obj_type='line')
        if not hit:
            point_raycast = self.mouse_to_xy_plane(context, event)
            return False, point_raycast, 0
        else:
            return True , Vector(obj['point_end']), obj['t_road_planView_geometry_hdg']