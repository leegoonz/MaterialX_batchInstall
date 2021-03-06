#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import logging
import os
import subprocess
import tempfile

import MaterialX as mx

import sdmatx

logger = logging.getLogger("SDMaterialX")


def showMatxView(doc,
                 matx_filename=None,
                 blocking=False):
    '''
    :param doc: The materialX document to show in the viewer
    :type doc: mx.Document
    :param matx_filename: The filename to write the document to. Will be
    autogenerated in temp directory if nothing is provided
    :type matx_filename: string or None
    :param blocking: Whether the window should hold up the thread it is
    called from until it's closed or if it should be non-modal.
    :type blocking: bool
    :return: None
    '''
    matx_view = sdmatx.getMatXViewBin()
    parameters = sdmatx.getMatXViewParameters()
    if matx_filename is None:
        # Generate a temp file and close it so it can be overwritten
        with tempfile.NamedTemporaryFile(suffix='.mtlx') as matx_file:
            matx_filename = matx_file.name

    mx.writeToXmlFile(doc, matx_filename)

    def resolve_param(p):
        pp = p.replace('${SRC_DOC}', matx_filename)
        return pp.replace(';', mx.PATH_LIST_SEPARATOR)
    resolved_params = [resolve_param(p) for p in parameters]

    cmd = [matx_view] + resolved_params
    logger.info(' '.join([piece.replace(' ', '\\ ') for piece in cmd]))
    p = subprocess.Popen(cmd)
    if blocking:
        # Wait for the process to finish before returning
        p.wait()
