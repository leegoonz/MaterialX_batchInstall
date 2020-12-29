#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import functools
import logging
import os
import subprocess

from PySide2 import QtGui, QtWidgets, QtCore

import sd
import sdmatx
import substance_codegen

from .icon import getMaterialXIconPath

logger = logging.getLogger("SDMaterialX")

from .exportpoll import PollMode
from .statusbar import StatusBar


class MaterialXToolbar(QtWidgets.QToolBar):
    def __init__(self, graphViewID, uiMgr, pollState):
        super(MaterialXToolbar, self).__init__(parent=uiMgr.getMainWindow())

        self.setObjectName("allegorithmic.com.materialXexport")

        self.__graphViewID = graphViewID
        self.__uiMgr = uiMgr

        act = self.addAction("Update GL")
        act.setShortcut(QtGui.QKeySequence('H'))
        act.setToolTip(self.tr("Export MaterialX and reload the viewport"))
        act.triggered.connect(self.__onMaterialXExport)

        view_act = self.addAction('View')
        view_act.setToolTip("View material in MaterialXView")
        view_act.triggered.connect(self.__onMaterialXView)

        subgraph_act = self.addAction('Export Subgraphs')
        subgraph_act.setToolTip("Exports subgraphs from the current document")
        subgraph_act.triggered.connect(self.__onExportSubgraphs)

        export_mtlx_act = self.addAction('Export Mtlx')
        export_mtlx_act.setToolTip("Exports materialx graph and its "
                                   "dependencies from the "
                                   "current graph")
        export_mtlx_act.triggered.connect(self.__onExportMtlx)

        export_painter_act = self.addAction('Export Painter')
        export_painter_act.setToolTip("Exports materialx graph to a painter "
                                      "compatible glsl file")
        export_painter_act.triggered.connect(self.__onExportPainter)

        # Set up poll state button/menu
        self.pollState = pollState
        self.enableAutoExport = QtWidgets.QToolButton(self)
        self.enableAutoExport.setAutoRaise(True)
        self.enableAutoExport.setStyleSheet(
            'QToolButton {background-color: #3E0F0F;}')
        # Menu items for selecting viewport state
        disabled_action = QtWidgets.QAction('No Preview', self)
        disabled_action.triggered.connect(
            functools.partial(self.__onPollStateChanged, PollMode.DISABLED))
        material_action = QtWidgets.QAction('Material Preview', self)
        material_action.triggered.connect(
            functools.partial(self.__onPollStateChanged, PollMode.MATERIAL))
        selection_action = QtWidgets.QAction('Selection Preview', self)
        selection_action.triggered.connect(
            functools.partial(self.__onPollStateChanged, PollMode.SELECTION))

        # Add action to set the name of the button to represent the selection
        # and set the state to be aligned with the default state
        self.enableAutoExport.triggered.connect(
            self.enableAutoExport.setDefaultAction)
        self.__onPollStateChanged(PollMode.MATERIAL)

        self.enableAutoExport.setDefaultAction(material_action)

        menu = QtWidgets.QMenu(self.enableAutoExport)
        menu.addAction(disabled_action)
        menu.addAction(material_action)
        menu.addAction(selection_action)

        self.enableAutoExport.setMenu(menu)
        self.enableAutoExport.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.addWidget(self.enableAutoExport)
        self.status_bar = StatusBar()
        self.addWidget(self.status_bar)
        self.pollState.status_bar = self.status_bar

    def tooltip(self):
        return self.tr("MaterialX Tools")

    def __onMaterialXExport(self):
        self.__runExportViewport(sd.getContext())

    def __onMaterialXView(self):
        self.__run_view(sd.getContext())

    def __onExportSubgraphs(self):
        self.__run_export_subgraphs(sd.getContext())

    def __onExportMtlx(self):
        self.__run_export_mtlx(sd.getContext())

    def __onExportPainter(self):
        self.__runExportPainter(sd.getContext())

    def __onPollStateChanged(self, newState):
        self.pollState.mode = newState

    def __basicDialog(self, basic_message, detail_message):
        dialog = QtWidgets.QMessageBox(self.__uiMgr.getMainWindow())
        dialog.setText(basic_message)
        dialog.setInformativeText(detail_message)
        return dialog

    def __errorDialog(self, basic_error, detail_error):
        error_dialog = self.__basicDialog(basic_error, detail_error)
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.exec()

    def __successDialog(self, basic_message, detail_message):
        success_dialog = self.__basicDialog(basic_message, detail_message)
        success_dialog.setIcon(QtWidgets.QMessageBox.Information)
        success_dialog.exec()

    def __export_textures(self, mtlx_document, graph, target_directory, doc_root=None):
        all_image_nodes = sdmatx.findImageNodes(mtlx_document)
        texture_export_map = {}
        for image_node in all_image_nodes:
            usage = image_node.getAttribute('GLSLFX_usage')
            if usage:
                texture_export_map[usage] = os.path.join(target_directory, usage + '.png')

        if len(texture_export_map) > 0:
            # Make the texture export dir if there are
            # textures to export
            if not os.path.isdir(target_directory):
                os.makedirs(target_directory)
            # Export all files
            exported_maps = sdmatx.exportOutputByUsage(graph, texture_export_map)
            # Bind texture files to the filename property of the nodes
            for image_node in all_image_nodes:
                usage = image_node.getAttribute('GLSLFX_usage')
                if usage:
                    texture_file = exported_maps.get(usage, None)
                    if texture_file is None:
                        logger.warning('No texture found for usage: {}'.format(usage))
                    else:
                        final_file = os.path.relpath(texture_file, doc_root) if doc_root else texture_file
                        # Make sure paths uses / on windows machines for consistency 
                        if os.sep != '/':
                            final_file = final_file.replace(os.sep, '/')
                        image_node.setParameterValue('file', final_file, 'filename')

    def __runExportViewport(self, aContext):
        current_graph = \
            aContext.getSDApplication().getUIMgr().getCurrentGraph()
        current_package = sdmatx.getPackageFromResource(current_graph)
        material_name = current_graph.getIdentifier()
        try:
            mtlx_document = sdmatx.mdl2mtlx_material(
                current_graph,
                material_name=material_name,
                sd_package=current_package,
                materialx_searchpaths=
                sdmatx.getMatxSearchPathString())
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
                root_material=material_name)
            sdmatx.reloadViewport(glslfx_output_files['glslfx_output'])
            return
        except sdmatx.UnsupportedMDLType as e:
            error_message = sdmatx.isKnownMDLIssue(e)
            if error_message is not None:
                self.__errorDialog('Known MaterialX Graph issue',
                                   error_message)
            else:
                self.__errorDialog('MDL to MaterialX Conversion Error',
                                   str(e))
        except sdmatx.MDLToMaterialXException as e:
            self.__errorDialog('MDL to MaterialX Conversion Error',
                               str(e))
        except subprocess.CalledProcessError as e:
            self.__errorDialog('MaterialX to GLSL conversion error',
                               str(e))
        except BaseException as e:
            self.__errorDialog('General Error',
                               str(e))

    def __run_view(self, aContext):
        import ShadergraphPlugin.matxviewdialog as matx_export
        import tempfile
        logger.info('launching materialx view')
        view_dialog = matx_export.MatxViewDialog(
            aContext.getSDApplication().getQtForPythonUIMgr())
        view_dialog.setModal(True)
        view_dialog.show()
        result = view_dialog.exec()
        if result == 1:
            state = view_dialog.getState()
            current_graph = \
                aContext.getSDApplication().getUIMgr().getCurrentGraph()
            current_package = sdmatx.getPackageFromResource(current_graph)
            package_dir = os.path.dirname(current_package.getFilePath())
            material_name = current_graph.getIdentifier()
            try:
                progress = QtWidgets.QProgressDialog("Exporting files...", None, 0, 3, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()
                progress.setValue(0)
                mtlx_document = sdmatx.mdl2mtlx_material(
                    current_graph,
                    material_name=material_name,
                    sd_package=current_package,
                    materialx_searchpaths=sdmatx.getMatxSearchPathString(),
                    resource_root=package_dir)
                progress.setValue(1)

                # Export the textures for the document
                export_data = state['comp_graph_to_export']
                if export_data:
                    texture_dir = tempfile.mkdtemp(prefix='matx_tex')
                    texture_graph, texture_package = export_data
                    if texture_graph != '':
                        self.__export_textures(mtlx_document, texture_graph, texture_dir)
                progress.setValue(2)

                sdmatx.showMatxView(mtlx_document)
                progress.setValue(3)
            except sdmatx.UnsupportedMDLType as e:
                error_message = sdmatx.isKnownMDLIssue(e)
                if error_message is not None:
                    self.__errorDialog('Known MaterialX Graph issue',
                                       error_message)
                else:
                    self.__errorDialog('MDL to MaterialX Conversion Error',
                                       str(e))
            except sdmatx.MDLToMaterialXException as e:
                self.__errorDialog('MDL to MaterialX Conversion Error',
                                   str(e))
            except BaseException as e:
                self.__errorDialog('General Error',
                                   str(e))
            finally:
                progress.close()
        view_dialog.close()

    def __run_export_subgraphs(self, aContext):
        import ShadergraphPlugin.exportsubgraphdialog as esg
        import importlib
        importlib.reload(esg)
        subgraph_dialog = esg.ExportSubgraphDialog(
            aContext.getSDApplication().getQtForPythonUIMgr())
        subgraph_dialog.setModal(True)
        subgraph_dialog.show()
        result = subgraph_dialog.exec()
        if result == 1:
            result, current_package = subgraph_dialog.getState()
            export_result = esg.exportSubgraphs(result, current_package)
            msg = ''
            had_error = False
            for graph_name, status in export_result.items():
                if status['result']:
                    msg += '{}: Success\n'.format(graph_name)
                else:
                    msg += '{}: Failed\n'.format(graph_name)
                    msg += str('{}\n\n'.format(status['exception']))
                    had_error = True
            if had_error:
                logger.error(msg)
                self.__errorDialog('Export Error', msg)
            else:
                logger.info(msg)
                self.__successDialog('Successfully exported', msg)
        subgraph_dialog.close()

    def __run_export_mtlx(self, aContext):
        import ShadergraphPlugin.exportmtlxdialog as emx
        import importlib
        import MaterialX as mx
        importlib.reload(emx)
        export_mtlx_dialog = emx.ExportMaterialXDialog(
            aContext.getSDApplication().getQtForPythonUIMgr())
        export_mtlx_dialog.setModal(True)
        export_mtlx_dialog.show()
        result = export_mtlx_dialog.exec()
        if result == 1:
            # export document
            state = export_mtlx_dialog.getState()
            try:
                progress = QtWidgets.QProgressDialog("Exporting Graph...", None, 0, 3, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()
                progress.setValue(0)

                graph = state['graph']
                package = state['package']
                package_dir = os.path.dirname(package.getFilePath())
                target_file = state['export_path']
                mtlx_document = sdmatx.mdl2mtlx_material(
                    graph,
                    material_name=graph.getIdentifier(),
                    sd_package=package,
                    materialx_searchpaths=
                    sdmatx.getMatxSearchPathString(),
                    resource_root=package_dir)
                progress.setValue(1)
                target_dir = os.path.dirname(target_file)
                if not os.path.isdir(target_dir):
                    os.makedirs(target_dir)

                # Export textures
                export_textures = state['export_images']
                if export_textures:
                    texture_dir = os.path.join(target_dir, 'textures')
                    texture_graph, texture_package = state['comp_graph_to_export']
                    self.__export_textures(mtlx_document, texture_graph, texture_dir, os.path.dirname(target_file))
                    progress.setValue(2)

                mx.writeToXmlFile(mtlx_document, target_file)
                if state['export_dependencies']:
                    sdmatx.exportDependentFiles(os.path.dirname(target_file),
                                                mtlx_document,
                                                sdmatx.getMatxSearchPathString(),
                                                ignore_modules=set(sdmatx.getStdlibMtlxModules()) if not state['export_stdlib'] else set())

                if state['show_folder']:
                    export_url = QtCore.QUrl.fromLocalFile(
                        os.path.dirname(target_file))
                    QtGui.QDesktopServices.openUrl(export_url)
                progress.setValue(3)
            except sdmatx.UnsupportedMDLType as e:
                error_message = sdmatx.isKnownMDLIssue(e)
                if error_message is not None:
                    self.__errorDialog('Known MaterialX Graph issue',
                                       error_message)
                else:
                    self.__errorDialog('MDL to MaterialX Conversion Error',
                                       str(e))
            except sdmatx.MDLToMaterialXException as e:
                self.__errorDialog('MDL to MaterialX Conversion Error',
                                   str(e))
            except subprocess.CalledProcessError as e:
                self.__errorDialog('MaterialX to GLSL conversion error',
                                   str(e))
            except BaseException as e:
                self.__errorDialog('General Error',
                                   str(e))
            finally:
                progress.close()
        export_mtlx_dialog.close()

    def __runExportPainter(self, aContext):
        current_graph = \
            aContext.getSDApplication().getUIMgr().getCurrentGraph()
        current_package = sdmatx.getPackageFromResource(current_graph)
        material_name = current_graph.getIdentifier()
        try:
            mtlx_document = sdmatx.mdl2mtlx_material(
                current_graph,
                material_name=material_name,
                sd_package=current_package,
                materialx_searchpaths=sdmatx.getMatxSearchPathString())
            output_file = os.path.join(sdmatx.getUserPainterDirectory(),
                                       material_name + '.glsl')
            substance_codegen.mtlx2PainterGLSL(
                mtlx_document,
                output_file,
                sdmatx.getMatxSearchPathList(),
                root_material=material_name,
                painter_template_directory=sdmatx.getPainterTemplateDirectory())
            return
        except sdmatx.UnsupportedMDLType as e:
            error_message = sdmatx.isKnownMDLIssue(e)
            if error_message is not None:
                self.__errorDialog('Known MaterialX Graph issue',
                                   error_message)
            else:
                self.__errorDialog('MDL to MaterialX Conversion Error',
                                   str(e))
        except sdmatx.MDLToMaterialXException as e:
            self.__errorDialog('MDL to MaterialX Conversion Error',
                               str(e))
        except subprocess.CalledProcessError as e:
            self.__errorDialog('MaterialX to Painter GLSL conversion error',
                               str(e))
        except BaseException as e:
            self.__errorDialog('General Error',
                               str(e))


def onNewGraphViewCreated(graphViewID, uiMgr, pollState):
    logger.info('Adding toolbar')
    from sd.api.mdl.sdmdlgraph import SDMDLGraph
    graph = uiMgr.getGraphFromGraphViewID(graphViewID)
    if isinstance(graph, SDMDLGraph):
        icon = QtGui.QIcon(getMaterialXIconPath())
        toolbar = MaterialXToolbar(graphViewID,
                                   uiMgr,
                                   pollState)
        uiMgr.addToolbarToGraphView(
            graphViewID,
            toolbar,
            icon=icon,
            tooltip=toolbar.tooltip())
    else:
        pollState.active = False
