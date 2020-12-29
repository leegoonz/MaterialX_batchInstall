#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os

from PySide2 import QtWidgets

import sdmatx


class _FileSelector(QtWidgets.QWidget):
    def __init__(self, parent, default_filename, extensions):
        super(_FileSelector, self).__init__(parent=parent)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.label = QtWidgets.QLabel(self)
        self.label.setText('Output')
        layout.addWidget(self.label)
        self.filename = QtWidgets.QLineEdit(self)
        self.filename.setText(default_filename)

        layout.addWidget(self.filename)
        self.file_select_button = QtWidgets.QPushButton()
        self.file_select_button.setText('Select')

        def _showFileDialog():
            file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export mtlx",
                default_filename,
                "Mtlx Documents Files ({})".format(extensions))
            if file_name:
                self.filename.setText(file_name)

        self.file_select_button.clicked.connect(_showFileDialog)
        layout.addWidget(self.file_select_button)

    def getSelectedFile(self):
        return self.filename.text()


class ExportMaterialXDialog(QtWidgets.QDialog):
    """
    :param uiMgr: Ui manager to build the dialog on
    :type uiMgr: sd.api.qtforpythonuimgrwrapper.QtForPythonUIMgrWrapper
    """

    def __init__(self, uiMgr):
        from sd import getContext
        from sdmatx import getPackageFromResource
        super(ExportMaterialXDialog, self).__init__(parent=uiMgr.getMainWindow())

        self.current_graph = uiMgr.getCurrentGraph()
        self.current_package = getPackageFromResource(self.current_graph) if \
            self.current_graph else None

        default_name = self.current_graph.getIdentifier()
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.selector = _FileSelector(
            self,
            os.path.join(sdmatx.getDefaultMaterialXExportDirectory(),
                         default_name,
                         default_name + '.mtlx'),
            '*.mtlx')
        self.layout.addWidget(self.selector)

        self.dependencies_checkbox = QtWidgets.QCheckBox()
        self.dependencies_checkbox.setText('Export Dependencies')
        self.dependencies_checkbox.setChecked(True)
        self.layout.addWidget(self.dependencies_checkbox)

        self.stdlib_checkbox = QtWidgets.QCheckBox()
        self.stdlib_checkbox.setText('Export Stdlib')
        self.stdlib_checkbox.setChecked(False)
        self.layout.addWidget(self.stdlib_checkbox)

        self.export_bound_textures = QtWidgets.QCheckBox()
        self.export_bound_textures.setText('Export Bound Textures')
        self.export_bound_textures.setChecked(True)
        self.layout.addWidget(self.export_bound_textures)

        pkg_mgr = getContext().getSDApplication().getPackageMgr()
        self.all_graphs = self._getAllCompGraphs(pkg_mgr)

        self.comp_graph_to_export = QtWidgets.QComboBox()
        for g, _ in self.all_graphs.items():
            self.comp_graph_to_export.addItem(g)
        if self.current_package:
            for id, (g, p) in self.all_graphs.items():
                if p.getFilePath() == self.current_package.getFilePath():
                    self.comp_graph_to_export.setCurrentText(id)
                    break

        sel_layout = QtWidgets.QHBoxLayout()
        self.comp_label = QtWidgets.QLabel(self)
        self.comp_label.setText('Texture Graph')
        sel_layout.addWidget(self.comp_label)
        sel_layout.addWidget(self.comp_graph_to_export)
        self.layout.addLayout(sel_layout)

        def _toggle_graph_export(state):
            if state > 0:
                self.comp_graph_to_export.setEnabled(True)
            else:
                self.comp_graph_to_export.setEnabled(False)

        self.export_bound_textures.stateChanged.connect(_toggle_graph_export)

        self.show_folder = QtWidgets.QCheckBox()
        self.show_folder.setText('Show Export Folder')
        self.show_folder.setChecked(True)
        self.layout.addWidget(self.show_folder)

        # Add ok/cancel buttons
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

        self.setMinimumSize(700, 0)

    def getState(self):
        comp_graph_to_export = None
        if self.export_bound_textures.isChecked():
            selected = self.comp_graph_to_export.currentText()
            comp_graph_to_export = self.all_graphs.get(selected, None)

        return {
            'graph': self.current_graph,
            'package': self.current_package,
            'export_path': self.selector.getSelectedFile(),
            'export_dependencies': self.dependencies_checkbox.isChecked(),
            'export_stdlib' : self.stdlib_checkbox.isChecked(),
            'export_images': self.export_bound_textures.isChecked() and comp_graph_to_export,
            'comp_graph_to_export': comp_graph_to_export,
            'show_folder': self.show_folder.isChecked()
        }

    def _getAllCompGraphs(self, pkg_mgr):
        from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
        import collections
        all_pkg = pkg_mgr.getPackages()
        all_graphs = collections.OrderedDict()
        for pkg in all_pkg:
            for res in pkg.getChildrenResources(True):
                if isinstance(res, SDSBSCompGraph):
                    all_graphs[res.getIdentifier()] = (res, pkg)
        return all_graphs
