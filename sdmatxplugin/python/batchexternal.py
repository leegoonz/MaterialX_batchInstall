# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
import os
import subprocess

import MaterialX as mx
import sd
import sdmatx
import substance_codegen
from tests import tools

logger = logging.getLogger("SDMaterialX")


def main():
    logger.setLevel(logging.INFO)
    context = sd.getContext()
    for mdl_path in sdmatx.paths.getMdlDirectories():
        context.getSDApplication().getModuleMgr().addRootPath('mdl', mdl_path)

    data_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', '..', 'data'))

    sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
                                                          'samples',
                                                          'Floor',
                                                          'Floor.sbs'))
    assert (sdPackage)
    shader = sdPackage.findResourceFromUrl('Shader')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'Shader.sbs'))
    # assert (sdPackage)
    # shader = sdPackage.findResourceFromUrl('Shader')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'simpleuber.sbs'))
    # shader = sdPackage.findResourceFromUrl('MDL_Material')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'subgraph_used.sbs'))
    # shader = sdPackage.findResourceFromUrl('MaterialX_Graph')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'substances',
    #                                                       'PainterTest.sbs'))
    # shader = sdPackage.findResourceFromUrl('Shader')

    # sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
    #                                                       'Teapot_Demo_Matx',
    #                                                       'Teapot_Demo_MatX.sbs'))
    # shader = sdPackage.findResourceFromUrl('Teapot_Demo_MatX')

    assert (shader)
    assert (sdmatx.isMtlxGraph(shader))
    try:
        with sdmatx.Benchmark('All'):
            material_name = shader.getIdentifier()
            package_dir = os.path.dirname(sdPackage.getFilePath())
            with sdmatx.Benchmark('mdl2mtlx_material'):
                # custom_root = shader.getNodes()[3]
                # mtlxdoc = sdmatx.mdl2mtlx_custom_root(shader,
                #                                       material_name,
                #                                       sdPackage,
                #                                       sdmatx.getMatxSearchPathString(),
                #                                       custom_root,
                #                                       package_dir)

                mtlxdoc = sdmatx.mdl2mtlx_material(shader,
                                                   material_name,
                                                   sdPackage,
                                                   sdmatx.getMatxSearchPathString(),
                                                   package_dir)

            glslfx_output_files = sdmatx.getGLSLFXOutputFiles(mtlxdoc)
            temp_dir = sdmatx.paths.getTempDirectory()
            mtlx_output_file = os.path.join(temp_dir, 'test.mtlx')
            res, log = mtlxdoc.validate()
            mx.writeToXmlFile(mtlxdoc, mtlx_output_file)
            if not res:
                raise BaseException(log)
            try:
                if not os.path.isdir(temp_dir):
                    os.mkdir(temp_dir)
                with sdmatx.Benchmark('mtlx2GLSLFX_python'):
                    substance_codegen.mtlx2GLSLFX(
                        mtlxdoc,
                        glslfx_output_files['glsl_output'],
                        glslfx_output_files['glslfx_output'],
                        glslfx_output_files['glslfx_template'],
                        sdmatx.getMatxSearchPathList(),
                        root_material=material_name)
            except subprocess.CalledProcessError as e:
                logger.error(str(e))
                return

            try:
                if not os.path.isdir(temp_dir):
                    os.mkdir(temp_dir)
                with sdmatx.Benchmark('mtlx2PainterGLSL_python'):
                    substance_codegen.mtlx2PainterGLSL(
                        mtlxdoc,
                        os.path.join(sdmatx.getTempDirectory(),
                                     'painter_test.glsl'),
                        sdmatx.getMatxSearchPathList(),
                        root_material=material_name,
                        painter_template_directory=sdmatx.getPainterTemplateDirectory())
            except subprocess.CalledProcessError as e:
                logger.error(str(e))
                return
    finally:
        sdmatx.dump_benchmarks()
    # Enable to pop up results in materialx view
    # sdmatx.showMatxView(mtlxdoc,
    #                     matx_filename=mtlx_output_file,
    #                     blocking=True)


if __name__ == '__main__':
    main()
