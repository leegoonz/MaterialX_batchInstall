#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import sd
import os
import MaterialX as mx
from tests import tools
import sdmatx


def main():
    context = sd.getContext()
    for mdl_path in sdmatx.paths.getMdlDirectories():
        context.getSDApplication().getModuleMgr().addRootPath('mdl', mdl_path)

    data_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', '..', 'data'))

    sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
                                                          'substances',
                                                          'Floor.sbs'))
    assert(sdPackage)
    shader = sdPackage.findResourceFromUrl('Shader')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'simpleuber.sbs'))
    # shader = sdPackage.findResourceFromUrl('MDL_Material')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'subgraph_used.sbs'))
    # shader = sdPackage.findResourceFromUrl('MaterialX_Graph')

    assert(shader)
    material_name = shader.getIdentifier()
    package_dir = os.path.dirname(sdPackage.getFilePath())
    mtlxdoc = sdmatx.mdl2mtlx_material(shader,
                                       material_name,
                                       sdPackage,
                                       sdmatx.getMatxSearchPathString(),
                                       package_dir)

    temp_dir = sdmatx.paths.getTempDirectory()
    target_file = os.path.join(temp_dir, shader.getIdentifier() + '.mtlx')
    mx.writeToXmlFile(mtlxdoc, target_file)
    sdmatx.exportDependentFiles(os.path.dirname(target_file),
                                mtlxdoc,
                                sdmatx.getMatxSearchPathString(),
                                package_dir)

    # Enable to pop up results in materialx view
    # sdmatx.showMatxView(mtlxdoc,
    #              matx_filename=mtlx_output_file,
    #              blocking=True,
    #              resource_paths=[package_dir],
    #              matx_doc_paths=sdmatx.getMatxSearchPathList())

if __name__ == '__main__':
    main()
