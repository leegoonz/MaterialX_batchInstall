#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import logging
import sys

logger = logging.getLogger("SDMaterialX")

_platform_bin_suffix = ''
if sys.platform == "linux" or sys.platform == "linux2":
    _platform_bin_suffix = ''
elif sys.platform == "darwin":
    _platform_bin_suffix = ''
elif sys.platform == "win32":
    _platform_bin_suffix = '.exe'


class ConfigException(BaseException):
    pass


def _resolve_patterns_str(data, pattern_map):
    if not isinstance(data, str):
        raise ConfigException('Non string values not supported \'{}\''.format(data))
    else:
        d = data
        for k, v in pattern_map.items():
            d = d.replace(k, v)
        return d


def _resolve_patterns_list(data_list, pattern_map):
    if not isinstance(data_list, list):
        raise ConfigException('Non list values not supported \'{}\''.format(data_list))
    else:
        return [_resolve_patterns(v, pattern_map) for v in data_list]


def _resolve_patterns_dict(data_map, pattern_map):
    if not isinstance(data_map, dict):
        raise ConfigException('Non dict values not supported \'{}\''.format(data_map))
    return {
        k: _resolve_patterns(v, pattern_map) for k, v in data_map.items() if not k.startswith('_comment')
    }


def _resolve_preserve(data, _):
    return data


def _resolve_patterns(data, pattern_map):
    resolve_functions = {dict: _resolve_patterns_dict,
                         str: _resolve_patterns_str,
                         list: _resolve_patterns_list}
    return resolve_functions.get(type(data), _resolve_preserve)(data, pattern_map)


class Config:
    def __init__(self, plugin_path, doc_path, config_file_path):
        import json
        self.plugin_path = plugin_path
        self.doc_path = doc_path
        with open(config_file_path, "r") as f:
            try:
                raw_data = json.load(f)
                self.config_data = _resolve_patterns(raw_data, {'${PLUGIN_ROOT}': plugin_path,
                                                                '${PLUGIN_DOC_ROOT}': doc_path,
                                                                '${PLATFORM_EXE_EXTENSION}': _platform_bin_suffix})
            except json.JSONDecodeError:
                logger.error('Failed to parse config file {}'.format(config_file_path))
                raise
    def getFullConfigData(self):
        return self.config_data

    def getPluginPath(self):
        return self.plugin_path

    def getDocPath(self):
        return self.doc_path

    def _getConfigKey(self, key, expected_type):
        d = self.config_data
        for k in key:
            d = d.get(k, None)
            if d is None:
                raise ConfigException('Key: {} is not in configuration'.format('/'.join(key)))
        if expected_type and not isinstance(d, expected_type):
            raise ConfigException('Key: {} is not of expected type {}'.format('/'.join(key), expected_type))
        return d

    def getMaterialXStdModuleNames(self):
        return self._getConfigKey(['materialx', 'std_modules'], list)

    def getMaterialXSearchPaths(self):
        return self._getConfigKey(['materialx', 'search_paths'], list)

    def getPainterExportPath(self):
        return self._getConfigKey(['paths', 'painter_export'], str)

    def getMaterialXExportPath(self):
        return self._getConfigKey(['paths', 'materialx_export'], str)

    def getMdlSubgraphPath(self):
        return self._getConfigKey(['paths', 'mdl_subgraph'], str)

    def getMaterialXSubgraphPath(self):
        return self._getConfigKey(['paths', 'mtlx_subgraph'], str)

    def getDesignerGlslPath(self):
        return self._getConfigKey(['paths', 'designer_glsl'], str)

    def getPainterTemplatePath(self):
        return self._getConfigKey(['paths', 'painter_template'], str)

    def getPluginMdlPath(self):
        return self._getConfigKey(['paths', 'plugin_mdl'], str)

    def getPluginMaterialXPath(self):
        return self._getConfigKey(['paths', 'plugin_mtlx'], str)

    def getTempPath(self):
        return self._getConfigKey(['paths', 'temp'], str)

    def getViewerBinary(self):
        return self._getConfigKey(['viewer', 'executable'], str)

    def getViewerParameters(self):
        return self._getConfigKey(['viewer', 'parameters'], list)