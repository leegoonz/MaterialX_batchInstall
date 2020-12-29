#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from .paths import getDataDirectory, \
    getMatxDocRoot, \
    getMdlDirectories, \
    getShaderDirectory, \
    getTempDirectory, \
    getMatXViewBin, \
    getMatXViewParameters, \
    getInstallDirectory, \
    getMatxSearchPathList, \
    getMatxSearchPathString, \
    makeMtlxPathString, \
    makeConsistentPath, \
    getUserPluginDataDirectory, \
    getUserMaterialXDocDirectory, \
    getUserMaterialXSubgraphDirectory, \
    getUserMdlDirectory, \
    getMdlSubgraphDirectory, \
    getDefaultMaterialXExportDirectory, \
    getUserPainterDirectory, \
    getPainterTemplateDirectory, \
    getStdlibMtlxModules, \
    initPaths
from .utilities import getGLSLFXOutputFiles, \
    getPackageFromResource, \
    reloadViewport, \
    extractReferenceUid, \
    setErrorViewport, \
    isMtlxGraph, \
    getGLSLFXOutputShaderFromUbershader, \
    isKnownMDLIssue
from .sd_hashes import hash_graph
from .mdl2mtlx import \
    mdl2mtlx_material, \
    mdl2mtlx_subgraph, \
    mdl2mtlx_custom_root, \
    exportDependentFiles, \
    forwardOutputs, \
    convertSRGBToLinear, \
    MDLToMaterialXException, \
    MissingMaterialXType,\
    UnsupportedMDLType, \
    InvalidGraphType,\
    findImageNodes, \
    findRootNode

from .mtlx2mdl import mtlx2mdl_library, \
    mtlx2mdl_shared, \
    MDLGenerationException
from .matx_view import showMatxView
from .benchmark import perf_measure, dump_benchmarks, Benchmark
from .export import exportOutputByUsage
from .modules import getMdlSourceHash, hashMtlxDocsForModule
from .config import Config, ConfigException
try:
    from .version import get_version_string
except ImportError:
    def get_version_string():
        return 'development_build'
