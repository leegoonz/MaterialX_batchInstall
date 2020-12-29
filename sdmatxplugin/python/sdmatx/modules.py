#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

# Defines handling of modules and paths associated with them
# for mdl and materialX
# A module in mdl is defined as a file with a path. By convention any module
# coming out of the system is located in the mtlx directory and it supports a
# hierarchy.
# MDL Example the MDL module mtlx/fruit/apple.mdl is represented by the
# module path fruit/apple
# A module in materialx is defined as all files in a directory. The same mdl
# module would have the following layout in MaterialX coming out of the system
# fruit/apple/*.mtlx meaning all files in the apple directory constitutes the
# apple module.
import logging
import os

import MaterialX as mx
from .paths import getMatxSearchPathList, \
    getMatxSearchPathString, \
    makeConsistentPath
import mx_utils 

logger = logging.getLogger("SDMaterialX")


class ModuleError(BaseException):
    pass


def moduleFromMdlNamespace(sd_node_id):
    function_namespace = sd_node_id.split('(')[0].split('::')
    if len(function_namespace) < 4 or \
            function_namespace[0] != 'mdl' or \
            function_namespace[1] != 'mtlx':
        raise ModuleError('Type: {} is not in a supported '
                          'namespace for materialx '
                          'conversion'.format(sd_node_id))
    return os.path.join(*function_namespace[2:-1])


def _getMtlxSearchPathList(search_path):
    if search_path:
        return search_path.split(mx.PATH_LIST_SEPARATOR)
    else:
        return getMatxSearchPathList()


def getMtlxModuleDocs(module, mtlx_search_path=None, absolute=False):
    import glob
    if mtlx_search_path == None:
        mtlx_search_path = getMatxSearchPathString()
    mtlx_search_path_list = _getMtlxSearchPathList(mtlx_search_path)
    result = set()
    result_abs = set()
    for search_path in mtlx_search_path_list:
        matching_files = glob.glob1(os.path.join(search_path, module),
                                    '*.mtlx')
        for f in matching_files:
            # Produce the include relative filename for the document
            p = makeConsistentPath(os.path.join(module,
                                                os.path.basename(f)))
            if p not in result:
                # Check if the file is known before adding to avoid adding
                # absolute paths shadowed by a file earlier in the search path
                result.add(p)
                abs_path = makeConsistentPath(os.path.join(search_path, p))
                result_abs.add(abs_path)

    if absolute:
        return sorted(result_abs)
    else:
        return sorted(result)


def importMtlxDocsForModule(module,
                            mtlx_document,
                            mtlx_search_path=None):
    if mtlx_search_path == None:
        mtlx_search_path = getMatxSearchPathString()
    module_docs = getMtlxModuleDocs(module,
                                    mtlx_search_path)
    for module_doc in module_docs:
        doc = mx.createDocument()
        mx.readFromXmlFile(doc,
                           module_doc,
                           mtlx_search_path)
        mx_utils.importSkipConflicting(mtlx_document, doc)


def hashMtlxDocsForModule(module,
                          mtlx_search_path=None):
    if mtlx_search_path == None:
        mtlx_search_path = getMatxSearchPathString()
    module_docs = getMtlxModuleDocs(module,
                                    mtlx_search_path)
    import hashlib
    hasher = hashlib.md5()
    for module_doc in module_docs:
        found_doc = False
        for p in _getMtlxSearchPathList(mtlx_search_path):
            try:
                with open(os.path.join(p, module_doc), 'r') as f:
                    for l in f.readlines():
                        hasher.update(l.encode())
                    found_doc = True
                    continue
            except FileNotFoundError:
                # Ignore invalid search path
                pass
        if not found_doc:
            raise ModuleError('Can\'t find source doucment for {} when hashing contents'.format(module_doc))
    return hasher.hexdigest()


def loadMtlxDocsForModule(module,
                          mtlx_document,
                          mtlx_search_path=None):
    if mtlx_search_path == None:
        mtlx_search_path = getMatxSearchPathString()
    module_docs = getMtlxModuleDocs(module, mtlx_search_path)
    for module_doc in module_docs:
        mx.readFromXmlFile(mtlx_document,
                           module_doc,
                           mtlx_search_path)


def getMdlNamespaceForModule(module):
    if module == '':
        return ''
    return 'mtlx::' + '::'.join(module.split('/'))


def getAllMtlxModules(search_path=None):
    mtlx_search_path_list = _getMtlxSearchPathList(search_path)
    allMtlxModules = set()
    for p in mtlx_search_path_list:
        for root, dirs, files in os.walk(p):
            if any([os.path.splitext(p)[1] == '.mtlx' for p in files]):
                module_path = os.path.relpath(root, p)
                allMtlxModules.add(makeConsistentPath(module_path))
    # Sort result to make result deterministic
    return sorted(allMtlxModules)


def getMdlModulePathFromMtlxElement(element):
    uri = element.getSourceUri()
    module_uri = makeConsistentPath(os.path.dirname(uri))
    return getMdlNamespaceForModule(module_uri)


def mtlxDocContainsModule(module, mtlx_doc):
    for c in mtlx_doc.getChildren():
        if makeConsistentPath(os.path.dirname(c.getSourceUri())) == module:
            return True


def generateSourceHashString(hash_string):
    return '// SRC_DOC_HASH {}\n'.format(hash_string)


def getMdlSourceHash(doc_src_path):
    with open(doc_src_path, 'r') as f:
        f.seek(0, 0)
        line = f.readline()
        components = line.split(' ')
        if len(components) == 3:
            if components[0] == '//' and components[1] == 'SRC_DOC_HASH':
                return components[2].rstrip('\n')
    return None
