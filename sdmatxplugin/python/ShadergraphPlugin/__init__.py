#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

_graphViewCreatedCallbackID = 0
_pollHandle = None

from .MaterialXEditor import *
from .exportpoll import install_export_poll, uninstall_export_poll, PollMode

logger = logging.getLogger("SDMaterialX")


class PollState:
    def __init__(self):
        self.mode = PollMode.MATERIAL
        self.status_bar = None


_pollState = PollState()


def initializeShaderGraph():
    import sd

    MaterialXEditor.init()
    app = sd.getContext().getSDApplication()
    # register UI plugins
    uiMgr = app.getQtForPythonUIMgr()
    if uiMgr:
        from . import materialxToolbar
        import functools
        global _graphViewCreatedCallbackID
        logger.info("Registering materialx toolbar")
        _graphViewCreatedCallbackID = uiMgr.registerGraphViewCreatedCallback(
            functools.partial(
                materialxToolbar.onNewGraphViewCreated, uiMgr=uiMgr,
                pollState=_pollState))
        _pollHandle = install_export_poll(uiMgr, 1000, _pollState)


def uninitializeShaderGraph():
    # remove mdl path
    import sd

    MaterialXEditor.uninit()
    app = sd.getContext().getSDApplication()

    # unregister UI plugins
    uiMgr = app.getQtForPythonUIMgr()
    if uiMgr:
        global _graphViewCreatedCallbackID
        global _pollHandle
        logger.info("Clearing materialx toolbar")
        uiMgr.unregisterCallback(_graphViewCreatedCallbackID)
        uninstall_export_poll(_pollHandle)
