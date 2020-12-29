#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from hashlib import sha3_256

def _get_all_properties(node):
    from sd.api.sdproperty import SDPropertyCategory
    '''
    :param node: the node to hash
    :type node: sd.api.mdl.sdmdlnode.SDMDLNode
    :return:
    '''
    categories = [SDPropertyCategory.Input,
                  SDPropertyCategory.Output,
                  SDPropertyCategory.Annotation]
    result = []
    for pp in [node.getProperties(c) for c in categories]:
        result = result + [p for p in pp]
    return result

def hash_node(node, hash):
    '''
    :param node: the node to hash
    :type node: sd.api.mdl.sdmdlnode.SDMDLNode
    :return:
    '''
    hash.update(node.getIdentifier().encode('utf-8'))
    for p in _get_all_properties(node):
        hash_property(p, node, hash)

def hash_value(value, hash):
    '''
    :param node: the type to hash
    :type node: sd.api.SDValue
    :return:
    '''
    from sd.api.mdl.sdmdlvaluecall import SDMDLValueCall
    from sd.api.sdvaluematrix import SDValueMatrix
    from sd.api.mdl.sdmdlvaluetexturereference import SDMDLValueTextureReference
    if value:
        if isinstance(value, SDMDLValueCall):
            hash.update(str(value.getValue()).encode('utf-8'))
        elif isinstance(value, SDValueMatrix):
            for row in range(value.getRowCount()):
                for column in range(value.getColumnCount()):
                    hash.update(str(value.getItem(column, row).get()).encode(
                        'utf-8'))
        elif isinstance(value, SDMDLValueTextureReference):
            pass
        else:
            hash.update(str(value.get()).encode('utf-8'))
    pass

def hash_type(type, hash):
    '''
    :param node: the type to hash
    :type node: sd.api.SDType
    :return:
    '''
    if type:
        hash.update(type.getId().encode('utf-8'))

def hash_property(property, node, hash):
    '''
    :param property: the property to hash
    :type property: sd.api.sdproperty.SDProperty
    :param node: the node the property lives on (None if it's not a node property)
    :type node: sd.api.mdl.sdmdlnode.SDMDLNode
    :return:
    '''
    hash.update(property.getId().encode('utf-8'))
    hash_type(property.getType(), hash)
    if node:
        connections = node.getPropertyConnections(property)
        if len(connections) > 0:
            # Hash connections
            for c in connections:
                connected_node = c.getInputPropertyNode()
                id = connected_node.getIdentifier()
                hash.update(id.encode('utf-8'))
        else:
            hash_value(node.getPropertyValue(property), hash)
    else:
        hash_value(property.getDefaultValue(), hash)


def hash_graph(graph, hash):
    '''
    :param graph: the graph to hash
    :type graph: sd.api.mdl.sdmdlgraph.SDMDLGraph
    :return:
    '''
    hash.update(graph.getIdentifier().encode('utf-8'))
    for n in graph.getNodes():
        hash_node(n, hash)
    for p in _get_all_properties(graph):
        hash_property(p, None, hash)
    for o in graph.getOutputNodes():
        hash.update(o.getIdentifier().encode('utf-8'))
