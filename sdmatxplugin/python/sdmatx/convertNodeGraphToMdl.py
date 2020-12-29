#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import MaterialX as mx
from sdmatx.common import *

def _getOrderedNodes(root, nodegraph, placed_nodes):
    """
    Follows a node to the inputs and outputs a list of nodes that is unique and ordered so any node in the
    list is independent of anything below it
    :param root:
    :type root: MaterialX.Node
    :param placed_nodes:
    :type placed_nodes: set

    """
    if root in placed_nodes:
        # This node has already been visited
        return []
    node_list = []
    for i in range(root.getUpstreamEdgeCount()):
        edge = root.getUpstreamEdge(None, i)
        parent = edge.getUpstreamElement()
        if parent != None:
            node_list += _getOrderedNodes(parent, nodegraph, placed_nodes)
    return node_list + [root]

def _getMdlIntefaceName(node):
    ifs = node.getInterfaceName()
    return correctMdlInputForReservedWords(ifs)

def _getMdlValue(node):
    value = node.getValueString()
    mtlx_type = node.getType()
    mdl_type = mtlxToMdl_types[mtlx_type]
    if mtlx_type == 'string':
        return mdl_type + '(\"' + value + '\")'
    else:
        return mdl_type + '(' + value +')'

def _getMdlFunctionName(node, warnings, clashing_nodes, used_mdl_modules):
    from .modules import getMdlModulePathFromMtlxElement
    node_def = node.getNodeDef()
    if node_def == None:
        raise BaseException('No node def found for node {}'.format(node.getName()))
    full_function_name = node_def.getName()
    function_name = correctMdlFunctionForReservedWords(node_def.getNodeString())
    if node_def in clashing_nodes:
        function_name += '_' + node_def.getType()
    if function_name in mtlx_unsupported_nodes:
        warnings.append('// Error: Node %s not supported' % function_name)
    mdl_module = getMdlModulePathFromMtlxElement(node_def)
    qualified_function_name = mdl_module + '::' + function_name if mdl_module \
        else function_name
    if mdl_module != '':
        used_mdl_modules.add(mdl_module)
    return qualified_function_name

class _UnsupportedTypeException(BaseException):
    pass

def _generateCall(node,
                  var_generator,
                  node_outputs,
                  warnings,
                  clashing_nodes,
                  used_mdl_modules):
    if node.__class__ is mx.Output:
        connected_node = node.getConnectedNode()
        return 'return ' + node_outputs[connected_node] + ';'
    else:
        var_name = var_generator.get()
        type = mtlxToMdl_types[node.getType()]
        result = type + ' ' + var_name + ' = '
        result += _getMdlFunctionName(node,
                                      warnings,
                                      clashing_nodes,
                                      used_mdl_modules) + '('
        nd = node.getNodeDef()
        for ii in nd.getInputs():
            i = node.getInput(ii.getName())
            referred_node = i.getConnectedNode() if i else None
            if not i:
                # Use default if no connected node or value
                result += _getMdlValue(ii)
            elif referred_node:
                if referred_node.getType() in mdl_unsupported_types:
                    raise _UnsupportedTypeException('Type %s not supported in mdl conversion' % referred_node.getType())
                result += node_outputs[referred_node]
            elif i.getInterfaceName() != '':
                result += _getMdlIntefaceName(i)
            elif i.getValue() != '':
                result += _getMdlValue(i)
            else:
                raise BaseException('Couldn\'t find input, constant or interface name on input')
            result += ', '
        for ii in nd.getParameters():
            i = node.getParameter(ii.getName())
            if not i:
                # Use default if no connected node or value
                result += _getMdlValue(ii)
            elif i.getInterfaceName() and i.getInterfaceName() != '':
                result += _getMdlIntefaceName(i)
            elif i.getValue() != None:
                result += _getMdlValue(i)
            else:
                raise BaseException('Couldn\'t find input, constant or interface name on input')
            result += ', '
        result = result.rstrip(', ')
        result += ');'
        node_outputs[node] = var_name
        return result

def convertNodeGraphToMdlBody(nodegraph,
                              warnings,
                              clashing_nodes,
                              used_mdl_modules):
    """

    :param nodegraph:
    :type nodegraph: MaterialX.NodeGraph
    :param nodedef:
    :type nodedef: MaterialX.NodeDef
    :return:
    """
    class VarNameGenerator:
        def __init__(self):
            self.idx = 0
        def get(self):
            self.idx = self.idx + 1
            return 'v_' + str(self.idx-1)

    result = '\n'
    var_generator = VarNameGenerator()
    if nodegraph.getOutputCount() != 1:
        raise BaseException('Multioutput nodes not supported: '
                            '{}'.format(nodegraph.getName()))
    output = nodegraph.getOutputs()[0]
    ordered_nodes = _getOrderedNodes(output, nodegraph, set())
    node_outputs = {}
    for node in ordered_nodes:
        result += '    ' + _generateCall(node,
                                         var_generator,
                                         node_outputs,
                                         warnings,
                                         clashing_nodes,
                                         used_mdl_modules) + '\n'
    return result
