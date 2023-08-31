import uvicorn
import time
from typing import Union
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, File, Body, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import io
import bpy
import bmesh
import tempfile
import shutil
import os
from supabase import create_client, Client
from pathlib import Path

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)
# bpy.ops.wm.read_factory_settings()
# bpy.ops.wm.open_mainfile(filepath="")
# Install the addon from the zip file.

    
addon_zip_path = "./VRM_Addon_for_Blender-release.zip"
addon_name = os.path.splitext(os.path.basename(addon_zip_path))[0]
if addon_name not in bpy.context.preferences.addons:
    bpy.ops.preferences.addon_install(filepath=addon_zip_path)
    bpy.ops.preferences.addon_enable(module=addon_name)

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # cookie 포함 여부를 설정한다. 기본은 False
    allow_methods=["*"],    # 허용할 method를 설정할 수 있으며, 기본값은 'GET'이다.
    allow_headers=["*"],   # 허용할 http header 목록을 설정할 수 있으며 Content-Type, Accept, Accept-Language, Content-Language은 항상 허용된다.
)

progress_dict = []

if __name__ == '__main__':
    uvicorn.run(app, host = "0.0.0.0", port = 8000)

@app.get("/progress")
def read_root():
    return progress_dict

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

# id: userID, name: filename, 
@app.post("/")
async def upload_file(file: UploadFile = File(...), id: str = Body(...), name: str = Body(...)):
    
    bpy.context.preferences.filepaths.use_relative_paths = False
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Save the uploaded file to the temporary directory
    temp_dir = tempfile.mkdtemp()
    file_path = f"{temp_dir}/{file.filename}"
    with open(file_path, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    start_time = time.time()
    # Import vrm file to blender scene
    result = bpy.ops.import_scene.vrm(filepath=file_path)
    if result != {"FINISHED"}:
        raise Exception(f"Failed to import vrm: {result}")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")

    for i, o in enumerate(bpy.context.scene.objects):
        if o.type == 'MESH':
            mesh = o.data
            basis_In = False
            shape_keys = mesh.shape_keys
            if shape_keys is not None:
                for index, key_block in enumerate(shape_keys.key_blocks):
                    temp_Basic = "basis"
                    if(temp_Basic in key_block.name.lower()):
                        basis_In = True
                    else:
                        if(basis_In == True):
                            o.shape_key_remove(key_block)
               
        if o.name == 'Cube':
            o.select_set(True)
        else:
            o.select_set(False)

    bpy.ops.object.delete() 
    
    save_as_glb(file.filename, id, name)

    return {
        "file": file.filename,
        "id": id,
        "name": name
    }


def save_as_glb(filepath, id, name):
    name_without_extension = filepath.split(".")[0]
    file_save = name_without_extension + ".vrm"

    bpy.ops.export_scene.vrm(filepath=file_save)

    file = open(file_save, 'rb')
    upload_avatar(id, file_save, file)

def upload_avatar(user_id, filename, file):
    filepath = f"{user_id}/{filename}"
    supabase.storage.from_("optimize").upload(filepath, file, file_options={"x-upsert": "true"})
    supabase.table("avatars").update({"optimized": True}).eq().execute()
    file_path_delete = filename
    try:
        os.remove(file_path_delete)
        print(f"File '{file_path_delete}' has been removed successfully.")
    except FileNotFoundError:
        print(f"File '{file_path_delete}' not found.")
    except Exception as e:
        print(f"An error occurred while trying to remove the file: {e}")



    # # Remove shapekeys from all objects
    # for obj in bpy.data.objects:
    #     if obj.type == 'MESH':
    #         if obj.data.shape_keys:
    #             shapekey_names = [key_block.name for key_block in obj.data.shape_keys.key_blocks]
    #             for key_name in shapekey_names:
    #                 key_block = obj.data.shape_keys.key_blocks.get(key_name)
    #                 if key_block:
    #                     obj.shape_key_remove(key_block)
    # # Remove unused data blocks
    # bpy.ops.outliner.orphans_purge()

        # bpy.ops.export_scene.gltf(filepath=file_save, check_existing=True, export_format='GLB', ui_tab='GENERAL', export_copyright="", export_image_format='AUTO', export_texture_dir="", export_keep_originals=False, export_texcoords=True, export_normals=True, export_draco_mesh_compression_enable=False, export_draco_mesh_compression_level=6, export_draco_position_quantization=14, export_draco_normal_quantization=10, export_draco_texcoord_quantization=12, export_draco_color_quantization=10, export_draco_generic_quantization=12, export_tangents=False, export_materials='EXPORT', export_colors=True, use_mesh_edges=False, use_mesh_vertices=False, export_cameras=False, use_selection=False, use_visible=False, use_renderable=False, use_active_collection=False, use_active_scene=False, export_extras=False, export_yup=True, export_apply=False, export_animations=True, export_frame_range=True, export_frame_step=1, export_force_sampling=True, export_nla_strips=True, export_def_bones=False, export_current_frame=False, export_skins=True, export_all_influences=False, export_morph=True, export_morph_normal=True, export_morph_tangent=False, export_lights=False, will_save_settings=False, filter_glob="*.glb;*.gltf")