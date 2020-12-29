#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import collections
import logging
import os

from PySide2 import QtWidgets

logger = logging.getLogger("SDMaterialX")


def _makeModuleName(package):
    import sdmatx
    package_file_root = os.path.splitext(os.path.basename(
        package.getFilePath()))[0]
    mdl_user_module_name = os.path.join('user', package_file_root)
    return sdmatx.makeConsistentPath(mdl_user_module_name)


class ExportSubgraphDialog(QtWidgets.QDialog):
    """
    :param uiMgr: Ui manager to build the dialog on
    :type uiMgr: sd.api.qtforpythonuimgrwrapper.QtForPythonUIMgrWrapper
    """

    def __init__(self, uiMgr):
        from sdmatx import getPackageFromResource
        super(ExportSubgraphDialog, self).__init__(parent=uiMgr.getMainWindow())

        current_graph = uiMgr.getCurrentGraph()
        self.current_package = getPackageFromResource(current_graph) if \
            current_graph else None
        self.package_mtlx_graphs = self._getAllMDLGraphs(self.current_package)
        self.layout = QtWidgets.QGridLayout()
        self.export_checkboxes = []

        idx = 0
        if len(self.package_mtlx_graphs) == 0:
            label = QtWidgets.QLabel()
            label.setText('No subgraphs to export')
            self.layout.addWidget(label, idx, 0)
            idx += 1
        else:
            label = QtWidgets.QLabel()
            module_name = _makeModuleName(self.current_package)
            label.setText('Module Name: {}.mdl'.format(module_name))
            self.layout.addWidget(label, idx, 0)
            idx += 1

            # Add combobox for selecting the graph to import from
            for name, graph in self.package_mtlx_graphs.items():
                cb = QtWidgets.QCheckBox()
                cb.setText(name)
                cb.setChecked(True)
                self.layout.addWidget(cb, idx, 0)
                self.export_checkboxes.append(cb)
                idx += 1

            frame = QtWidgets.QFrame()
            frame.setFrameShape(frame.HLine)
            frame.setFrameShadow(frame.Sunken)
            self.layout.addWidget(frame, idx, 0)
            idx += 1

            def _setAllCheckboxes(new_state):
                for cb in self.export_checkboxes:
                    cb.setChecked(new_state)

            self.global_checkbox = QtWidgets.QCheckBox()
            self.global_checkbox.setText('Select/Deselect All')
            self.global_checkbox.setChecked(True)
            self.global_checkbox.stateChanged.connect(_setAllCheckboxes)
            self.layout.addWidget(self.global_checkbox, idx, 0)
            idx += 1
        # Add ok/cancel buttons
        self.setLayout(self.layout)
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox, idx, 0)

    def _getAllMDLGraphs(self, package):
        from sd.api.mdl.sdmdlgraph import SDMDLGraph
        all_graphs = {}
        for res in package.getChildrenResources(True):
            if isinstance(res, SDMDLGraph):
                all_graphs[res.getIdentifier()] = res
        return all_graphs

    def getState(self):
        result = []
        for cb in self.export_checkboxes:
            if cb.isChecked():
                result.append(self.package_mtlx_graphs[cb.text()])
        return (result, self.current_package)


def exportSubgraphs(graphs, package):
    import sdmatx
    import MaterialX as mx
    results = collections.OrderedDict()
    mdl_user_module_name = _makeModuleName(package)
    exported_file = False
    for g in graphs:
        name = g.getIdentifier()
        try:
            mtlx_doc = sdmatx.mdl2mtlx_subgraph(
                g,
                name,
                package,
                sdmatx.getMatxSearchPathString(),
                os.path.dirname(package.getFilePath()))
            val_res, val_log = mtlx_doc.validate()
            if not val_res:
                logger.error(val_log)
            else:
                logger.debug('validation successful')
            mtlx_dir = os.path.join(sdmatx.getUserMaterialXDocDirectory(),
                                    mdl_user_module_name)
            if not os.path.isdir(mtlx_dir):
                os.makedirs(mtlx_dir)
            mtlx_path = os.path.join(mtlx_dir,
                                     name + '.mtlx')

            mx.writeToXmlFile(mtlx_doc, mtlx_path)
            exported_file = True
            results[name] = {
                'result': True,
                'exception': None
            }
        except BaseException as e:
            results[name] = {
                'result': False,
                'exception': e
            }
    if exported_file:
        try:
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
        except BaseException as e:
            results[mdl_user_module_name + '.mdl'] = {
                'result': False,
                'exception': e
            }
    return results
