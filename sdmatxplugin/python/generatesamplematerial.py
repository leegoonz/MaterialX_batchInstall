#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import MaterialX as mx
import os
import sdmatx
import substance_codegen
from samplesshaders import ball, makeRustNetwork, makeDesaturatedNetwork, simplest
import automatx as ax

SD_MATERIAL_TYPE = 'ND_standard_surface_surfaceshader'


def main():
    matx_doc_root = sdmatx.getMatxDocRoot()
    stdlib_path = os.path.join(matx_doc_root, 'stdlib')
    bxdf_path = os.path.join(sdmatx.getDataDirectory(), 'alglib', 'bxdf')
    # Generate a shader adhering to the painter schema
    stdLib = mx.createDocument()

    mx.readFromXmlFile(stdLib, filename='stdlib_defs.mtlx', searchPath=stdlib_path)
    mx.readFromXmlFile(stdLib, filename='stdlib_ng.mtlx', searchPath=stdlib_path)
    lib = ax.Library(stdLib)
    mDoc = mx.createDocument()
    docs_to_include = [os.path.join('stdlib', 'stdlib_defs.mtlx'),
                       os.path.join('bxdf', 'standard_surface.mtlx')]
    for f in docs_to_include:
        d = mx.createDocument()
        f = sdmatx.makeConsistentPath(f)
        mx.readFromXmlFile(d, f, sdmatx.getMatxSearchPathString())
        mDoc.importLibrary(d)

    nd = mDoc.getNodeDef(SD_MATERIAL_TYPE)
    material_name = 'TestMaterial'
    material = mDoc.addMaterial(material_name)
    shader_ref = material.addShaderRef(material_name)
    shader_ref.setAttribute("node", nd.getNodeString())
    node_graph = mDoc.addNodeGraph('inputs')

    node_def = mDoc.addNodeDef(name='ND_MtlxShader', node='MtlxShader')
    node_def.removeOutput('out')
    # makeDesaturatedNetwork(node_graph, node_def, shader_ref, lib)
    # makeRustNetwork(node_graph, node_def, shader_ref, lib)
    # simplest(node_graph, node_def, shader_ref, lib)
    ball(node_graph, node_def, shader_ref, lib)
    node_graph.setNodeDef(node_def)
    sdmatx.forwardOutputs(material_name, mDoc, node_graph, node_def)
    val_result, val_string = mDoc.validate()
    if val_result:
        print('Validation succeeded')
    else:
        print('Validation failed')
        print(val_string)
        return 1

    temp_dir = sdmatx.getTempDirectory()
    glslfx_output_files = sdmatx.getGLSLFXOutputFiles(mDoc)
    mtlx_output_file = os.path.join(temp_dir, 'test.mtlx')
    mx.writeToXmlFile(mDoc, mtlx_output_file)
    substance_codegen.mtlx2GLSLFX(mDoc,
                       glslfx_output_files['glsl_output'],
                       glslfx_output_files['glslfx_output'],
                       glslfx_output_files['glslfx_template'],
                       sdmatx.getMatxSearchPathList(),
                       root_material=material_name)

    # Enable to pop up results in materialx view
    # sdmatx.showMatxView(mDoc,
    #                     matx_filename=mtlx_output_file,
    #                     blocking=True,
    #                     resource_paths=[],
    #                     matx_doc_paths=sdmatx.getMatxSearchPathList())


if __name__ == '__main__':
    main()
