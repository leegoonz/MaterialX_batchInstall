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
from functools import partial
from subprocess import CalledProcessError

from PySide2 import QtCore

logger = logging.getLogger("SDMaterialX")

_last_hash_digest = None


class PollMode(enum.Enum):
    DISABLED = 0
    MATERIAL = 1
    SELECTION = 2


def install_export_poll(ui_mgr, poll_rate, pollState):
    import sdmatx
    import substance_codegen
    import sd
    from sd.api.sdapiobject import APIException, SDApiError
    from sd.api.mdl.sdmdlgraph import SDMDLGraph
    logger.info('Installing export poll')

    def _isMaterialXGraph(graph):
        return sdmatx.isMtlxGraph(graph)

    def _hasChanged(graph, selected_node):
        import hashlib as sd_hashes

        # Keeping around for reload support for hashing for fast iteration
        from importlib import reload
        sd_hashes = reload(sd_hashes)

        global _last_hash_digest
        new_hash = sd_hashes.sha3_256()
        sdmatx.hash_graph(graph, new_hash)
        if selected_node:
            # Hash the selected node to trigger updates
            # when changing selection too
            new_hash.update(selected_node.getIdentifier().encode('utf-8'))
        new_digest = new_hash.hexdigest()
        if new_digest != _last_hash_digest:
            # print('mismatching hashes old: %s, old: %s' % (_last_hash_digest,
            #                                                new_digest))
            _last_hash_digest = new_digest
            return True
        return False

    def _exportGraph(graph, selected_node, pollState):
        current_package = sdmatx.getPackageFromResource(graph)
        material_name = graph.getIdentifier()
        try:
            mtlx_document = None
            if not selected_node:
                mtlx_document = \
                    sdmatx.mdl2mtlx_material(graph,
                                             material_name=material_name,
                                             sd_package=current_package,
                                             materialx_searchpaths=
                                             sdmatx.getMatxSearchPathString())
            else:
                mtlx_document = \
                    sdmatx.mdl2mtlx_custom_root(graph,
                                                node_name=material_name,
                                                sd_package=current_package,
                                                materialx_searchpaths=
                                                sdmatx.getMatxSearchPathString(),
                                                custom_root=selected_node)
            # Designer doesn't support sRGB samplers so add explicit gamma
            # to linear conversions on affected nodes
            sdmatx.convertSRGBToLinear(mtlx_document,
                                       sdmatx.getMatxSearchPathString())

            glslfx_output_files = sdmatx.getGLSLFXOutputFiles(mtlx_document)

            substance_codegen.mtlx2GLSLFX(
                mtlx_document,
                glslfx_output_files['glsl_output'],
                glslfx_output_files['glslfx_output'],
                glslfx_output_files['glslfx_template'],
                sdmatx.getMatxSearchPathList(),
                root_material=material_name,
                force_constants=True)

            sdmatx.reloadViewport(glslfx_output_files['glslfx_output'])
            pollState.status_bar.set_status(True)
            return
        except sdmatx.UnsupportedMDLType as e:
            error_message = sdmatx.isKnownMDLIssue(e)
            if error_message:
                logger.error('Failed to convert MaterialX to MDL')
                pollState.status_bar.set_status(False, 'Failed to convert MaterialX to MDL', error_message)
                logger.error(error_message)
            else:
                logger.error('Failed to convert MaterialX to MDL')
                pollState.status_bar.set_status(False, 'Failed to convert MaterialX to MDL', str(e))
                logger.error(str(e))
        except sdmatx.MDLToMaterialXException as e:
            logger.error('Failed to convert MaterialX to MDL')
            pollState.status_bar.set_status(False, 'Failed to convert MaterialX to MDL', str(e))
            logger.error(str(e))
        except CalledProcessError as e:
            logger.error('GLSLFX processing failed')
            pollState.status_bar.set_status(False, 'GLSLFX processing failed', str(e))
            logger.error(str(e))
        except BaseException as e:
            logger.error('General error')
            pollState.status_bar.set_status(False, 'General Error', str(e))
            logger.error(str(e))

        # This code sets the error viewport for all exceptions but not for
        # success
        try:
            root_name = 'standard_surface'
            if not selected_node:
                root_node = sdmatx.findRootNode(graph)
                if root_node:
                    if root_node.getDefinition() is not None:
                        root_name = root_node.getDefinition().getId()
            shader_name = root_name.split('::')[-1]
            shader_path = sdmatx.getGLSLFXOutputShaderFromUbershader(shader_name)
            sdmatx.setErrorViewport(shader_path)
        except BaseException as e:
            logger.error(str(e))

    def _pollFunction(pollState):
        app = sd.getContext().getSDApplication()
        ui_mgr = app.getQtForPythonUIMgr()
        try:
            # Make sure there is at least a single graph to avoid
            # littering log with exceptions
            if len(app.getPackageMgr().getPackages()) > 0:
                currentGraph = ui_mgr.getCurrentGraph()
                if (pollState.mode != PollMode.DISABLED) and \
                        isinstance(currentGraph, SDMDLGraph):
                    # Heuristically check if it's a materialX graph at all
                    if not _isMaterialXGraph(currentGraph):
                        return
                    selected_node = None
                    if pollState.mode == PollMode.SELECTION:
                        selected_nodes = ui_mgr.getCurrentGraphSelection()
                        if len(selected_nodes) > 0:
                            selected_node = selected_nodes[0]
                    # Compare it with the previous export in a nimble way
                    if not _hasChanged(currentGraph, selected_node):
                        return
                    # Export and reset the viewport
                    _exportGraph(currentGraph, selected_node, pollState)
        except APIException as e:
            if e.mErrorCode == SDApiError.InvalidArgument:
                # This is what happens if we don't have any graphs at all
                pass
            else:
                raise e

    timer = QtCore.QTimer(ui_mgr.getMainWindow())
    timer.connect(timer, QtCore.SIGNAL("timeout()"), partial(_pollFunction,
                                                             pollState))
    timer.setInterval(poll_rate)
    timer.start(poll_rate)


def uninstall_export_poll(timer):
    logger.info('Uninstalling export poll')
    del timer
