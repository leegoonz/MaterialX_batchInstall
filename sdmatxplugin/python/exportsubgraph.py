#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import logging
import os

import MaterialX as mx

import sd
import sdmatx
from tests import tools

logger = logging.getLogger("SDMaterialX")


def main():
    context = sd.getContext()
    for p in sdmatx.paths.getMdlDirectories():
        context.getSDApplication().getModuleMgr().addRootPath(
            'mdl', p)

    data_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'substances'))
    sdPackage = tools.loadSDPackage(context, os.path.join(data_dir,
                                                          'subgraph_test.sbs'))
    assert (sdPackage)

    exported_file = False
    # Get user module name from package name
    package_file_root = os.path.splitext(os.path.basename(
        sdPackage.getFilePath()))[0]
    mdl_user_module_name = 'user/' + package_file_root

    for s in sdPackage.getChildrenResources(False):
        from sd.api.mdl.sdmdlgraph import SDMDLGraph
        if isinstance(s, SDMDLGraph):
            name = s.getIdentifier()
            logger.info('Exporting {}'.format(name))
            try:
                doc = sdmatx.mdl2mtlx_subgraph(s,
                                               name,
                                               sdPackage,
                                               sdmatx.getMatxSearchPathString(),
                                               data_dir)
                val_res, val_log = doc.validate()
                if not val_res:
                    logger.error(val_log)
                    raise sdmatx.MDLToMaterialXException('Invalid MaterialX document generated')
                else:
                    logger.info('validation successful')
                mtlx_dir = os.path.join(
                    sdmatx.getUserMaterialXDocDirectory(),
                    mdl_user_module_name)
                if not os.path.isdir(mtlx_dir):
                    os.makedirs(mtlx_dir)
                mtlx_path = os.path.join(mtlx_dir,
                                         name + '.mtlx')
                mx.writeToXmlFile(doc,
                                  mtlx_path)
                exported_file = True
            except BaseException as e:
                logger.error(str(e))

    if exported_file:
        mdl_content = sdmatx.mtlx2mdl_library(
            mdl_user_module_name,
            'shared',
            sdmatx.getMatxSearchPathString(),
            exception_on_omissions=True)
        mdl_output_file = os.path.join(sdmatx.getMdlSubgraphDirectory(),
                                       mdl_user_module_name + '.mdl')
        mdl_output_dir = os.path.dirname(mdl_output_file)
        if not os.path.isdir(mdl_output_dir):
            os.makedirs(mdl_output_dir)

        with open(mdl_output_file,
                  'w') as f:
            f.write(mdl_content)


if __name__ == '__main__':
    main()
