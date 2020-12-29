#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from PySide2 import QtWidgets, QtCore


class StatusBar(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(StatusBar, self).__init__(parent)
        # Create widgets
        ok_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        fail_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)
        self.ok_pixmap = ok_icon.pixmap(QtCore.QSize(16, 16))
        self.fail_pixmap = fail_icon.pixmap(QtCore.QSize(16, 16))
        self.status_light = QtWidgets.QLabel()
        self.status_light.setPixmap(self.ok_pixmap)
        self.status_line = QtWidgets.QLabel('')
        # Create layout and add widgets
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.status_light)
        layout.addWidget(self.status_line)
        # Set dialog layout
        self.setLayout(layout)

    def set_status(self, success, message='', detailed_message=''):
        self.status_light.setPixmap(self.ok_pixmap if success else self.fail_pixmap)
        self.status_line.setText(message)
        self.status_line.setToolTip(detailed_message)
