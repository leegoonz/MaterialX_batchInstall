#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import logging

from sd.api.mdl.sdmdlgraphdefinition import *
from .icon import getMaterialXIconPath

logger = logging.getLogger("SDMaterialX")


class MaterialXEditor:
    @staticmethod
    def init():
        logger.info('Initializing MaterialX')
        from sdmatx import getMdlDirectories
        context = sd.getContext()
        sdApp = context.getSDApplication()

        # Add MDL Root path
        # currentScriptAbsPath = os.path.abspath(os.path.split(__file__)[0])
        mdlRootPaths = getMdlDirectories()
        for p in mdlRootPaths:
            sdApp.getModuleMgr().addRootPath('mdl', p)

        # Create new Graph definition
        graphDefinitionMgr = sdApp.getSDGraphDefinitionMgr()
        assert (graphDefinitionMgr)

        # Add Graph Definition if not already exist
        sdGraphDefinitionId = 'matx'
        sdGraphDefinition = graphDefinitionMgr.getGraphDefinitionFromId(sdGraphDefinitionId)
        if not sdGraphDefinition:
            sdGraphDefinition = SDMDLGraphDefinition.sNew('matx')
            assert (sdGraphDefinition)
            assert (sdGraphDefinition.getId() == sdGraphDefinitionId)
            sdGraphDefinition.setLabel('MaterialX Graph')
            sdGraphDefinition.setIconFile(getMaterialXIconPath())
            # Add the new graph definition
            graphDefinitionMgr.addGraphDefinition(sdGraphDefinition)
        else:
            assert (sdGraphDefinition.getId() == sdGraphDefinitionId)
        logger.info('Adding MaterialX Editor')
        # Add some Node definition to teh graph definition
        sdModuleMgr = sdApp.getModuleMgr()
        sdModules = sdModuleMgr.getModules()
        selectedDefinitions = []
        selectedTypes = []
        for sdModule in sdModules:
            sdModuleId = sdModule.getId()

            logger.info('Module: ' + sdModuleId)
            # Discard non 'mdl' modules
            if not sdModuleId.startswith('mdl::'):
                continue

            for sdType in sdModule.getTypes():
                sdTypeId = sdType.getId()
            for sdDefinition in sdModule.getDefinitions():
                sdDefinitionId = sdDefinition.getId()

            # Add some definitions from the MDL 'builtin' module
            if sdModuleId == 'mdl::<builtins>':
                # Add some base types
                baseTypes = ['bool',
                             'int',
                             'ColorRGB',
                             'float', 'float2', 'float3', 'float4',
                             'string',
                             'mdl::texture_2d'
                             ]
                for sdType in sdModule.getTypes():
                    sdTypeId = sdType.getId()
                    if sdTypeId in baseTypes:
                        # Add some base Types
                        selectedTypes.append(sdType)
                    elif sdTypeId.startswith('matrix<float>[3][3]') or \
                            sdTypeId.startswith('matrix<float>[4][4]'):
                        # Add matrices
                        selectedTypes.append(sdType)

            # Add all definitions from the MDL module 'mtlx'
            if sdModuleId.startswith('mdl::mtlx'):
                for sdDefinition in sdModule.getDefinitions():
                    selectedDefinitions.append(sdDefinition)

        # Add the selected types
        for sdType in selectedTypes:
            logger.debug('[%s] Adding Type "%s"' % (sdGraphDefinition.getId(), sdType.getId()))
            sdGraphDefinition.addType(sdType)

        # Add the selected node definitions
        for definition in selectedDefinitions:
            existingNodeDefinition = sdGraphDefinition.getDefinitionFromId(definition.getId())
            if existingNodeDefinition:
                sdGraphDefinition.removeDefinition(existingNodeDefinition)

            logger.debug('[%s] Adding Definition "%s"' % (sdGraphDefinition.getId(), definition.getId()))
            sdGraphDefinition.addDefinition(definition)

        logger.info('Done adding MaterialX Editor\n\n')

    @staticmethod
    def uninit():
        pass
