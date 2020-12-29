#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import enum
import logging
import os
import platform
import sys

import MaterialX as mx
from .config import Config

logger = logging.getLogger("SDMaterialX")

__platform_bin_suffix = ''
if sys.platform == "linux" or sys.platform == "linux2":
    __platform_bin_suffix = ''
elif sys.platform == "darwin":
    __platform_bin_suffix = ''
elif sys.platform == "win32":
    __platform_bin_suffix = '.exe'

# This is global state to stay compatible with the current code base
# config/paths should probably be passed around rather than being global
_config = None


class PathException(BaseException):
    pass


def _getConfig():
    '''
    :return: Config
    '''
    global _config
    if not _config:
        raise PathException('Path module not initialized with a config object')
    return _config


class MissingDirOperation(enum.Enum):
    DONT_CREATE = 1
    CREATE = 2
    CREATE_RECURSIVE = 3


class DirectoryFailureMode(enum.Enum):
    RAISE = 1
    RETURN_NONE = 2


def _handleMissingDir(user_path, dir_operation, error_approach):
    if user_path is None:
        if error_approach == DirectoryFailureMode.RETURN_NONE:
            return None
        else:
            raise PathException('None path not supported')
    if not os.path.isdir(user_path):
        try:
            if dir_operation == MissingDirOperation.DONT_CREATE:
                if error_approach == DirectoryFailureMode.RAISE:
                    raise PathException('Expected directory {} missing'.format(user_path))
                else:
                    return None
            elif dir_operation == MissingDirOperation.CREATE:
                logger.debug('Creating path {}'.format(user_path))
                os.mkdir(user_path)
            elif dir_operation == MissingDirOperation.CREATE_RECURSIVE:
                logger.debug('Creating path {}'.format(user_path))
                os.makedirs(user_path)
        except FileNotFoundError:
            if error_approach == DirectoryFailureMode.RETURN_NONE:
                return None
            else:
                raise PathException('Failed to create path {}'.format(user_path))
    return user_path


def getUserPluginDataDirectory():
    org_name = None
    app_name = None
    doc_path = None
    try:
        from PySide2 import QtCore
        org_name = QtCore.QCoreApplication.organizationName()
        app_name = QtCore.QCoreApplication.applicationName()
        doc_path_list = QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.DocumentsLocation)
        if len(doc_path_list) > 1:
            logger.warning('Multiple Document Paths found, using {}'.format(doc_path_list[0]))
        if len(doc_path_list) == 0:
            logger.warning('No document path in Qt Application, falling back to ~')
        else:
            doc_path = doc_path_list[0]
    except ModuleNotFoundError:
        pass
    if not doc_path:
        doc_path = os.path.expanduser(os.path.join('~', 'Documents'))
    sd_doc_root = os.path.join(doc_path,
                               org_name if org_name is not None else 'Allegorithmic',
                               app_name if app_name is not None else 'Substance Designer')

    user_path = os.path.join(sd_doc_root, 'sdmatx')
    return _handleMissingDir(user_path, MissingDirOperation.CREATE_RECURSIVE, DirectoryFailureMode.RETURN_NONE)


# These paths should only be used for things assumed to exist in the installed
# version of the plugin. Any data external to installation must generate
# their own paths

# TODO: add flags for installed version of these paths

def getInstallDirectory():
    # TODO: read from build configuration
    # Detect whether we are doing an in-source run or an installed run
    file_dir = os.path.dirname(__file__)
    if os.path.abspath(os.path.join(file_dir, '..', '..')).endswith(
            os.sep + 'src'):
        # Hacky way to make tests work in both submodule and standalone form
        paths = [os.path.abspath(os.path.join(
            __file__, '..', '..', '..', '..', '..', 'build', 'installed', 'sdmatxplugin')),
            os.path.abspath(os.path.join(
            __file__, '..', '..', '..', '..', '..', '..', 'build', 'installed', 'sdmatxplugin')),
            os.path.abspath(os.path.join(
            __file__, '..', '..', '..', '..', 'build', 'installed', 'sdmatxplugin'))]
        for p in paths:
            if os.path.isdir(p):
                return p
    else:
        return os.path.abspath(os.path.join(file_dir, '..', '..'))


def initPaths(plugin_path=None, doc_path=None, config_file_path=None):
    global _config
    if not plugin_path:
        plugin_path = getInstallDirectory()
    if not doc_path:
        doc_path = getUserPluginDataDirectory()
    if not config_file_path:
        config_file_path = os.path.join(plugin_path, 'data', 'config', 'sdmatxplugin-config.json')
    _config = Config(plugin_path, doc_path, config_file_path)


initPaths()


def getProjectDirectory():
    projectName = 'substance-matx'
    filePath = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    if filePath.find(projectName) != -1:
        retval = os.path.join(filePath.split(projectName)[0], projectName)
        return retval


def getMaterialXInstallDirectory():
    # Default to use MATERIALX_ROOT environment if present
    materialx_root = os.getenv('MATERIALX_ROOT')
    if materialx_root and os.path.isdir(materialx_root):
        if os.path.isdir(materialx_root):
            logger.debug('Using MaterialX from environment MATERIALX_ROOT {}'.format(materialx_root))
            return materialx_root
        else:
            logger.debug('Non-existent MaterialX from environment MATERIALX_ROOT {}. Ignoring'.format(materialx_root))

    config = _getConfig()
    materialx_root = os.path.join(config.getPluginPath(), 'MaterialX')
    return _handleMissingDir(materialx_root, MissingDirOperation.DONT_CREATE, DirectoryFailureMode.RAISE)


# TODO: Should probably be retired, keeping it for now
def getDataDirectory():
    return os.path.join(getInstallDirectory(), 'data')


def getMdlDirectories():
    config = _getConfig()
    user_dir = _handleMissingDir(getUserMdlDirectory(), MissingDirOperation.DONT_CREATE,
                                 DirectoryFailureMode.RETURN_NONE)
    return [_handleMissingDir(config.getPluginMdlPath(), MissingDirOperation.DONT_CREATE, DirectoryFailureMode.RAISE)] + \
           ([user_dir] if user_dir else [])


def _getBinDirectory():
    return os.path.join(getMaterialXInstallDirectory(), 'bin')


def getMatXViewBin():
    config = _getConfig()
    bin_path = config.getViewerBinary()
    if not os.path.isfile(bin_path):
        raise PathException('Missing viewer binary {}'.format(bin_path))
    return bin_path


def getMatXViewParameters():
    config = _getConfig()
    return config.getViewerParameters()


def getMatxDocRoot():
    return os.path.join(getMaterialXInstallDirectory(), 'libraries')


def getShaderDirectory():
    config = _getConfig()
    return _handleMissingDir(config.getDesignerGlslPath(), MissingDirOperation.DONT_CREATE, DirectoryFailureMode.RAISE)


def getPainterTemplateDirectory():
    config = _getConfig()
    return _handleMissingDir(config.getPainterTemplatePath(),
                             MissingDirOperation.DONT_CREATE,
                             DirectoryFailureMode.RAISE)


def getTempDirectory():
    config = _getConfig()
    temp_directory = config.getTempPath()
    return _handleMissingDir(temp_directory, MissingDirOperation.CREATE, DirectoryFailureMode.RAISE)


def makeMtlxPathString(path_list):
    '''
    Turns a list of paths into a single line with the os appropriate separator
    :param path_list: Vector of strings to make into a path list
    :return: str
    '''
    return mx.PATH_LIST_SEPARATOR.join(path_list)


def getMatxSearchPathList(includeUserDir=True):
    '''
    Gets the default search paths for materialx files in this project as a list
    Todo: Should we override/include using the environment variable
     MATERIALX_SEARCH_PATH?
    :return: list of strings
    '''
    # Note alglib before standard surface to make sure our version of standard
    # surface is being used
    # TODO: Redo paths so this is done explicitly rather than include order
    config = _getConfig()
    path_list = config.getMaterialXSearchPaths()
    user_doc_dir = getUserMaterialXDocDirectory()
    if includeUserDir:
        if user_doc_dir != None:
            path_list.append(user_doc_dir)
    return path_list


def getMatxSearchPathString(includeUserDir=True):
    '''
    Gets the default search paths for materialx files in this project as a
    single string separated by the materialx suggested separator character
    for the platform it is run on
    Todo: Should we override/include using the environment variable
     MATERIALX_SEARCH_PATH?
    :return: list of strings
    '''
    return makeMtlxPathString(getMatxSearchPathList(
        includeUserDir=includeUserDir))


def getDefaultMaterialXExportDirectory():
    config = _getConfig()
    export_path = config.getMaterialXExportPath()
    return _handleMissingDir(export_path, MissingDirOperation.CREATE_RECURSIVE, DirectoryFailureMode.RAISE)


def getUserMaterialXDocDirectory():
    config = _getConfig()
    user_path = config.getPluginMaterialXPath()
    return _handleMissingDir(user_path, MissingDirOperation.DONT_CREATE, DirectoryFailureMode.RAISE)


def getUserMaterialXSubgraphDirectory():
    config = _getConfig()
    user_path = config.getMaterialXSubgraphPath()
    return _handleMissingDir(user_path, MissingDirOperation.CREATE_RECURSIVE, DirectoryFailureMode.RETURN_NONE)


def getUserPainterDirectory():
    config = _getConfig()
    user_path = config.getPainterExportPath()
    return _handleMissingDir(user_path, MissingDirOperation.CREATE_RECURSIVE, DirectoryFailureMode.RAISE)


def getUserMdlDirectory():
    '''
    Gets the root of all user mdl documents for the plugin
    :return:
    '''
    config = _getConfig()
    user_path = config.getMdlSubgraphPath()
    return _handleMissingDir(user_path, MissingDirOperation.CREATE_RECURSIVE, DirectoryFailureMode.RETURN_NONE)


def getMdlSubgraphDirectory():
    user_mdl_directory = getUserMdlDirectory()
    user_path = os.path.join(user_mdl_directory, 'mtlx')
    return _handleMissingDir(user_path, MissingDirOperation.CREATE, DirectoryFailureMode.RETURN_NONE)


# TODO: This is not strictly a path operation. Should be refactored to configuration at some point?
def getStdlibMtlxModules():
    config = _getConfig()
    return config.getMaterialXStdModuleNames()


def makeConsistentPath(path):
    '''
    Makes a path look like a unix path if it's on windows
    used to make sure paths look the same on windows and *nix system so
    automatic testing can share baseline documents
    :param path: the path to convert
    :return: str
    '''
    if platform.system() == 'Windows':
        # Make sure our paths are consistent between platforms
        return path.replace('\\', '/')
    return path
