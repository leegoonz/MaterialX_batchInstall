#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from PySide2 import QtWidgets


class MatxViewDialog(QtWidgets.QDialog):
    """
    :param uiMgr: Ui manager to build the dialog on
    :type uiMgr: sd.api.qtforpythonuimgrwrapper.QtForPythonUIMgrWrapper
    """

    def __init__(self, uiMgr):
        from sd import getContext
        from sdmatx import getPackageFromResource
        super(MatxViewDialog, self).__init__(parent=uiMgr.getMainWindow())

        self.current_graph = uiMgr.getCurrentGraph()
        self.current_package = getPackageFromResource(self.current_graph) if \
            self.current_graph else None

        pkg_mgr = getContext().getSDApplication().getPackageMgr()
        self.all_graphs = self._getAllCompGraphs(pkg_mgr)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.comp_graph_to_export = QtWidgets.QComboBox()
        for g, _ in self.all_graphs.items():
            self.comp_graph_to_export.addItem(g)
        if self.current_package:
            for id, (g, p) in self.all_graphs.items():
                if p.getFilePath() == self.current_package.getFilePath():
                    self.comp_graph_to_export.setCurrentText(id)
                    break

        sel_layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(self)
        self.label.setText('Texture Graph')
        sel_layout.addWidget(self.label)
        sel_layout.addWidget(self.comp_graph_to_export)
        self.layout.addLayout(sel_layout)

        # Add ok/cancel buttons
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

        self.setMinimumSize(300, 0)

    def getState(self):
        selected = self.comp_graph_to_export.currentText()
        comp_graph_to_export = self.all_graphs.get(selected, None)

        return {
            'comp_graph_to_export': comp_graph_to_export,
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
