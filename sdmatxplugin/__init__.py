#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

'''
Top level init file.

Extend search path to include the python subfolder, then import all
registerable Substance Designer modules.
'''

import logging
import os
# add Python paths
import sys


class InitializationException(BaseException):
    pass


class CompatibilityException(InitializationException):
    pass


def _updateMDLFiles(logger):
    import os
    import sdmatx
    mdl_root = os.path.join(sdmatx.getMdlDirectories()[0], 'mtlx')
    os.makedirs(mdl_root, exist_ok=True)
    if not os.path.isfile(os.path.join(mdl_root, 'utilities.mdl')):
        raise InitializationException('utilities.mdl missing from installation')

    # Always, generate the shared file
    # Should be fast every time
    logger.info('Generating shared.mdl')
    shared_content = sdmatx.mtlx2mdl_shared()
    shared_filename = os.path.join(mdl_root, 'shared.mdl')
    with open(shared_filename, 'w') as f:
        f.write(shared_content)
    modules = ['stdlib', 'bxdf', 'alglib']
    mtlx_search_path = sdmatx.getMatxSearchPathString()

    mdl_root = os.path.join(sdmatx.getMdlDirectories()[0], 'mtlx')
    for m in modules:
        mdl_path = os.path.join(mdl_root, m + '.mdl')
        if os.path.isfile(mdl_path):
            logger.info('Found existing module: {}'.format(m))
            old_content_hash = sdmatx.getMdlSourceHash(mdl_path)
            new_content_hash = sdmatx.hashMtlxDocsForModule(m, sdmatx.getMatxSearchPathString())
            if old_content_hash == new_content_hash:
                logger.info('Hash matching for module {}, keeping'.format(m))
                # This mdl file exits and has a content hash matching the previous version
                continue
            else:
                logger.info('Hash mismatch for module {} old:{}, new:{}, rebuilding'.format(m, old_content_hash,
                                                                                            new_content_hash))
        else:
            logger.info('Module {} missing, building'.format(m))
        content = sdmatx.mtlx2mdl_library(m, 'shared', mtlx_search_path)
        with open(mdl_path, 'w') as f:
            f.write(content)


def _setupSdmatxPath(logger):
    mod_path, _ = os.path.split(os.path.abspath(__file__))
    plugin_mod_path = os.path.join(mod_path, 'python')
    sys.path.append(plugin_mod_path)
    try:
        import sdmatx
        logger.info('Found sdmatx at {}'.format(plugin_mod_path))
    except ImportError:
        raise CompatibilityException('Failed to initialize sdmatx module')


def _setupMaterialXPath(logger):
    mod_path, _ = os.path.split(os.path.abspath(__file__))
    # Look for MaterialX in the installation package
    materialx_mod_path = os.path.join(mod_path, 'MaterialX', 'python')
    if not os.path.isdir(materialx_mod_path):
        # Default location missing
        # Check environment variables
        materialx_root = os.getenv('MATERIALX_ROOT')
        if materialx_root:
            materialx_mod_path = os.path.join(materialx_root, 'python')
        else:
            raise CompatibilityException('MaterialX not found')
    sys.path.append(materialx_mod_path)
    try:
        import MaterialX as mx
        matx_version = mx.getVersionString()
        matx_version_list = [int(i) for i in matx_version.split('.')]
        if matx_version_list[0] == 1 and matx_version_list[1] == 37 or matx_version_list[2] == 1:
            logger.info('Found MaterialX version {} at {}'.format(matx_version, materialx_mod_path))
        else:
            logger.warning(
                'Unsupported MaterialX version {}. The expected version is 1.37.1, anything different than that may cause issues'.format(
                    matx_version))
    except ImportError:
        raise CompatibilityException('MaterialX not found or can\'t load. Place installation in sdmatxplugin/MaterialX')


def _checkDesignerVersion(logger):
    from PySide2 import QtCore
    sd_version = QtCore.QCoreApplication.applicationVersion()
    sd_version_list = [int(i) for i in sd_version.split('.')]
    if sd_version_list[0] > 2000:
        sd_version_list[0] = sd_version_list[0] - 2010
    if sd_version_list[0] >= 10:
        logger.info('Found Substance Designer Version {}'.format(sd_version))
    else:
        raise CompatibilityException('Unsupported Designer version {}, expected 10.1.0 or higher'.format(sd_version))

    python_version = sys.version_info
    if python_version[0] == 3 and python_version[1] == 7:
        logger.info('Found Python version {}.{}.{}'.format(*python_version[:3]))
    else:
        raise CompatibilityException(
            'Unsupported Python version {}.{}.{} Expected 3.7.x'.format(*python_version[:3]))


def initializeSDPlugin():
    # add mdl paths
    try:
        import sd

        ctx = sd.getContext()

        logger = logging.getLogger("SDMaterialX")
        # if channelName is None, use the logger name as the channel.
        logger.addHandler(ctx.createRuntimeLogHandler(channelName=None))
        logger.setLevel(logging.INFO)
        logger.propagate = False

        _checkDesignerVersion(logger)
        _setupMaterialXPath(logger)
        _setupSdmatxPath(logger)
        import sdmatx

        logger.info("SDMaterialX version {}".format(sdmatx.get_version_string()))

        app = ctx.getSDApplication()

        # Check for mdl documents and build them if not present
        _updateMDLFiles(logger)

        mdlpaths = sdmatx.paths.getMdlDirectories()
        moduleManager = app.getModuleMgr()
        paths = [p.get() for p in moduleManager.getRootPaths('mdl')]
        for mdlpath in mdlpaths:
            if mdlpath not in paths:
                logger.info("Adding to MDL search paths: " + mdlpath)
                moduleManager.addRootPath('mdl', mdlpath)

        # register UI callback
        import ShadergraphPlugin
        ShadergraphPlugin.initializeShaderGraph()
    except InitializationException as e:
        logger.error('Failed to initialize MaterialX plugin: {}'.format(str(e)))
        return


def uninitializeSDPlugin():
    # remove mdl path
    import sd
    import sdmatx
    app = sd.getContext().getSDApplication()
    mdlpaths = sdmatx.paths.getMdlDirectory()
    moduleManager = app.getModuleMgr()
    paths = [p.get() for p in moduleManager.getRootPaths('mdl')]
    for mdlpath in mdlpaths:
        if mdlpath in paths:
            logger.info("Clearing from MDL search paths: " + mdlpath)
            moduleManager.removeRootPath('mdl', mdlpath)

    # unregister UI callback
    import ShadergraphPlugin
    ShadergraphPlugin.uninitializeShaderGraph()
