bl_info = {
    "name": "SwiftBlock",
    "author": "Karl-Johan Nogenmyr, Mikko Folkersma, Turo Valikangas",
    "version": (0, 2),
    "blender": (2, 7, 7),
    "location": "View_3D > Object > SwiftBlock",
    "description": "Writes block geometry as blockMeshDict file",
    "warning": "",
    "wiki_url": "http://openfoamwiki.net/index.php/SwiftBlock",
    "tracker_url": "",
    "category": "OpenFOAM"}

import bpy
import bmesh
import importlib
from . import blockBuilder
importlib.reload(blockBuilder)
from . import blender_utils
importlib.reload(blender_utils)
from . import utils
importlib.reload(utils)
from mathutils import Vector


#blocking object name
bpy.types.Object.isblockingObject = bpy.props.BoolProperty(default=False)
bpy.types.Object.blocking_object = bpy.props.StringProperty(default="")
bpy.types.Object.preview_object = bpy.props.StringProperty(default="")
bpy.types.Object.ispreviewObject = bpy.props.BoolProperty(default=False)
bpy.types.Object.direction_object = bpy.props.StringProperty(default="")
bpy.types.Object.isdirectionObject = bpy.props.BoolProperty(default=False)


# Initialize all the bmesh layer properties for the blocking object
class InitBlockingObject(bpy.types.Operator):
    bl_idname = "init.blocking"
    bl_label = "Init blocking"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='EDIT')
        print("initialize")
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        bm.edges.layers.string.new("type")
        bm.edges.layers.float.new("x1")
        bm.edges.layers.float.new("x2")
        bm.edges.layers.float.new("r1")
        bm.edges.layers.float.new("r2")
        bm.edges.layers.float.new("dx")
        bm.edges.layers.int.new("cells")
        bm.edges.layers.int.new("groupid")
        bm.edges.layers.string.new("snapId")
        bm.edges.layers.float.new("time")
        bm.edges.layers.int.new("deactivated")
        bm.faces.layers.int.new("snapId")
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        ob.isblockingObject = True
        # context.scene.blocking_object = ob.name
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.set.patchname('INVOKE_DEFAULT')
        bpy.ops.mesh.select_all(action="DESELECT")
        ob.show_all_edges = True
        ob.show_wire = True
        return {"FINISHED"}


class ActivateSnap(bpy.types.Operator):
    bl_idname = "activate.snapping"
    bl_label = "Activate snapping object"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        scn = context.scene
        ob = context.active_object
        pob = bpy.data.objects[ob.SnapObject]
        pob.blocking_object = ob.name
        blender_utils.activateObject(pob, False)
        return {'FINISHED'}

class ActivateBlocking(bpy.types.Operator):
    bl_idname = "activate.blocking"
    bl_label = "Activate blocking"
    bl_options = {"UNDO"}

    hide = bpy.props.BoolProperty()

    def invoke(self, context, event):
        scn = context.scene
        ob = context.active_object
        bob = bpy.data.objects[ob.blocking_object]
        blender_utils.activateObject(bob, self.hide)
        return {'FINISHED'}

# Get all objects in current context
def getObjects(self, context):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not ob.isblockingObject and not ob.ispreviewObject and not ob.isdirectionObject:
            obs.append((ob.name, ob.name, ''))
    return obs

# SwiftBlock properties
class BlockProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    name = bpy.props.StringProperty()
    verts = bpy.props.IntVectorProperty(size = 8)
    enabled = bpy.props.BoolProperty(default=True)
    namedRegion = bpy.props.BoolProperty(default=False)
bpy.utils.register_class(BlockProperty)

# List of block edges (int edgeGroup, int v1, int v2)
class BlockEdgesProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    v1 = bpy.props.IntProperty()
    v2 = bpy.props.IntProperty()
    enabled = bpy.props.BoolProperty(default=True)
# TODO    snapline = bpy.props.IntProperty()
bpy.utils.register_class(BlockEdgesProperty)

class BlockFacesProperty(bpy.types.PropertyGroup):
    id = bpy.props.IntProperty()
    verts = bpy.props.IntVectorProperty(size = 4)
    pos = bpy.props.IntProperty()
    neg = bpy.props.IntProperty()
    enabled = bpy.props.BoolProperty(default=True)
bpy.utils.register_class(BlockFacesProperty)

class EdgeGroupProperty(bpy.types.PropertyGroup):
    group_name = bpy.props.StringProperty()
    group_edges = bpy.props.StringProperty()
bpy.utils.register_class(EdgeGroupProperty)

def initSwiftBlockProperties():
    bpy.types.Object.SnapObject = bpy.props.EnumProperty(name="Object", 
            items=getObjects, description = "The object which has the geometry curves")
    bpy.types.Object.Autosnap = bpy.props.BoolProperty(name="Enable",
            description = "Snap lines automatically from geometry?")
    bpy.types.Object.MappingType = bpy.props.EnumProperty(name="",
            items = (("Geometric1","Geometric1","",1),
                     ("Geometric2","Geometric2","",2),))
    bpy.types.Object.Dx = bpy.props.FloatProperty(name="dx", default=1, update=setCellSize, min=0)
    bpy.types.Object.Cells = bpy.props.IntProperty(name="Cells", default=10,  min=1)
    bpy.types.Object.x1 = bpy.props.FloatProperty(name="x1", default=0, description="First cell size", min=0)
    bpy.types.Object.x2 = bpy.props.FloatProperty(name="x2", default=0, description="Last cell size",  min=0)
    bpy.types.Object.r1 = bpy.props.FloatProperty(name="r1", default=1.2, description="First boundary layer geometric ratio", min=1.0)
    bpy.types.Object.r2 = bpy.props.FloatProperty(name="r2", default=1.2, description="Last boundary layer geometric ratio", min=1.0)
    # bpy.types.Object.ShowEdgeDirections = bpy.props.BoolProperty(name="Show directions", default=True, update = updateDirections, description="Show edge directions?")
    bpy.types.Object.EdgeGroupName = bpy.props.StringProperty(
        name = "Name",default="group name",
        description = "Specify name of edge group")
    bpy.types.Object.bcTypeEnum = bpy.props.EnumProperty(
        items = [('wall', 'wall', 'Defines the patch as wall'),
                 ('patch', 'patch', 'Defines the patch as generic patch'),
                 ('empty', 'empty', 'Defines the patch as empty'),
                 ('symmetry', 'symmetry', 'Defines the patch as symmetry'),
                 ],
        name = "Patch type")
    bpy.types.Object.patchName = bpy.props.StringProperty(
        name = "Patch name",
        description = "Specify name of patch",
        default = "defaultName")

    bpy.types.Object.blocks = \
        bpy.props.CollectionProperty(type=BlockProperty)

    bpy.types.Object.block_edges = \
        bpy.props.CollectionProperty(type=BlockEdgesProperty)


    bpy.types.Object.block_faces = \
        bpy.props.CollectionProperty(type=BlockFacesProperty)


    bpy.types.Object.edge_groups = \
        bpy.props.CollectionProperty(type=EdgeGroupProperty)

class block_items(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.9)
        block = context.active_object.blocks[index]
        name = block.name + ' %d'%index
        c = split.operator("edit.block", name, emboss=False)
        c.blockid = index
        c.name = block.name
        # split.label("%d" % (index))
        # split.prop(item, "name", text="", emboss=False, translate=False)#, icon='BORDER_RECT')

        if block.enabled:
            c = split.operator('enable.block', '',emboss=False,icon="CHECKBOX_HLT").blockid = index
        else:
            c = split.operator('enable.block','', emboss=False,icon="CHECKBOX_DEHLT").blockid = index
        # split.prop(item, "enabled", text="")

    def invoke(self, context, event):
        pass   

# bpy.types.Scene.custom = bpy.types.CollectionProperty(type=CustomProp)
bpy.types.Scene.block_index = bpy.props.IntProperty()

# Create the swiftBlock panel
class SwiftBlockPanel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "SwiftBlock"
    bl_label = "SwiftBlock"
    # bl_context = "OBJECT"

    def draw(self, context):
        scn = context.scene
        ob = context.active_object
        if not ob:
            return

        box = self.layout.column(align=True)

        if ob.ispreviewObject:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = True
        # elif scn.blocking_object in bpy.data.objects and ob.name != scn.blocking_object:
        elif ob.blocking_object and ob.name != ob.blocking_object:
            box = self.layout.box()
            box.operator("activate.blocking", text="Activate blocking").hide = False
        elif not ob.isblockingObject:
            box.operator("init.blocking", text="Initialize blocking")

        elif context.active_object and bpy.context.active_object.mode == "EDIT":

            box = self.layout.box()
            box.operator("build.blocking", text="Build Blocking")

            split = box.split()
            split.operator("preview.mesh", text="Preview mesh")
            split = split.split()
            split.operator("write.mesh", text="Write mesh")


            box = self.layout.box()
            box.label("Automatic snapping")
            if ob.Autosnap:
                split = box.split(percentage=0.2)
                col = split.column()
                col.prop(ob, "Autosnap")
                col = split.column()
                col.prop(ob, "SnapObject",'')
                if ob.SnapObject != "":
                    box.operator("activate.snapping", text="Activate")
            else:
                box.prop(ob, "Autosnap")

            # box.label("Snapping")
            # split = box.split()
            # split.operator("snap.edge", text="Edge to line")
            # split = split.split()
            # split.operator("snap.face", text="Face to surface")

            box = self.layout.box()
            # split = box.split()
            box.label("Line Mapping")
            # box.prop(scn, "MappingType")
            # if scn.MappingType == "Geometric1":
                # box.prop(scn, "Nodes")
            # elif scn.MappingType == "Geometric2":
                # box.prop(scn, "Dx")
            split = box.split()
            col = split.column()
            col.prop(ob, "Cells")
            col.label("Start")
            col.prop(ob, "x1")
            col.prop(ob, "r1")
            col.operator("set.edgemapping")
            col = split.column()
            col.label('')
            # col.prop(ob, "Dx")
            col.label("End")
            col.prop(ob, "x2")
            col.prop(ob, "r2")
            col.operator("get.edge")
            box.operator("select.aligned")
            split = box.split()
            # split.operator("edge.mapping", text="Set edge")
            # split = split.split()
            box = self.layout.box()
            box.label('Boundary conditions')
            box.prop(ob, 'patchName')
            box.prop(ob, 'bcTypeEnum')
            box.operator("set.patchname")
            for m in ob.data.materials:
                try:
                    patchtype = str(' ' + m['patchtype'])
                    split = box.split(percentage=0.2, align=True)
                    col = split.column()
                    col.prop(m, "diffuse_color", text="")
                    col = split.column()
                    col.operator("set.getpatch", text=m.name + patchtype, emboss=False).whichPatch = m.name
                except:
                    pass
            box = self.layout.box()
            box.label("Edges")
            if 'Edge_directions' in bpy.data.objects:
                box.operator("draw.directions",'Show edge directions',emboss=False,icon="CHECKBOX_HLT").show=False
            else:
                box.operator("draw.directions",'Show edge directions',emboss=False,icon="CHECKBOX_DEHLT").show=True
            box.operator("flip.edge")
            box.label("Add Edge groups")
            split = box.split(percentage=0.9)
            split.prop(ob, 'EdgeGroupName','')
            split.operator("set.edgegroup",'',icon='PLUS',emboss = False)
            for eg in ob.edge_groups:
                split = box.split(percentage=0.8, align=True)
                col = split.column()
                col.operator("get.edgegroup", eg.group_name , emboss=False).egName = eg.group_name
                col = split.column()
                col.operator('del.edgegroup', '',emboss=False,icon='X').egName = eg.group_name
            box = self.layout.box()
            box.label("Blocks")
            box.template_list("block_items", "", ob, "blocks", scn, "block_index", rows=2)
            box.operator("get.block")
            # split = box.split(percentage=0.5, align=True)
            # col = split.column()
            # col.label("Name")
            # col = split.column()
            # col.label("Id")
            # col = split.column()

            # for i,bv in enumerate(ob.blocks):
                # split = box.split(percentage=0.5, align=True)
                # col = split.column()
                # c = col.operator("edit.block", ob.blocks[i].name, emboss=False)
                # c.blockid = i
                # c.name = ob.blocks[i].name

                # col = split.column()
                # col.label(str(i))
                # col = split.column()
                # if bv.enabled:
                    # c = col.operator('enable.block', 'enabled').blockid = i
                # else:
                    # c = col.operator('enable.block', 'disabled').blockid = i


class EdgeSelectAligned(bpy.types.Operator):
    bl_idname = "select.aligned"
    bl_label = "Select aligned edges"

    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        for e in bm.edges:
            if e.select:
                groupid = e[groupl]
                for i in bm.edges:
                    if i[groupl] == groupid:
                        i.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class FlipEdge(bpy.types.Operator):
    "Flips aligned edges, select only one edge per group"
    bl_idname = "flip.edge"
    bl_label = "Flip edges"

    def execute(self, context):
        ob = context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')
        flip_edges = []
        for e in bm.edges:
            if e.select:
                groupid = e[groupl]
                for i in bm.edges:
                    if i[groupl] == groupid:
                        flip_edges.append(i.index)
                break
        bpy.ops.object.mode_set(mode='OBJECT')
        for fe in flip_edges:
            e = ob.data.edges[fe]
            (e0,e1) = e.vertices
            e.vertices = (e1,e0)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.draw.directions('INVOKE_DEFAULT')
        return {'FINISHED'}

class GetBlock(bpy.types.Operator):
    "Get block from selection"
    bl_idname = "get.block"
    bl_label = "Get block"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        ob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(ob.data)
        selection = []
        for v in bm.verts:
            if v.select:
                selection.append(v.index)
        block = False
        occs = []
        for b in ob.blocks:
            occ = [v in selection for v in b.verts].count(True)
            if occ == 8:
                block = b
                break
            else:
                occs.append(occ)
        if not block:
            max_occ = max(enumerate(occs), key=lambda x:x[1])[0]
            block = ob.blocks[max_occ]
        if not block:
            self.report({'INFO'}, "No block found with selected vertices")
            return {'CANCELLED'}
        bpy.ops.edit.block('INVOKE_DEFAULT', blockid=block.id, name = block.name )
        return {'FINISHED'}

class EditBlock(bpy.types.Operator):
    bl_idname = "edit.block"
    bl_label = "Edit block"
    bl_options = {'REGISTER', 'UNDO'}


    blockid = bpy.props.IntProperty(name='id')
    # enabled = bpy.props.BoolProperty(name='enabled', default = True)
    namedRegion = bpy.props.BoolProperty(name='Named region', default = False)
    name = bpy.props.StringProperty(name='name')

    def draw(self, context):
        ob = context.active_object
        if not ob.blocks[self.blockid].enabled:
            return
        col = self.layout.column(align = True)
        # col.prop(self, "enabled")
        # split = col.split(percentage=0.1, align=True)
        # col = split.column()
        col.prop(self, "namedRegion")
        if self.namedRegion:
            # col = split.column()
            col.prop(self, "name")

# this could be used to select multiple blocks
    def invoke(self, context, event):
        context.scene.block_index = self.blockid
        if event.shift:
            self.shiftDown = True
        else:
            self.shiftDown = False
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        bpy.ops.mesh.select_all(action="DESELECT")
        scn = context.scene
        ob = context.active_object
        ob.blocks[self.blockid].name = self.name
        ob.blocks[self.blockid].namedRegion = self.namedRegion
        ob = context.active_object

        verts = ob.blocks[self.blockid].verts

        bm = bmesh.from_edit_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        for v in verts:
            bm.verts[v].select = True
        for e in bm.edges:
            if e.verts[0].select and e.verts[1].select:
                e.select = True
        for f in bm.faces:
            if len(f.verts) == 4 and sum([v.select for v in f.verts]) == 4:
                f.select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class EnableBlock(bpy.types.Operator):
    bl_idname = "enable.block"
    bl_label = "Enable/disable block"

    blockid = bpy.props.IntProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        block = ob.blocks[self.blockid]
        context.scene.block_index = self.blockid

        if block.enabled:
            block.enabled = False
        else:
            block.enabled = True
        repair_blockFacesEdges(ob)

        return {'FINISHED'}


class DelEdgeGroup(bpy.types.Operator):
    bl_idname = "del.edgegroup"
    bl_label = "Get edge group"

    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        for i,eg in enumerate(ob.edge_groups):
            if eg.group_name == self.egName:
                ob.edge_groups.remove(i)
                return {'FINISHED'}
        return {'CANCEL'}

class GetEdgeGroup(bpy.types.Operator):
    bl_idname = "get.edgegroup"
    bl_label = "Get edge group"

    egName = bpy.props.StringProperty()

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.mesh.select_all(action="DESELECT")

        bm = bmesh.from_edit_mesh(ob.data)
        for eg in ob.edge_groups:
            if eg.group_name == self.egName:
                edges = list(map(int,eg.group_edges.split(',')))
                for e in edges:
                    bm.edges[e].select = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class SetEdgeGroup(bpy.types.Operator):
    '''Set the given name to the selected edges'''
    bl_idname = "set.edgegroup"
    bl_label = "Set edge group"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        edges = []
        for e in ob.data.edges:
            if e.select:
                edges.append(e.index)
        edgesstr = ','.join(map(str,edges))
        for e in ob.edge_groups:
            if e.group_name == ob.EdgeGroupName:
                e.group_edges = edgesstr
                return {'FINISHED'}
        eg = ob.edge_groups.add()
        eg.group_name = ob.EdgeGroupName
        eg.group_edges = edgesstr
        return {'FINISHED'}

def patchColor(patch_no):
    color = [(0.25,0.25,0.25), (1.0,0.,0.), (0.0,1.,0.),(0.0,0.,1.),(0.707,0.707,0),(0,0.707,0.707),(0.707,0,0.707)]
    return color[patch_no % len(color)]

class OBJECT_OT_SetPatchName(bpy.types.Operator):
    '''Set the given name to the selected faces'''
    bl_idname = "set.patchname"
    bl_label = "Set name"

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        NoSelected = 0
        for f in ob.data.polygons:
            if f.select:
                NoSelected += 1
        if NoSelected:
            namestr = ob.patchName
            namestr = namestr.strip()
            namestr = namestr.replace(' ', '_')
            try:
                mat = bpy.data.materials[namestr]
                patchindex = list(ob.data.materials).index(mat)
                ob.active_material_index = patchindex
            except: # add a new patchname (as a blender material, as such face props are conserved during mesh mods)
                mat = bpy.data.materials.new(namestr)
                mat.diffuse_color = patchColor(len(ob.data.materials))
                bpy.ops.object.material_slot_add()
                ob.material_slots[-1].material = mat
            mat['patchtype'] = ob.bcTypeEnum
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.material_slot_assign()
        else:
            self.report({'INFO'}, "No faces selected!")
            return{'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_GetPatch(bpy.types.Operator):
    '''Click to select faces belonging to this patch'''
    bl_idname = "set.getpatch"
    bl_label = "Get patch"

    whichPatch = bpy.props.StringProperty()
    shiftDown = False

    def invoke(self, context, event):
        if event.shift:
            self.shiftDown = True
        else:
            self.shiftDown = False
        self.execute(context)
        return {'FINISHED'}

    def execute(self, context):
        scn = context.scene
        ob = context.active_object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,False,True)")
        if not self.shiftDown:
            bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mat = bpy.data.materials[self.whichPatch]
        patchindex = list(ob.data.materials).index(mat)
        ob.active_material_index = patchindex
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_select()
        ob.bcTypeEnum = mat['patchtype']
        ob.patchName = self.whichPatch
        return {'FINISHED'}


# Change the layer properties of currently selected edges
class SetEdge(bpy.types.Operator):
    "Set mapping for the edge"
    bl_idname = "set.edgemapping"
    bl_label = "Set edge"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        cellsl = bm.edges.layers.int.get('cells')

        for e in bm.edges:
            if e.select:
                # if ob.CopyAligned:
                    # groupid = e[groupl]
                    # for i in bm.edges:
                        # if i[groupl] == groupid:
                            # i.select = True
                e[typel] = str.encode(ob.MappingType)
                e[cellsl] = ob.Cells
                e[x1l] = ob.x1
                e[x2l] = ob.x2
                e[r1l] = ob.r1
                e[r2l] = ob.r2
        return {'FINISHED'}

class SetEdge(bpy.types.Operator):
    bl_idname = "get.edge"
    bl_label = "Get edge"
    bl_options = {"UNDO"}

    def execute(self, context):
        ob = context.active_object
        scn = context.scene
        if not ob.blocks:
            bpy.ops.build.blocking('INVOKE_DEFAULT')

        bm = bmesh.from_edit_mesh(ob.data)
        typel = bm.edges.layers.string.get('type')
        x1l = bm.edges.layers.float.get('x1')
        x2l = bm.edges.layers.float.get('x2')
        r1l = bm.edges.layers.float.get('r1')
        r2l = bm.edges.layers.float.get('r2')
        cellsl = bm.edges.layers.int.get('cells')

        for e in bm.edges:
            if e.select:
                # e[typel] = str.encode(ob.MappingType)
                 ob.Cells = e[cellsl]
                 ob.x1 = e[x1l]
                 ob.x2 = e[x2l]
                 ob.r1 = e[r1l]
                 ob.r2 = e[r2l]
        return {'FINISHED'}

def setCellSize(self, context):
    ob = context.active_object
    scn = context.scene

    bm = bmesh.from_edit_mesh(ob.data)
    typel = bm.edges.layers.string.get('type')
    x1l = bm.edges.layers.float.get('x1')
    x2l = bm.edges.layers.float.get('x2')
    r1l = bm.edges.layers.float.get('r1')
    r2l = bm.edges.layers.float.get('r2')
    cellsl = bm.edges.layers.int.get('cells')

    for e in bm.edges:
        if e.select:
            e[typel] = str.encode(ob.MappingType)
            L = (e.verts[0].co-e.verts[1].co).length
            N=utils.getNodes(ob.x1,ob.x2,ob.r1,ob.r2,L,ob.Dx)
            e[cellsl] = N
            e[x1l] = ob.x1
            e[x2l] = ob.x2
            e[r1l] = ob.r1
            e[r2l] = ob.r2

# Explicitly define which line to snap for a edge
# Not fully functional
class SnapToEdge(bpy.types.Operator):
    bl_idname = "snap.edge"
    bl_label = "Snap edge to line"
    bl_options = {"UNDO"}

    def modal(self, context, event):
        # assign to vertex group
        if event.type in {'RET', 'RIGHTMOUSE'}:
            edges_selected = False
            for e in self.gob.data.edges:
                if e.select:
                    edges_selected = True
                    break
            if edges_selected:
                bpy.ops.object.vertex_group_add()
                bpy.ops.object.vertex_group_assign()
                vgname = self.gob.vertex_groups.active.name
                # Convert to 64 bit because otherwise "TypeError: expected an int, not a int"
                # vgid = uuid.uuid1().int >> 64 
            else:
                vgname = ""
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.objects.active = self.bob
            bpy.ops.object.mode_set(mode='EDIT')

            bm = bmesh.from_edit_mesh(self.bob.data)
            snapl = bm.edges.layers.string.get('snapId')

            for e in bm.edges:
                if e.select:
                    e[snapl] = vgname.encode()
                    edges_selected = True
            return {"FINISHED"}

        elif event.type in {'ESC'}:
            # self.bob.hide = False
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.objects.active = self.bob
            bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # self.bob = bpy.data.objects[context.scene.BlockingObject]
        self.bob = context.active_object
        self.gob = bpy.data.objects[context.scene.SnapObject]
        # self.bob.hide = True
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.objects.active = self.gob
        bpy.ops.object.mode_set(mode='EDIT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

# Explicitly define which surface to snap for a face
# Not implemented
class SnapToSurface(bpy.types.Operator):
    bl_idname = "snap.face"
    bl_label = "Snap face to surface"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        return {"FINISHED"}

# Automatically find blocking for the object and preview it.
class BuildBlocking(bpy.types.Operator):
    bl_idname = "build.blocking"
    bl_label = "Build blocks"
    bl_options = {"UNDO"}

    def invoke(self, context, event):
        # get verts and edges
        ob = context.active_object
        mesh = ob.data
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        verts = []
        edges = []

        edgeDict = dict()
        for v in mesh.vertices:
            verts.append(v.co)
        for e in mesh.edges:
            edges.append([e.vertices[0],e.vertices[1]])
            edgeDict[(e.vertices[0],e.vertices[1])] = e.index
        disabled = []
        # for b in ob.blocks:
            # if not b.enabled:
                # disabled.extend(b.block_verts)
        # find blocking
        log, block_verts, block_edges, face_info, all_edges, faces_as_list_of_nodes = blockBuilder.blockFinder(edges,verts,disabled = disabled)

        ob.blocks.clear()
        for i,bv in enumerate(block_verts):
            b = ob.blocks.add()
            b.id = i
            b.name = 'block'#_{}'.format(i)
            b.verts = bv

        # bm = bmesh.new()
        bm = bmesh.from_edit_mesh(ob.data)
        # bm.from_mesh(ob.data)
        groupl = bm.edges.layers.int.get('groupid')

        ob.block_edges.clear()
        for i, g in enumerate(block_edges):
            for e in g:
                bm.edges.ensure_lookup_table()
                de = ob.block_edges.add()
                de.id = i
                de.v1 = e[0]
                de.v2 = e[1]
                if (e[0],e[1]) in edgeDict:
                    be = bm.edges[edgeDict[(e[0],e[1])]]
                else:
                    be = bm.edges[edgeDict[(e[1],e[0])]]
                be[groupl] = i
        faces = []
        for f in bm.faces:
            faces.append([v.index for v in f.verts])

        
# A bug in face_info when there are o-grids. The block indices after o-grid block have to be decreased by one.
        replace_ids = dict()
        block_ids = []
        for key in face_info.keys():
            block_ids.extend(face_info[key]['pos'])
            block_ids.extend(face_info[key]['neg'])
        block_ids = sorted(set(block_ids))
        nblocks = len(ob.blocks)-1

        decrease = []
        if nblocks < max(block_ids):
            for i in range(max(block_ids)):
                if i not in block_ids:
                    decrease.append(i)

        ob.block_faces.clear()
        for fid, fn in enumerate(faces_as_list_of_nodes):
            f = ob.block_faces.add()
            f.id = utils.findFace(faces,fn)[0]
            f.enabled = True
            f.verts = fn
            if face_info[fid]['pos']:
                f.pos = face_info[fid]['pos'][0]
                dec = sum(x < f.pos for x in decrease)
                f.pos -= dec
            else:
                f.pos = -1
            if face_info[fid]['neg']:
                f.neg = face_info[fid]['neg'][0]
                dec = sum(x < f.neg for x in decrease)
                f.neg -= dec
            else:
                f.neg = -1

        bpy.ops.object.mode_set(mode='OBJECT')

        edgeDirections = utils.getEdgeDirections(block_verts, block_edges)

        ob = bpy.context.active_object
        me = ob.data
        edgelist = dict()
        for e in me.edges:
            edgelist[(e.vertices[0],e.vertices[1])] = e.index
        for ed in edgeDirections:
            # consistentEdgeDirs(ed)
            for e in ed:
                if (e[0],e[1]) not in edgelist:
                    ei = me.edges[edgelist[(e[1],e[0])]]
                    (e0, e1) = ei.vertices
                    ei.vertices = (e1, e0)
        bpy.ops.object.mode_set(mode='EDIT')

        repair_blockFacesEdges(ob)
        bpy.ops.draw.directions('INVOKE_DEFAULT')
        self.report({'INFO'}, "Number of blocks: {}".format(len(block_verts)))
		# blender_utils.draw_edge_direction()
        return {"FINISHED"}


# Build the mesh from already existing blocking
def writeMesh(ob, filename = ''):
    verts = list(blender_utils.vertices_from_mesh(ob))
    # edges = list(blender_utils.edges_from_mesh(ob))
    bm = bmesh.from_edit_mesh(ob.data)
    edges = []

    # do not write polyline for hidden edges
    for e in bm.edges:
        if not e.hide:
            edges.append((e.verts[0].index, e.verts[1].index))

    bpy.ops.object.mode_set(mode='OBJECT')

    ob.select = False
    if ob.Autosnap and ob.SnapObject:
        polyLines, polyLinesPoints, lengths = getPolyLines(verts, edges, ob)
    else:
        polyLines = []
        lengths = [[]]
    verts = []
    matrix = ob.matrix_world.copy()
    for v in ob.data.vertices:
        verts.append(matrix*v.co)

    if not ob.blocks:
        bpy.ops.build.blocking('INVOKE_DEFAULT')
    blocks = []
    block_names = []
    for b in ob.blocks:
        if b.enabled:
            blocks.append(list(b.verts))
            if b.namedRegion:
                block_names.append(b.name)
            else:
                block_names.append('')

    edgeInfo = collectEdges(ob,lengths)
    detemp = []
    ngroups = 0
    for de in ob.block_edges:
        detemp.append((de.id,de.v1,de.v2))
        ngroups = max(ngroups,int(de.id))

    block_edges = [[] for i in range(ngroups+1)]
    for e in detemp:
        block_edges[e[0]].append([e[1],e[2]])

    block_faces = []
    for f in ob.block_faces:
        if f.enabled:
            block_faces.append(list(f.verts))

    selected_edges = [e.select for e in ob.data.edges]

    patchnames = list()
    patchtypes = list()
    patchverts = list()
    patches = list()
    bpy.ops.object.mode_set(mode='EDIT')
    for mid, m in enumerate(ob.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        ob.active_material_index = mid
        bpy.ops.object.material_slot_select()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        faces = ob.data.polygons
        for f in faces:
            if f.select and f.material_index == mid:
                if m.name in patchnames:
                    ind = patchnames.index(m.name)
                    patchverts[ind].append(list(f.vertices))
                else:
                    patchnames.append(m.name)
                    patchtypes.append(m['patchtype'])
                    patchverts.append([list(f.vertices)])

    for ind,pt in enumerate(patchtypes):
        patches.append([pt])
        patches[ind].append(patchnames[ind])
        patches[ind].append(patchverts[ind])

# return edge selection
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for e,sel in zip(ob.data.edges,selected_edges):
        e.select = sel

### This is everything that is related to blockMesh so a new multiblock mesher could be introduced easily just by creating new preview file ###
    from . import preview
    importlib.reload(preview)
    if filename:
        mesh = preview.PreviewMesh(filename)
    else:
        mesh = preview.PreviewMesh()
    cells = mesh.writeBlockMeshDict(verts, 1, patches, polyLines, edgeInfo, block_names, blocks, block_edges, block_faces)
    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(False,True,False)")
###############################################################
    return mesh, cells

class WriteMesh(bpy.types.Operator):
    bl_idname = "write.mesh"
    bl_label = "Write Mesh"

    filepath = bpy.props.StringProperty(
            name="File Path",
            description="Filepath used for exporting the file",
            maxlen=1024,
            subtype='FILE_PATH',
            default='/opt',
            )
    check_existing = bpy.props.BoolProperty(
            name="Check Existing",
            description="Check and warn on overwriting existing files",
            default=True,
            options={'HIDDEN'},
            )


    def invoke(self, context, event):
        bpy.context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        ob = context.active_object
        mesh, cells = writeMesh(ob, self.filepath)
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}

class PreviewMesh(bpy.types.Operator):
    bl_idname = "preview.mesh"
    bl_label = "Preview mesh"
    bl_options = {"UNDO"}

    filename = bpy.props.StringProperty(default='')

    def invoke(self, context, event):
        ob = context.active_object
        mesh, cells = writeMesh(ob)
        points, faces = mesh.runMesh()
        blender_utils.previewMesh(ob, points, faces)
        self.report({'INFO'}, "Cells in mesh: " + str(cells))
        return {"FINISHED"}


class DrawEdgeDirections(bpy.types.Operator):
    "Draw edge directions"
    bl_idname = "draw.directions"
    bl_label = "draw edge directions"
    bl_options = {'REGISTER', 'UNDO'}

    show = bpy.props.BoolProperty(default=True)
    size = bpy.props.FloatProperty(default=0,min=0)
    verts = bpy.props.IntProperty(default=12,min=0)
    relativeSize = bpy.props.BoolProperty(default=True)

    def invoke(self, context, event):
        self.bob = bpy.context.active_object
        bm = bmesh.from_edit_mesh(self.bob.data)
        self.edges = []
        for e in bm.edges:
            if not e.hide:
                self.edges.append((Vector(e.verts[0].co[:]),Vector(e.verts[1].co[:])))
        self.lengths = [(e[0]-e[1]).length for e in self.edges]
        self.size = 0.2
        self.execute(context)
        return {"FINISHED"}


    def execute(self,context):
        try:
            eob = bpy.data.objects['Edge_directions']
            self.remove(context,eob)
        except:
            pass
        if not self.edges or not self.show:
            self.bob.direction_object = ''
            return {"CANCELLED"}
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.mesh.primitive_cone_add(vertices=self.verts,radius1=0.3,depth=1)#,end_fill_type='NOTHING')
        default_arrow = context.active_object
        arrows = []
        # this is "a bit" slow
        for e,l in zip(self.edges,self.lengths):
            v1 = Vector(e[0])
            v2 = Vector(e[1])
            tob = bpy.data.objects.new("Arrow_duplicate", default_arrow.data)
            tob.location = v1+0.5*(v2-v1)
            if self.relativeSize:
                scale = self.size*l
            else:
                scale = self.size
            tob.scale = (scale,scale,scale)
            tob.rotation_mode = 'QUATERNION'
            tob.rotation_quaternion = (v1-v2).to_track_quat('Z','Y')
            context.scene.objects.link(tob)
            arrows.append(tob)
            tob.select = True
        aob = arrows[0]
        bpy.context.scene.objects.active = aob
        aob.name = 'Edge_directions'
        aob.hide_select = True

        mat = bpy.data.materials.new('black')
        mat.emit = 2
        mat.diffuse_color = (0,0,0)
        bpy.ops.object.material_slot_add()
        aob.material_slots[-1].material = mat
        self.remove(context, default_arrow)
        aob.isdirectionObject = True

        bpy.ops.object.join()
        bpy.ops.object.shade_smooth()
        blender_utils.activateObject(self.bob)
        self.bob.direction_object = aob.name
        return {"FINISHED"}

    def remove(self, context, ob):
        context.scene.objects.unlink(ob)
        bpy.data.objects.remove(ob)

def repair_blockFacesEdges(ob):
    bm = bmesh.from_edit_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    for f in ob.block_faces:
        f_verts = [bm.verts[vid] for vid in f.verts]
        bf = bm.faces.get(f_verts)
        if f.pos != -1 and f.neg != -1:
            if (not ob.blocks[f.pos].enabled and ob.blocks[f.neg].enabled) \
                    or (ob.blocks[f.pos].enabled and not ob.blocks[f.neg].enabled):
                if not bf:
                    bm.faces.new(f_verts)
            else:
                if bf:
                    bm.faces.remove(bf)
        elif (f.pos == -1 and f.neg != -1):
            if ob.blocks[f.neg].enabled:
                if not bf:
                    bm.faces.new(f_verts)
            else:
                if bf:
                    bm.faces.remove(bf)
        elif (f.pos != -1 and f.neg == -1):
            if ob.blocks[f.pos].enabled:
                if not bf:
                    bm.faces.new(f_verts)
            else:
                if bf:
                    bm.faces.remove(bf)

    for e in ob.block_edges:
        bme = bm.edges.get((bm.verts[e.v1],bm.verts[e.v2]))
        edge_found = False
        for b in ob.blocks:
            if b.enabled and e.v1 in b.verts and e.v2 in b.verts:
                edge_found = True
                bme.hide_set(False)
                continue
        if not edge_found:
            bme.hide_set(True)
    bpy.ops.draw.directions('INVOKE_DEFAULT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')

def get_snap_vertices(bob):
    gob = bpy.data.objects[bpy.context.scene.SnapObject]
    # vg = gob.vertex_groups.get(str(snapId))

    group_lookup = {g.index: g.name for g in gob.vertex_groups}
    verts = {name: [] for name in group_lookup.values()}
    for v in gob.data.vertices:
        for g in v.groups:
            verts[group_lookup[g.group]].append(v.index)

    for key, value in verts.items() :
        bm = bmesh.new()
        bm.from_mesh(gob.data)
        bm.select_mode = {"VERT","EDGE"}
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        edges = []
        averts = []
        bm.verts.ensure_lookup_table()
        for v in value:
            bm.verts[v].select = True
        bm.select_flush(True)
        bm.select_flush_mode()
        for e in bm.edges:
            if e.select:
                edges.append((e.verts[0].index,e.verts[1].index))
        if edges:
            vertids = utils.sortEdges(edges)
        verts[key] = [gob.data.vertices[vid].co for vid in vertids]
    return verts

def collectEdges(bob, lengths):
    bob.select = True
    bpy.context.scene.objects.active = bob
    bpy.ops.object.mode_set(mode='EDIT')
    # snap_vertices = get_snap_vertices(bob)
    bm = bmesh.from_edit_mesh(bob.data)
    layers = bm.edges.layers
    snapIdl = layers.string.get('snapId')
    block_edges = dict()

    def getDefault(e, var, prop):
        if type(prop) is float:
            val = e[layers.float.get(var)]
        elif type(prop) is int:
            val = e[layers.int.get(var)]
        return val

    for e in bm.edges:
        be = dict()
        ev = list([e.verts[0].index,e.verts[1].index])
        if ev in lengths[0]:
            ind = lengths[0].index(ev)
            L = lengths[1][ind]
        else:
            L = (e.verts[0].co-e.verts[1].co).length
        be["type"] = e[layers.string.get("type")].decode()
        be["x1"] = e[layers.float.get('x1')] #getDefault(e, "x1", bob.x1)
        be["x2"] = e[layers.float.get('x2')] #getDefault(e, "x2", bob.x2)
        be["r1"] = e[layers.float.get('r1')] #getDefault(e, "r1", bob.r1)
        be["r2"] = e[layers.float.get('r2')] #getDefault(e, "r2", bob.r2)
        be["N"] = e[layers.int.get('cells')] #getDefault(e, "nodes", bob.Nodes)
        be["L"] = L
        if not be["N"]:
            be["N"] = 10
        if not be["r1"]:
            be["r1"] = 1.
        if not be["r2"]:
            be["r2"] = 1.
        be = utils.edgeMapping(be)
        block_edges[(e.verts[1].index,e.verts[0].index)] = be
        be = dict(be)
        be["x1"],be["x2"] = be["x2"],be["x1"]
        be["r1"],be["r2"] = be["r2"],be["r1"]
        be = utils.edgeMapping(be)

        block_edges[(e.verts[0].index,e.verts[1].index)] = be

        # if e[snapIdl]:
            # verts = snap_vertices[e[snapIdl].decode()]
            # if (verts[0]-e.verts[0].co).length < (verts[0] - e.verts[1].co).length:
                # be["verts"] = verts
            # else:
                # verts = list(reversed(verts))
                # be["verts"] = verts
        # else:
            # be["verts"] = (e.verts[0].co,e.verts[1].co)
    return block_edges


# Kalle's implementation
def getPolyLines(verts, edges, bob):
    scn = bpy.context.scene
    polyLinesPoints = []
    polyLines = ''
    polyLinesLengths = [[], []]
    tol = 1e-6

    def isPointOnEdge(point, A, B):
        eps = (((A - B).magnitude - (point-B).magnitude) - (A-point).magnitude)
        return True if (abs(eps) < tol) else False

    # nosnap= [False for i in range(len(edges))]
    # for eid, e in enumerate(obj.data.edges):
        # nosnap[eid] = e.use_edge_sharp

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    geoobj = bpy.data.objects[bob.SnapObject]
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    geoobj.select = False # avoid deletion

# First go through all vertices in the block structure and find vertices snapped to edges
# When found, add a vertex at that location to the polyLine object by splitting the edge
# Create a new Blender object containing the newly inserted verts. Then use Blender's
# shortest path algo to find polyLines.

    for vid, v in enumerate(verts):
        found = False
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                found = True
                break   # We have found a vertex co-located, continue with next block vertex
        if not found:
            for geid, ge in enumerate(geo_edges):
                if (isPointOnEdge(v, geo_verts[ge[0]], geo_verts[ge[1]])):
                    geo_verts.append(v)
                    geo_edges.append([geo_edges[geid][1],len(geo_verts)-1]) # Putting the vert on the edge, by splitting it in two.
                    geo_edges[geid][1] = len(geo_verts)-1
                    break # No more iteration, go to next block vertex

    mesh_data = bpy.data.meshes.new("deleteme")
    mesh_data.from_pydata(geo_verts, geo_edges, [])
    mesh_data.update()
    geoobj = bpy.data.objects.new('deleteme', mesh_data)
    bpy.context.scene.objects.link(geoobj)
    geo_verts = list(blender_utils.vertices_from_mesh(geoobj))
    geo_edges = list(blender_utils.edges_from_mesh(geoobj))
    bpy.context.scene.objects.active=geoobj

# Now start the search over again on the new object with more verts
    snapped_verts = {}
    for vid, v in enumerate(verts):
        for gvid, gv in enumerate(geo_verts):
            mag = (v-gv).magnitude
            if mag < tol:
                snapped_verts[vid] = gvid
                break   # We have found a vertex co-located, continue with next block vertex

    bpy.ops.wm.context_set_value(data_path="tool_settings.mesh_select_mode", value="(True,False,False)")
    for edid, ed in enumerate(edges):
        if ed[0] in snapped_verts and ed[1] in snapped_verts:# and not nosnap[edid]:
            geoobj.hide = False
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            geoobj.data.vertices[snapped_verts[ed[0]]].select = True
            geoobj.data.vertices[snapped_verts[ed[1]]].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_vertex_path(type='EDGE_LENGTH')
            except:
                bpy.ops.mesh.shortest_path_select()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.duplicate()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            polyLineobj = bpy.data.objects['deleteme.001']
            if len(polyLineobj.data.vertices) > 2:
                polyLineverts = list(blender_utils.vertices_from_mesh(polyLineobj))
                polyLineedges = list(blender_utils.edges_from_mesh(polyLineobj))
                for vid, v in enumerate(polyLineverts):
                    mag = (v-verts[ed[0]]).magnitude
                    if mag < tol:
                        startVertex = vid
                        break
                polyLineStr, vectors, length = sortedVertices(polyLineverts,polyLineedges,startVertex)
                polyLinesPoints.append([ed[0],ed[1],vectors])
                polyLinesLengths[0].append([min(ed[0],ed[1]), max(ed[0],ed[1])]) # write out sorted
                polyLinesLengths[1].append(length)
                polyLine = 'polyLine {} {} ('.format(*ed)
                polyLine += polyLineStr
                polyLine += ')\n'
                polyLines += polyLine

            geoobj.select = False
            polyLineobj.select = True
            bpy.ops.object.delete()
    geoobj.select = True
    bpy.ops.object.delete()
    return polyLines, polyLinesPoints, polyLinesLengths

def sortedVertices(verts,edges,startVert):
    sorted = []
    vectors = []
    sorted.append(startVert)
    vert = startVert
    length = len(edges)+1
    for i in range(len(verts)):
        for eid, e in enumerate(edges):
            if vert in e:
                if e[0] == vert:
                    sorted.append(e[1])
                else:
                    sorted.append(e[0])
                edges.pop(eid)
                vert = sorted[-1]
                break

    polyLine = ''
    length = 0.
    for vid, v in enumerate(sorted):
        polyLine += '({} {} {})'.format(*verts[v])
        vectors.append(verts[v])
        if vid>=1:
            length += (vectors[vid] - vectors[vid-1]).magnitude
    return polyLine, vectors, length

initSwiftBlockProperties()
def register():
    bpy.utils.register_module(__name__)
def unregister():
    bpy.utils.unregister_module(__name__)
if __name__ == "__main__":
        register()
