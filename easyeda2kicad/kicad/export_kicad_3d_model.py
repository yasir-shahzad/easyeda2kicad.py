"""
Convert 3D model from .obj format to .wrl with colors
"""

# Global imports
import re
from typing import List

from easyeda2kicad.easyeda.parameters_easyeda import ee_3d_model
from easyeda2kicad.kicad.parameters_kicad import ki_3d_model

VRML_HEADER = """#VRML V2.0 utf8
# 3D model generated by easyeda2kicad.py (https://github.com/uPesy/easyeda2kicad.py)
"""


def get_materials(obj_data: str) -> dict:

    material_regex = "newmtl .*?endmtl"
    matchs = re.findall(pattern=material_regex, string=obj_data, flags=re.DOTALL)

    materials = {}
    for match in matchs:
        material = {}
        for value in match.splitlines():
            if value.startswith("newmtl"):
                material_id = value.split(" ")[1]
            elif value.startswith("Ka"):
                material["ambient_color"] = value.split(" ")[1:]
            elif value.startswith("Kd"):
                material["diffuse_color"] = value.split(" ")[1:]
            elif value.startswith("Ks"):
                material["specular_color"] = value.split(" ")[1:]
            elif value.startswith("d"):
                material["transparency"] = value.split(" ")[1]

        materials[material_id] = material
    return materials


def get_vertices(obj_data: str) -> List:
    vertices_regex = "v (.*?)\n"
    matchs = re.findall(pattern=vertices_regex, string=obj_data, flags=re.DOTALL)

    return [
        " ".join([str(round(float(coord) / 2.54, 4)) for coord in vertice.split(" ")])
        for vertice in matchs
    ]


def generate_wrl_model(model_3d: ee_3d_model):
    materials = get_materials(obj_data=model_3d.raw_obj)
    vertices = get_vertices(obj_data=model_3d.raw_obj)

    raw_wrl = VRML_HEADER
    shapes = model_3d.raw_obj.split("usemtl")[1:]
    for shape in shapes:
        lines = shape.splitlines()
        material = materials[lines[0].replace(" ", "")]
        index_counter = 0
        link_dict = {}
        coordIndex = []
        points = []
        for line in lines[1:]:
            if len(line) > 0:
                face = [int(index) for index in line.replace("//", "").split(" ")[1:]]
                face_index = []
                for index in face:
                    if index not in link_dict:
                        link_dict[index] = index_counter
                        face_index.append(str(index_counter))
                        points.append(vertices[index - 1])
                        index_counter += 1
                    else:
                        face_index.append(str(link_dict[index]))
                face_index.append("-1")
                coordIndex.append(",".join(face_index) + ",")
        points.insert(-1, points[-1])

        shape_str = f"""
            Shape{{
                appearance Appearance {{
                    material  Material 	{{
                        diffuseColor {' '.join(material['diffuse_color'])}
                        specularColor {' '.join(material['specular_color'])}
                        ambientIntensity 0.2
                        transparency {material['transparency']}
                        shininess 0.5
                    }}
                }}
                geometry IndexedFaceSet {{
                    ccw TRUE
                    solid FALSE
                    coord DEF co Coordinate {{
                        point [
                            {(", ").join(points)}
                        ]
                    }}
                    coordIndex [
                        {"".join(coordIndex)}
                    ]
                }}
            }}"""

        raw_wrl += shape_str

    return ki_3d_model(
        translation=None, rotation=None, name=model_3d.name, raw_wrl=raw_wrl
    )


class exporter_3d_model_kicad:
    def __init__(self, model_3d: ee_3d_model):
        self.input = model_3d
        self.output = generate_wrl_model(model_3d=model_3d)

    def export(self, lib_path: str):
        with open(
            file=f"{lib_path}.3dshapes/{self.output.name}.wrl",
            mode="w",
            encoding="utf-8",
        ) as my_lib:
            my_lib.write(self.output.raw_wrl)