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


class DSC_OT_road_properties_popup(bpy.types.Operator):
    bl_idname = 'dsc.road_properties_popup'
    bl_label = ''

    operators = {'road_straight': bpy.ops.dsc.road_straight,
                 'road_arc': bpy.ops.dsc.road_arc,
                 'road_clothoid': bpy.ops.dsc.road_clothoid,
                 'road_parametric_polynomial': bpy.ops.dsc.road_parametric_polynomial,}

    operator: bpy.props.StringProperty(
        name='Road operator', description='Type of the road operator to call.', options={'HIDDEN'})
    expand_parameters: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        return {'FINISHED'}

    def cancel(self, context):
        # Popup closed, call operator for the specified road operator
        op = self.operators[self.operator]
        op('INVOKE_DEFAULT')
        return None

    def invoke(self, context, event):
        if len(context.scene.road_properties.strips) == 0:
            context.scene.road_properties.init()
        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        box = self.layout.box()
        row = box.row(align=True)
        box_info = row.box()
        box_info.label(text='Note: Lines are centered between lanes and do not ')
        box_info.label(text='contribute to overall road width or number of lanes.')
        row = box.row(align=True)

        row.label(text='Cross section preset:')
        row.prop(context.scene.road_properties, 'cross_section_preset', text='')
        row = box.row(align=True)

        box_params = row.box()
        if self.expand_parameters == False:
            box_params.prop(self, 'expand_parameters', icon="TRIA_RIGHT", text="Parameters", emboss=False)
        else:
            # Expand
            box_params.prop(self, 'expand_parameters', icon="TRIA_DOWN", text="Parameters", emboss=False)
            row = box_params.row(align=True)
            row.label(text='Width line standard:')
            row.prop(context.scene.road_properties, 'width_line_standard', text='')
            row = box_params.row(align=True)
            row.label(text='Width line bold:')
            row.prop(context.scene.road_properties, 'width_line_bold', text='')
            row = box_params.row(align=True)
            # row.label(text='Length line broken:')
            # row.prop(context.scene.road_properties, 'length_broken_line', text='')
            # row = box_params.row(align=True)
            # row.label(text='Ratio broken line gap:')
            # row.prop(context.scene.road_properties, 'ratio_broken_line_gap', text='')
            row = box_params.row(align=True)

            row = box_params.row(align=True)
            row.label(text='Width driving:')
            row.prop(context.scene.road_properties, 'width_driving', text='')
            row = box_params.row(align=True)
            row.label(text='Width border:')
            row.prop(context.scene.road_properties, 'width_border', text='')
            # row = box_params.row(align=True)
            # row.label(text='Width curb:')
            # row.prop(context.scene.road_properties, 'width_curb', text='')
            row = box_params.row(align=True)
            row.label(text='Width median:')
            row.prop(context.scene.road_properties, 'width_median', text='')
            row = box_params.row(align=True)
            row.label(text='Width stop:')
            row.prop(context.scene.road_properties, 'width_stop', text='')
            row = box_params.row(align=True)
            row.label(text='Width shoulder:')
            row.prop(context.scene.road_properties, 'width_shoulder', text='')
            row = box_params.row(align=True)
            row.label(text='Width none (offroad lane):')
            row.prop(context.scene.road_properties, 'width_none', text='')
            row = box_params.row(align=True)

            row = box_params.row(align=True)
            row.label(text='Design speed:')
            row.prop(context.scene.road_properties, 'design_speed', text='')

        row = box.row(align=True)
        row.label(text='Number of lanes:')
        row = box.row(align=True)
        row.label(text='Left:')
        row.prop(context.scene.road_properties, 'num_lanes_left', text='')
        row.separator()
        row.label(text='Right:')
        row.prop(context.scene.road_properties, 'num_lanes_right', text='')

        row = box.row(align=True)

        for idx, strip in enumerate(context.scene.road_properties.strips):
            row = box.row(align=True)
            split = row.split(factor=0.2, align=True)
            split.label(text='Strip ' + str(idx+1) + ':')
            split = split.split(factor=0.3, align=True)
            split.prop(strip, 'type', text='')
            if context.scene.road_properties.strips[idx].type == 'line':
                split.prop(strip, 'road_mark_type', text='')
                split.prop(strip, 'road_mark_weight', text='')
                split.prop(strip, 'road_mark_color', text='')
            else:
                split.label(text='Width:')
                split.prop(strip, 'width', text='')
