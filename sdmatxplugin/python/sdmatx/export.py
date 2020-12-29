#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os

def _findAllOutputUsages(graph):
    from sd.api.sdproperty import SDPropertyCategory
    allOutputs = graph.getOutputNodes()
    result = {}
    for node in allOutputs:
        usages = node.getPropertyFromId('usages', SDPropertyCategory.Annotation)
        usage_values = node.getPropertyValue(usages)
        for v in usage_values.get():
            u = v.get()
            usage_name = u.getName()
            if usage_name in result:
                print('Warning: multiple outputs with one usage in graph: {}'.format(usage_name))
            else:
                result[usage_name] = node
    return result

def exportOutputByUsage(graph, texture_export_map):
    '''
    Export an output as an image by usage
    Raises an exception if the usage is missing
    :param graph:  sd.api.sbs.sdsbscompgraph.SDSBSCompGraph
    :param usage:
    :param filename:
    :return:
    '''
    from sd.api.sdproperty import SDPropertyCategory
    graph.compute()
    all_usages = _findAllOutputUsages(graph)
    result = {}
    for usage, filename in texture_export_map.items():
        outputNode = all_usages.get(usage, None)
        if not outputNode:
            print('Warning: missing usage in graph: {}'.format(usage))
            continue
        nodeDefinition = outputNode.getDefinition()
        outputProperties = nodeDefinition.getProperties(SDPropertyCategory.Output)
        for outputProperty in outputProperties:
            propertyValue = outputNode.getPropertyValue(outputProperty)
            if propertyValue:
                propertyTexture = propertyValue.get()
                if propertyTexture:
                    propertyTexture.save(filename)
                    result[usage] = filename
    return result


