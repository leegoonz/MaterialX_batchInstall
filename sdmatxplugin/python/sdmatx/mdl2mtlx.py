# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from .paths import makeConsistentPath
from .modules import moduleFromMdlNamespace, \
    importMtlxDocsForModule, getMtlxModuleDocs, mtlxDocContainsModule
import logging
import os
import shutil

import MaterialX as mtx

logger = logging.getLogger("SDMaterialX")

mdlToMtlx_types = {
    'int': 'integer',
    'bool': 'boolean',
    'float': 'float',
    'float2': 'vector2',
    'float3': 'vector3',
    'float4': 'vector4',
    'float3x3': 'matrix33',
    'float4x4': 'matrix44',
    'string': 'string',
    'color2': 'color2',
    'color3': 'color3',
    'color': 'color3',
    'color4': 'color4',
    'ColorRGB': 'color3',
    'texture_2d': 'filename',
    'material': 'surfaceshader',
    'mdl::material': 'surfaceshader',
    'mdl::texture_2d': 'filename',
    'matrix<float>[3][3]': 'matrix33',
    'matrix<float>[4][4]': 'matrix44'
}

PARAMETER_PROXY = 'parameter_proxy'
INPUT_PROXY = 'input_proxy'
SAMPLER_PROXY = 'sampler_proxy'
TEXTURED_INPUT_PROXY = 'textured_input_proxy'

PARAM_MODIFIER = 'param'
INPUT_MODIFIER = 'input'
SAMPLER_MODIFIER = 'sampler'
CONSTANT_PROXY = 'constant'

SWIZZLE_NODE_NAME = 'swizzle'
GLSLFX_USAGE_TAG = 'GLSLFX_usage'

# TODO: support all color types
mtlxColorTypes = {
    # 'color2',
    'color3',
    # 'color4'
}

_mdlSubgraphPrefix = 'mdl::mtlx::shared::subgraph_output('


class MDLToMaterialXException(BaseException):
    pass


class UnsupportedMDLType(MDLToMaterialXException):
    def __init__(self, text, node_name=None):
        MDLToMaterialXException.__init__(self, text)
        self.node_name = node_name


class MissingMaterialXType(MDLToMaterialXException):
    pass


class InvalidGraphType(MDLToMaterialXException):
    pass


class TypeModifierEnum:
    AUTO = 0
    UNIFORM = 1
    VARYING = 2


mtlx_rangedTypes = {
    'float', 'vector2', 'vector3', 'vector4'
}


def _getMtlxName(name):
    invalid_names = {
        'in_',
        'default_'
    }
    if name in invalid_names:
        return name[:-1]
    return name


def check_and_remove_substring_left(s, pattern):
    if len(s) < len(pattern) or s[:len(pattern)] != pattern:
        raise MDLToMaterialXException('%s is not the leftmost part of %s' %
                                      (pattern, s))
    return s[len(pattern):]


def _computeMinMaxValues(valueType, valueString, sd_node):
    import math
    from sd.api.sdproperty import SDPropertyCategory

    def _getPropertyVal(prop_name):
        prop = sd_node.getPropertyFromId(
            prop_name, SDPropertyCategory.Annotation)
        if prop:
            property_value = sd_node.getPropertyValue(prop)
            if property_value:
                return property_value.get()
        return None

    def _legacyRanges():
        if valueType in mtlx_rangedTypes:
            values = valueString.split(",")
            min_value = float('inf')
            max_value = float('-inf')
            for valueStr in values:
                value = float(valueStr)
                min_value = min(min_value, value)
                max_value = max(max_value, value)
            largest_value = max(abs(min_value), abs(max_value))
            if largest_value <= 1.0:
                largest_value = 1.0
            else:
                largest_value = float(math.ceil(largest_value * 5.0))
            uimin = min(0.0, float(math.floor(min_value)))
            uimax = largest_value
            if uimin == 0.0 and uimax == 0.0:
                uimax = 1.0
            return [(uimin, uimax), (uimin, uimax)]
        else:
            return [(None, None), (None, None)]

    range_properties = [('soft_range_min', 'soft_range_max'),
                        ('hard_range_min', 'hard_range_max')]
    ranges_from_properties = [(_getPropertyVal(rr)
                               for rr in r) for r in range_properties]
    legacy_ranges = _legacyRanges()
    result = list([tuple((rr if rr else legacy_ranges[i][j] for j, rr in enumerate(r))) for i, r in
                   enumerate(ranges_from_properties)])
    return result


def _sdValueToString(sdValue):
    # expect values in the form of: "1.0, 2.0, 3.0" or "foobar"

    # Hack to return something from constructors we don't understand
    # Specifically added to support texture_2d constructor with parameters
    value_strings = []
    full_type_name = sdValue.getType().getId()
    type_name = full_type_name.split('::')[-1]
    if type_name in ['color2', 'color3', 'color4', 'ColorRGB']:

        if 'SDTypeStruct' in str(sdValue.getType()):
            fields = ['r', 'g', 'b', 'a']
            for field in fields:
                member = sdValue.getPropertyValueFromId(field)
                if member:
                    value_strings.append(str(member.get()))
                else:
                    break
        else:
            # TODO verify standard color/color3
            # string coming in is: r: ..., g: ..., etc...
            tokens = str(sdValue.get()).split(',')
            for token in tokens:
                value_strings.append(token.split(":")[-1])
    elif type_name in ['float2', 'float3', 'float4']:
        # string coming in is: x: ..., y: ..., etc...
        tokens = str(sdValue.get()).split(',')
        for token in tokens:
            value_strings.append(token.split(":")[-1])
    elif type_name == 'bool':
        value_strings = [str(sdValue.get()).lower()]
    elif type_name == 'texture_2d':
        # If there is a string, set it as filename
        return sdValue.getValue()
    elif type_name.startswith('matrix'):
        # Matrices are in row major order
        values = []
        for r in range(sdValue.getRowCount()):
            for c in range(sdValue.getColumnCount()):
                # Todo: are row and column swapped in getItem?
                values.append(str(sdValue.getItem(r, c).get()))
        return ','.join(values)
    else:
        value_strings = str(sdValue.get()).split(';')

    if 'color' in type_name or 'float' in type_name:
        for i in range(len(value_strings)):
            # ensure this is a decimal
            if not '.' in value_strings[i]:
                value_strings[i] += ".0"

    return ','.join(value_strings)


def _resolveSDPath(resource_path, sd_package, resource_root):
    resource_path = resource_path.strip()
    if not resource_path:
        # empty path
        return ''
    if resource_path.startswith('pkg://'):
        # This is a resource link, resolve it to a file path
        resource = sd_package.findResourceFromUrl(resource_path)
        resource_path = resource.getFilePath()
    if resource_root:
        # Make the path relative to the resource root if one is provided
        resource_path = os.path.relpath(resource_path, resource_root)
    resource_path = makeConsistentPath(resource_path)
    return resource_path


def _setMtlxValue(sdValue, mtlxInput, sd_package, resource_root):
    from sd.api.mdl.sdmdlvaluecall import SDMDLValueCall
    if isinstance(sdValue, SDMDLValueCall):
        # This is a bound call as opposed to a value
        v = sdValue.getValue()
        if 'getGeomPropDef' in v:
            # This is a geomprop, these are not to be set on bind inputs
            # so just leave it to pick it up from the node def
            # TODO: Clean up this at some point
            pass
        else:
            logger.warning('Unsupported value call, setting empty value')
    else:
        if mtlxInput.getType() == 'filename' and resource_root:
            resolved_path = _resolveSDPath(
                _sdValueToString(sdValue), sd_package, resource_root)
            mtlxInput.setValueString(resolved_path)
        else:
            mtlxInput.setValueString(_sdValueToString(sdValue))


def __isIgnoredNode(sd_node_id):
    if sd_node_id.startswith('mdl::texture_2d'):
        return True
    return False


def __getSamplerUsage(sd_node):
    '''
    :param sd_node: the node to find sampler usage from
    :type sd_node: class SDNode
    :return: str
    '''
    from sd.api.sdproperty import SDPropertyCategory
    vs = sd_node.getPropertyValueFromId(
        'sampler_usage', SDPropertyCategory.Annotation)
    return vs.get()


class _Mdl2MtlxCaches:
    '''
    Represents shared state during a single export process
    '''

    def __init__(self):
        self.uniqueNodeNameMap = {}
        self.nodeDefCache = {}


def _getUniqueNodeName(mdl2mtlx_caches, sd_node=None):
    '''
    SD node names have id that change at every session.
    This utility returns consistent naming for created nodes across sessions
    as long as nodes are created in a deterministic order
    '''
    if sd_node is None:
        # if sd_node is not defined, return a new, unique name
        # to ensure uniqueness in the dict, i is not an integer, it's a string
        i = 'onthefly_' + str(
            len(mdl2mtlx_caches.uniqueNodeNameMap))  # never on the map already
        mdl2mtlx_caches.uniqueNodeNameMap[i] = i  # i is a string
        return i
    else:
        i = sd_node.getIdentifier()

        if i not in mdl2mtlx_caches.uniqueNodeNameMap:
            definition = sd_node.getDefinition().getId()
            definition = definition.split('(')[0]
            definition = definition.split('::')[-1]
            mdl2mtlx_caches.uniqueNodeNameMap[
                i] = 'node_' + definition + '_' + str(
                len(mdl2mtlx_caches.uniqueNodeNameMap))
    return mdl2mtlx_caches.uniqueNodeNameMap[i]


def _getInterfaceName(sd_node):
    from sd.api.sdproperty import SDPropertyCategory
    name_property = sd_node.getPropertyFromId('name', SDPropertyCategory.Input)
    if not name_property:
        name_property = sd_node.getPropertyFromId('identifier',
                                                  SDPropertyCategory.Annotation)
    # name_property = next(x for x in input_properties if x.getId() == "name")
    mtlx_interface_name = str(sd_node.getPropertyValue(name_property).get())
    if mtlx_interface_name == "":
        logger.error("Unnamed interface detected")
    return mtlx_interface_name


def _getMtlxNameAndType(sd_node, mtlx_document, mdl2mtlx_caches):
    '''
    :param sd_node:
    :type sd_node: class SDNode
    :param mtlx_document:
    :param mdl2mtlx_caches:
    :return:
    '''
    from sd.api.sdproperty import SDPropertyCategory
    sd_node_id = sd_node.getDefinition().getId()
    output_properties = sd_node.getProperties(SDPropertyCategory.Output)
    if len(output_properties) != 1:
        raise UnsupportedMDLType('Multiple output properties on MDL node '
                                 'not supported')
    type = output_properties[0].getType()
    mdl_type_id = type.getId() if type else None
    if 'mdl::mtlx::' in sd_node_id:
        if sd_node_id.startswith(_mdlSubgraphPrefix):
            mtlx_type = mdlToMtlx_types[mdl_type_id]
            return 'subgraph_proxy', mtlx_type, \
                   [INPUT_MODIFIER]
        if mdl_type_id and mdl_type_id not in mdlToMtlx_types:
            raise MissingMaterialXType('No type mapping for mdl type: '
                                       '{}'.format(mdl_type_id))
        mtlx_type = mdlToMtlx_types[mdl_type_id] if type else None
        function_name = sd_node_id.split('(')[0]
        namespaces = function_name.split('::')
        mtlx_full_name = namespaces[-1]

        split_mtlx_type = mtlx_full_name.split('_')
        if len(split_mtlx_type) == 1:
            mtlx_name = mtlx_full_name
        else:
            potential_type = split_mtlx_type[-1]
            # Todo: Make this o(log(n))
            if potential_type in mdlToMtlx_types.values() or potential_type == '':
                # This is a decorated type, reconstruct the name
                # Also dealing with keyword correction by adding an _ to the name
                # TODO: Track corrected keywords in a more stringent way
                mtlx_name = '_'.join(split_mtlx_type[:-1])
            else:
                # This is just a node that happens to have _ in its name
                mtlx_name = mtlx_full_name
    elif _isMdlConstructor(sd_node_id):
        from sd.api.mdl.sdmdlconstantnode import SDMDLConstantNode
        # This is a constructor
        modifier_prop = sd_node.getPropertyValueFromId('type_modifier',
                                                       SDPropertyCategory.Annotation)
        isExposed = isinstance(sd_node,
                               SDMDLConstantNode) and sd_node.isExposed()
        mtlx_type = mdlToMtlx_types[mdl_type_id]
        if isExposed:
            prop = sd_node.getProperties(SDPropertyCategory.Annotation)
            usage = __getSamplerUsage(sd_node)
            # This parameter is bound as a texture
            if mtlx_type == 'filename':
                return SAMPLER_PROXY, mtlx_type, \
                    [PARAM_MODIFIER]
            if usage != '':
                # TODO: What to do with this one, not sure if param modifier applies
                return TEXTURED_INPUT_PROXY, mtlx_type, \
                    [PARAM_MODIFIER]
            elif modifier_prop and modifier_prop.get() in [TypeModifierEnum.UNIFORM, TypeModifierEnum.AUTO]:
                # This is a parameter
                return PARAMETER_PROXY, mtlx_type, \
                    [PARAM_MODIFIER]
            elif modifier_prop and modifier_prop.get() == TypeModifierEnum.VARYING:
                # This is an input
                return INPUT_PROXY, mtlx_type, [INPUT_MODIFIER]
            else:
                raise MDLToMaterialXException(
                    'Unknown exposed input type for exposed node {}'.format(sd_node_id))
        else:
            input_properties = sd_node.getProperties(SDPropertyCategory.Input)
            if sd_node_id.startswith('mdl::texture_2d'):
                # We have special case treatment for mdl::texture_2d
                # constructors
                # TODO: This node should probably be suppressed rather than
                # returned as a dummy result
                return CONSTANT_PROXY, mtlx_type, [PARAM_MODIFIER]

            if len(input_properties) != 1:
                raise UnsupportedMDLType('Unsupported constructor found, '
                                         'non-identity mdl constructors are '
                                         'not supported. Node {}'.format(
                                             sd_node_id))
            if mdlToMtlx_types[input_properties[0].getType().getId()] != mtlx_type:
                # This is a constructor that creates a color/vector from a float
                # type meaning we need to swizzle it automatically
                # We return a swizzle node instead (which has a default swizzle string) to
                # to expand a float
                return SWIZZLE_NODE_NAME, mtlx_type, [INPUT_MODIFIER]
            return CONSTANT_PROXY, mtlx_type, [PARAM_MODIFIER]
    else:
        raise UnsupportedMDLType(
            'Unsupported node found {}'.format(sd_node_id), sd_node_id)
    if mtlx_name in {INPUT_MODIFIER, INPUT_MODIFIER}:
        raise UnsupportedMDLType('Input and parameter nodes are deprecated')

    valid_parameters = [p for p in
                        sd_node.getProperties(SDPropertyCategory.Input) if
                        not p.getId().startswith('attr_')]
    parameter_types = [mdlToMtlx_types[p.getType().getId()] for p in
                       valid_parameters]

    mtlx_type, parameter_modifiers = _findMtlxParameterTypes(sd_node_id,
                                                             mtlx_name,
                                                             mtlx_type,
                                                             parameter_types,
                                                             mtlx_document,
                                                             mdl2mtlx_caches)
    return mtlx_name, mtlx_type, parameter_modifiers


def _connectNode(mtlx_element, sd_node, mtlx_document, mdl2mtlx_caches):
    mtlx_node, _, _ = _getMtlxNameAndType(sd_node,
                                          mtlx_document,
                                          mdl2mtlx_caches)
    nodeId = sd_node.getDefinition().getId()
    isInterfaceConnection = _isInputProxyNode(nodeId,
                                              mtlx_node) or _isParameterProxyNode(
        nodeId, mtlx_node)
    if isInterfaceConnection:
        # connect to interface
        mtlx_node_name = _getInterfaceName(sd_node)
        mtlx_element.setInterfaceName(mtlx_node_name)
    else:
        # node to node or node to output
        mtlx_node_name = _getUniqueNodeName(mdl2mtlx_caches, sd_node)
        mtlx_element.setNodeName(mtlx_node_name)


def _connectNodeGraphOutput(mtlx_element, sd_node, mtlx_document,
                            mtlx_node_graph, mdl2mtlx_caches):
    '''
    Connects a node to a node graph output (and deals with the bureaucracy around it
    :param mtlx_element:
    :param sd_node:
    :param mtlx_document:
    :param mtlx_node_graph:
    :param mdl2mtlx_caches:
    :type mdl2mtlx_caches _Mdl2MtlxCaches
    :return:
    '''
    mtlx_node, type, _ = _getMtlxNameAndType(sd_node,
                                             mtlx_document,
                                             mdl2mtlx_caches)
    nodeId = sd_node.getDefinition().getId()
    isInterfaceConnection = _isInputProxyNode(nodeId,
                                              mtlx_node) or _isParameterProxyNode(
        nodeId, mtlx_node)
    if isInterfaceConnection:
        # Not supported to connect inputs directly to outputs, need a constant in-between
        mtlx_node_name = _getInterfaceName(sd_node)
        constant_node = mtlx_node_graph.addNode('dot', mtlx_node_name +
                                                '_constant', type)
        input = constant_node.addInput('in')
        input.setType(type)
        input.setInterfaceName(mtlx_node_name)
        mtlx_element.setNodeName(constant_node.getName())
    else:
        # node to node or node to output
        mtlx_node_name = _getUniqueNodeName(mdl2mtlx_caches, sd_node)
        mtlx_element.setNodeName(mtlx_node_name)


def _isInput(mdl_property):
    from sd.api.mdl.sdmdltype import SDTypeModifier
    type_modifier = mdl_property.getType().getModifier()
    if type_modifier is SDTypeModifier.Uniform:
        return False
    return True


def _isMdlConstructor(node_id):
    split_namespace = node_id.split('::')
    # Make sure it's a constructor directly in the mdl namespace
    if split_namespace[0] == 'mdl':
        # Split off parameterlist if existent
        name = split_namespace[1].split('(')[0]
        return name in mdlToMtlx_types
    return False


def _isInputProxyNode(node_id, mtlx_name):
    return 'input_' in node_id or (
        _isMdlConstructor(node_id) and mtlx_name == INPUT_PROXY)


def _isParameterProxyNode(node_id, mtlx_name):
    return 'parameter_' in node_id or (
        _isMdlConstructor(node_id) and mtlx_name == PARAMETER_PROXY)


def _isSamplerProxyNode(node_id, mtlx_name):
    return _isMdlConstructor(node_id) and mtlx_name == SAMPLER_PROXY


def _isTexturedInputProxyNode(node_id, mtlx_name):
    return _isMdlConstructor(node_id) and mtlx_name == TEXTURED_INPUT_PROXY


def _isSubgraphOutputProxyNode(node_id, mtlx_name):
    return node_id.startswith(_mdlSubgraphPrefix) and mtlx_name == \
        'subgraph_proxy'


def _isTexture2dConstructor(node_id, mtlx_name):
    if mtlx_name == 'image' and 'texture_2d' in node_id:
        return True
    return False


def _mkNodeDefParamCacheEntries(node_defs):
    result = {}
    for nd in node_defs:
        allTypes = tuple(i.getType() for i in nd.getInputs() +
                         nd.getParameters())
        result[(nd.getType(), allTypes)] = nd
        # In certain circumstances we have a non output
        # This should be safe since it implies nothing is connected
        # TODO : Ignore these nodes instead?
        result[(None, allTypes)] = nd
    return result


def _findMtlxParameterTypes(sd_node_id, mtlx_name, mtlx_out_type,
                            mtlx_param_types, mtlx_document, mdl2mtlx_caches):
    def _implementation():
        if mtlx_name in mdl2mtlx_caches.nodeDefCache:
            matching_node_defs = mdl2mtlx_caches.nodeDefCache[mtlx_name]
        else:
            matching_node_defs = _mkNodeDefParamCacheEntries(
                mtlx_document.getMatchingNodeDefs(mtlx_name))
        d = matching_node_defs.get(
            (mtlx_out_type, tuple(mtlx_param_types)), None)
        if not d:
            raise MissingMaterialXType('No MaterialX type found for '
                                       'function {}'.format(mtlx_name))
        mdl2mtlx_caches.nodeDefCache[mtlx_name] = matching_node_defs
        return (d.getType(),
                ([INPUT_MODIFIER] * len(d.getInputs())) + (
            [PARAM_MODIFIER] * len(d.getParameters())))

    try:
        # Try to find the implementation given what is already imported
        return _implementation()
    except MissingMaterialXType:
        # This is a sign of us missing an implementation
        # this can mean either we actually miss the implementation or need to
        # import the library document and try again
        node_dir = moduleFromMdlNamespace(sd_node_id)
        importMtlxDocsForModule(node_dir, mtlx_document)
        return _implementation()


def _bindMaterial(sd_node,
                  material_name,
                  mtlx_document,
                  mtlx_graph,
                  mtlx_node_def,
                  sd_package,
                  resource_root,
                  mdl2mtlx_caches):
    """
    :param sd_node: The node
    :type sd_node: class SDNode
    """
    from sd.api.sdproperty import SDPropertyCategory

    def _getBoundInputCount(node):
        from sd.api.mdl.sdmdlvaluecall import SDMDLValueCall
        count = 0
        for mdl_property in node.getProperties(SDPropertyCategory.Input):
            if len(sd_node.getPropertyConnections(mdl_property)) > 0 or \
                    isinstance(sd_node.getPropertyValue(mdl_property),
                               SDMDLValueCall):
                count += 1
        return count

    def _createBinding(mdl_property, input_name, source_type):
        if _isInput(mdl_property):
            return mtlx_shaderref.addBindInput(input_name, source_type)
        else:
            return mtlx_shaderref.addBindParam(input_name, source_type)

    def _instantiateValueCall(sdValue, mdl2mtlx_caches):
        # Since we don't have implementations of getGeomPropDef here we emulate them for now
        # TODO: Make sure this done in a consistent way
        geomPropMapping = {
            'getGeomPropDef_Pworld': (
                'position', {'space': 'world'}, 'vector3'),
            'getGeomPropDef_Nworld': ('normal', {'space': 'world'}, 'vector3'),
            'getGeomPropDef_Tworld': ('tangent', {'space': 'world'}, 'vector3'),
            'getGeomPropDef_Pobject': (
                'position', {'space': 'object'}, 'vector3'),
            'getGeomPropDef_Nobject': (
                'normal', {'space': 'object'}, 'vector3'),
            'getGeomPropDef_Tobject': (
                'tangent', {'space': 'object'}, 'vector3'),
            'getGeomPropDef_UV0': ('texcoord', {'index': 0}, 'vector2'),
        }

        v = sdValue.getValue()
        if 'getGeomPropDef' in v:
            # This is a geomprop, instantiate the call
            prop = v.split('::')[-1].split('(')[0]
            if prop in geomPropMapping:
                node_category, parameters, type = geomPropMapping[prop]
            else:
                # For unknown reasons there is occasionally an integer suffixed
                # to the end of the value call
                # TODO: Figure out why
                last_underscore_location = prop.rindex('_')
                if last_underscore_location != -1:
                    prop_str = prop[:last_underscore_location]
                    node_category, parameters, type = geomPropMapping[prop_str]
                else:
                    raise MDLToMaterialXException(
                        'Can\'t find geomprop {}'.format(prop))
            new_node = mtlx_graph.addNode(
                name=_getUniqueNodeName(mdl2mtlx_caches),
                category=node_category)
            for p, val in parameters.items():
                param = new_node.addParameter(p)
                param.setValue(val)
            new_node.setType(type)
            return new_node
        else:
            logger.warning('Unsupported value call, setting empty value')
            return None

    from sd.api.mdl.sdmdlvaluecall import SDMDLValueCall

    # sd_node = sd_node.getDefinition().getId()
    mtlx_name, mtlx_return, _ = _getMtlxNameAndType(sd_node,
                                                    mtlx_document,
                                                    mdl2mtlx_caches)

    mtlx_material = mtlx_document.addMaterial(material_name)
    mtlx_shaderref = mtlx_material.addShaderRef(material_name)
    mtlx_shaderref.setAttribute("node", mtlx_name)

    bound_input_count = _getBoundInputCount(sd_node)
    for mdl_property in sd_node.getProperties(SDPropertyCategory.Input):
        property_val = sd_node.getPropertyValue(mdl_property)
        property_connections = sd_node.getPropertyConnections(mdl_property)
        input_name = mdl_property.getId()
        if len(property_connections) > 0:
            sd_source_node = property_connections[0].getInputPropertyNode()
            sd_source_name, source_type, _ = _getMtlxNameAndType(
                sd_source_node, mtlx_document, mdl2mtlx_caches)
            shader_input_name = mdl_property.getId()
            # Add an output to material x graph
            mtlx_bind = _createBinding(mdl_property, input_name, source_type)
            mtlx_output_name = shader_input_name + '_output'
            mtlx_output = mtlx_graph.addOutput(
                name=mtlx_output_name, type=source_type)
            mtlx_nd_output = mtlx_node_def.addOutput(
                name=mtlx_output_name, type=source_type)
            _connectNodeGraphOutput(mtlx_output,
                                    sd_source_node,
                                    mtlx_document,
                                    mtlx_graph,
                                    mdl2mtlx_caches)
            # Bind the output to the surface shader
            mtlx_bind.setOutputString(mtlx_output.getName())
            mtlx_bind.setNodeGraphString(mtlx_graph.getName())
        elif isinstance(property_val, SDMDLValueCall):
            # This is a value calle, instantiate the node and connect it
            # TODO: Share more code with the connected code path
            new_node = _instantiateValueCall(property_val, mdl2mtlx_caches)
            source_type = new_node.getType()
            mtlx_bind = _createBinding(mdl_property, input_name, source_type)
            shader_input_name = mdl_property.getId()
            mtlx_output_name = shader_input_name + '_output'
            mtlx_output = mtlx_graph.addOutput(
                name=mtlx_output_name, type=source_type)
            mtlx_nd_output = mtlx_node_def.addOutput(
                name=mtlx_output_name, type=source_type)
            mtlx_output.setNodeName(new_node.getName())
            # Bind the output to the surface shader
            mtlx_bind.setOutputString(mtlx_output.getName())
            mtlx_bind.setNodeGraphString(mtlx_graph.getName())
        elif property_val:
            type = mdl_property.getType()

            mtlx_type = mdlToMtlx_types[type.getId()]
            mtlx_bind = _createBinding(mdl_property, input_name, mtlx_type)
            _setMtlxValue(property_val, mtlx_bind, sd_package, resource_root)
    return mtlx_material


def _addMaterialXNode(mtlx_graph,
                      mtlx_name,
                      mtlx_return,
                      sd_node,
                      sd_node_id,
                      parameter_modifiers,
                      mtlx_document,
                      sd_package,
                      resource_root,
                      mdl2mtlx_caches):
    from sd.api.sdproperty import SDPropertyCategory
    if __isIgnoredNode(sd_node_id):
        # This node has special treatment and is dealt with by the node
        # referencing it
        # TODO: this could potentially be solved cleaner by traversing the
        # graph from the output to the input which would get rid of all nodes
        # not used automatically
        return None

    mtlx_node = mtlx_graph.addNode(
        mtlx_name, _getUniqueNodeName(mdl2mtlx_caches, sd_node), mtlx_return)
    for idx, input_property in enumerate(
            sd_node.getProperties(SDPropertyCategory.Input)):
        mdl_input_type = input_property.getType().getId()
        # Workaround for unconnected pin with multiple possible types
        if mdl_input_type is '':
            mdl_input_type = sd_node.getPropertyValue(
                input_property).getType().getId()

        mdl_type_name = mdl_input_type.split('::')[-1]
        if mdl_type_name not in mdlToMtlx_types:
            logger.warning('Skipping unmapped input {}'.format(mdl_type_name))
            continue
        input_type = mdlToMtlx_types[mdl_type_name]
        # TODO: This is a hack related to mdl constants
        if mtlx_name == CONSTANT_PROXY:
            # This is an mdl constant meaning it's likely the name
            # came from a mdl constant node which has a different naming convention
            mdl_input_name = 'value'
        elif mtlx_name == SWIZZLE_NODE_NAME and _getMtlxName(input_property.getId()) == 'value':
            # This is a special case where we replace a color/vector constructor taking a float input
            # with a swizzle node. The input on the constructor is called value so we change it to in
            # The other side of this hack is in _getMtlxNameAndType where we return a swizzle node
            # instead of a constructor
            mdl_input_name = 'in'
        else:
            mdl_input_name = _getMtlxName(input_property.getId())
        # detect whether we are connecting a param or node
        if not "attr_" in mdl_input_name:
            if idx >= len(parameter_modifiers):
                sd_size = len(sd_node.getProperties(SDPropertyCategory.Input))
                for idx, input_property in enumerate(
                        sd_node.getProperties(SDPropertyCategory.Input)):
                    logger.warning(input_property.getId())
                raise MDLToMaterialXException(
                    'Inconsistent parameter list length for '
                    'MaterialX node {mtlx_name} expected '
                    'length: {sd_size}, parameter list length '
                    '{mtlx_size}'.format(mtlx_name=mtlx_name,
                                         sd_size=sd_size,
                                         mtlx_size=len(
                                             parameter_modifiers)))
            if parameter_modifiers[idx] == PARAM_MODIFIER:
                mtlx_param = mtlx_node.addParameter(mdl_input_name, input_type)
                property_connections = sd_node.getPropertyConnections(
                    input_property)
                if len(property_connections) != 0:
                    # Parameters can't be connected
                    ItoO_connection = property_connections[0]
                    # child_node = ItoO_connection.getTargetNode()
                    child_node = ItoO_connection.getInputPropertyNode()
                    child_mtlx_name, _, _ = _getMtlxNameAndType(child_node,
                                                                mtlx_document,
                                                                mdl2mtlx_caches)
                    mdl_child_id = child_node.getDefinition().getId()

                    if _isParameterProxyNode(mdl_child_id, child_mtlx_name):
                        _connectNode(mtlx_param,
                                     child_node,
                                     mtlx_document,
                                     mdl2mtlx_caches)
                    elif _isSamplerProxyNode(mdl_child_id, child_mtlx_name):
                        # Connected to a sampler proxy. Forward usage gamma and potentially filename to the image
                        usage = __getSamplerUsage(child_node)
                        mtlx_node.setAttribute(GLSLFX_USAGE_TAG, usage)
                        __apply_gamma(child_node, mtlx_param, mtlx_return)
                    elif child_mtlx_name == CONSTANT_PROXY:
                        # This is a constant connected to a parameter
                        # Forward the constant's value directly since we can't
                        # connect a constant node to it. Note, some assumptions
                        # here break if we support non identity constructors
                        child_properties = child_node.getProperties(
                            SDPropertyCategory.Input)
                        if len(child_properties) != 1:
                            raise MDLToMaterialXException('Expected strictly '
                                                          'one input property '
                                                          'on constant node')

                        value = child_node.getPropertyValue(
                            child_properties[0])
                        _setMtlxValue(value, mtlx_param, sd_package,
                                      resource_root)
                        if _isTexture2dConstructor(sd_node_id, mtlx_name):
                            # This might be redundant but it preserves old behaviors
                            mtlx_node.setAttribute(GLSLFX_USAGE_TAG, '')
                    else:
                        pass
                else:
                    value = sd_node.getPropertyValue(input_property)
                    _setMtlxValue(value, mtlx_param, sd_package, resource_root)
            else:
                # This is an input (as opposed to a param
                if mdl_input_name == "in_":
                    mdl_input_name = "in"
                mtlx_input = mtlx_node.addInput(
                    mdl_input_name, input_type)
                property_connections = sd_node.getPropertyConnections(
                    input_property)
                if len(property_connections) != 0:
                    ItoO_connection = property_connections[0]
                    # child_node = ItoO_connection.getTargetNode()
                    # XXX dakrunch....
                    child_node = ItoO_connection.getInputPropertyNode()

                    _connectNode(mtlx_input,
                                 child_node,
                                 mtlx_document,
                                 mdl2mtlx_caches)
                else:
                    value = sd_node.getPropertyValue(input_property)
                    _setMtlxValue(value, mtlx_input, sd_package, resource_root)
        else:
            mtlx_attribute_name = check_and_remove_substring_left(
                mdl_input_name, "attr_")
            mtlx_attribute_value = str(sd_node.getPropertyValue(
                input_property).get())
            mtlx_node.setAttribute(
                mtlx_attribute_name, mtlx_attribute_value)
    if "image" in sd_node_id:
        mtlx_node.setAttribute("expose", "true")
    return mtlx_node


def _addDisplayNameAndGroup(sd_node, mtlx_element):
    from sd.api.sdproperty import SDPropertyCategory
    in_group = sd_node.getPropertyValueFromId(
        'in_group', SDPropertyCategory.Annotation)
    if in_group and in_group.get() != '':
        mtlx_element.setAttribute("uifolder", in_group.get())
    display_name = sd_node.getPropertyValueFromId(
        'display_name', SDPropertyCategory.Annotation)
    if display_name and display_name.get() != '':
        mtlx_element.setAttribute("uiname", display_name.get())


def _addParameterProxyNode(mtlx_node_def,
                           mtlx_node_graph,
                           mtlx_return,
                           sd_node,
                           sd_package,
                           resource_root,
                           force_root):
    from sd.api.sdproperty import SDPropertyCategory
    # Parameter node case
    mtlx_node_name = _getInterfaceName(sd_node)
    value = sd_node.getPropertyValueFromId('v', SDPropertyCategory.Input)
    if not value:
        # This is an mdl constructor. Get the property using the node name
        value = sd_node.getPropertyValueFromId(
            mtlx_node_name, SDPropertyCategory.Input)

    mtlx_parameter = mtlx_node_def.addParameter(mtlx_node_name, mtlx_return)
    mtlx_value_string = _sdValueToString(value)
    _setMtlxValue(value, mtlx_parameter, sd_package, resource_root)
    _addDisplayNameAndGroup(sd_node, mtlx_parameter)

    _setMinMax(mtlx_parameter, mtlx_return, mtlx_value_string, sd_node)
    if force_root is not None:
        mtlx_node = mtlx_node_graph.addNode('dot', mtlx_node_name)
        mtlx_node.setType(mtlx_return)
        input = mtlx_node.addInput('in')
        input.setType(mtlx_return)
        input.setInterfaceName(mtlx_node_name)
        return mtlx_node
    return None


def _setMinMax(mtlx_parameter, mtlx_return, mtlx_value_string, sd_node):
    vec_len = len(mtlx_value_string.split(','))
    min_max = _computeMinMaxValues(mtlx_return, mtlx_value_string, sd_node)
    if min_max:
        if min_max[0][0] is not None:
            mtlx_parameter.setAttribute(
                "uisoftmin", ','.join([str(min_max[0][0])] * vec_len))
        if min_max[0][1] is not None:
            mtlx_parameter.setAttribute(
                "uisoftmax", ','.join([str(min_max[0][1])] * vec_len))
        if min_max[1][0] is not None:
            mtlx_parameter.setAttribute(
                "uimin", ','.join([str(min_max[1][0])] * vec_len))
        if min_max[1][1] is not None:
            mtlx_parameter.setAttribute(
                "uimax", ','.join([str(min_max[1][1])] * vec_len))


def _addInputProxyNode(mtlx_node_def,
                       mtlx_node_graph,
                       mtlx_return,
                       sd_node,
                       sd_package,
                       resource_root,
                       force_root):
    from sd.api.sdproperty import SDPropertyCategory
    # Input node case
    mtlx_node_name = _getInterfaceName(sd_node)
    value = sd_node.getPropertyValueFromId('v', SDPropertyCategory.Input)
    if not value:
        # This is an mdl constructor. Get the property using the node name
        value = sd_node.getPropertyValueFromId(
            mtlx_node_name, SDPropertyCategory.Input)
    mtlx_input = mtlx_node_def.addInput(mtlx_node_name, mtlx_return)
    mtlx_value_string = _sdValueToString(value)
    # mtlx_input.setValueString(mtlx_value_string)
    _setMtlxValue(value, mtlx_input, sd_package, resource_root)
    _addDisplayNameAndGroup(sd_node, mtlx_input)
    _setMinMax(mtlx_input, mtlx_return, mtlx_value_string, sd_node)

    if force_root is not None:
        mtlx_node = mtlx_node_graph.addNode('dot', mtlx_node_name)
        mtlx_node.setType(mtlx_return)
        input = mtlx_node.addInput('in')
        input.setType(mtlx_return)
        input.setInterfaceName(mtlx_node_name)
        return mtlx_node
    return None


def __apply_gamma(sd_node, file_param, mtlx_return):
    from sd.api.sdproperty import SDPropertyCategory
    gamma_prop = sd_node.getPropertyFromId('gamma_type',
                                           SDPropertyCategory.Annotation)
    is_color_type = mtlx_return in mtlxColorTypes
    if gamma_prop and is_color_type:
        # Set color space according to gamma for color
        # textures
        gamma_value = sd_node.getPropertyValue(
            gamma_prop)
        gamma = gamma_value.get()
        file_param.setColorSpace(['srgb_texture',
                                  'linear',
                                  'srgb_texture'][gamma])
    elif is_color_type:
        # Default to srgb for color textures using the
        # texture constructor with no gamma specified
        file_param.setColorSpace('srgb_texture')


def _addTexturedInputProxyNode(mtlx_graph, mtlx_return, sd_node, mdl2mtlx_caches):
    '''
    :param mtlx_graph:
    :param mtlx_return:
    :param sd_node:
    :param mdl2mtlx_caches:
    :return:
    '''
    # An input color with a usage should be translated into a sampler
    new_node = mtlx_graph.addNode(
        'image', _getUniqueNodeName(mdl2mtlx_caches, sd_node), mtlx_return)
    new_node.setAttribute(GLSLFX_USAGE_TAG, __getSamplerUsage(sd_node))
    new_node.setAttribute('expose', 'true')
    file_param = new_node.addParameter('file', 'filename')
    __apply_gamma(sd_node, file_param, mtlx_return)

    return new_node


def _addSubgraphOutput(mtlx_graph,
                       mtlx_node_def,
                       mtlx_return,
                       sd_node,
                       mtlx_document,
                       mdl2mtlx_caches):
    '''

    :param mtlx_graph: The graph to add the subgraph output to
    :type mtlx_graph: class mx.NodeGraph
    :param mtlx_node_def:
    :type mtlx_node_def: class mx.NodeDef
    :param mtlx_return:
    :param sd_node:
    :return:
    '''
    from sd.api.sdproperty import SDPropertyCategory
    output_count = len(mtlx_graph.getOutputs())
    output_name = format('output_{}'.format(output_count))
    output = mtlx_node_def.addOutput(output_name)
    output.setType(mtlx_return)

    new_output = mtlx_graph.addOutput(output_name, mtlx_return)
    for idx, input_property in \
            enumerate(sd_node.getProperties(SDPropertyCategory.Input)):
        property_connections = sd_node.getPropertyConnections(
            input_property)
        if len(property_connections) != 0:
            ItoO_connection = property_connections[0]
            child_node = ItoO_connection.getInputPropertyNode()
            _connectNodeGraphOutput(new_output, child_node, mtlx_document,
                                    mtlx_graph, mdl2mtlx_caches)

    return new_output


def _bindNodeToMaterial(mtlx_graph,
                        mtlx_node_def,
                        mtlx_node,
                        mtlx_document,
                        material_name):
    '''
    :param mtlx_graph: The graph to add the subgraph output to
    :type mtlx_graph: class mx.NodeGraph
    :param mtlx_node_def:
    :type mtlx_node_def: class mx.NodeDef
    :param mtlx_node: the node to bind to the new material
    :type mtlx_node: class mx.Node
    :return:
    '''
    output_count = len(mtlx_graph.getOutputs())
    output_name = format('output_{}'.format(output_count))
    mtlx_return = 'color3'
    if output_count != 0:
        raise MDLToMaterialXException('Multiple outputs specified in forced '
                                      'root export')

    if mtlx_node.getType() != mtlx_return:
        # We need to swizzle this node to a color node
        # before connecting it to a material
        swizzle = mtlx_graph.addNode(SWIZZLE_NODE_NAME, material_name +
                                     '_output_swizzle')
        swizzle.setConnectedNode('in', mtlx_node)
        swizzle_string = {
            'float': 'x',
            'vector2': 'xyy',
            'vector3': 'xyz',
            'vector4': 'xyz',
            'color4': 'rgb'
        }.get(mtlx_node.getType(), None)
        if swizzle_string == None:
            raise MDLToMaterialXException('Unsupported output node type for '
                                          'selection export {}'.format(
                                              mtlx_node.getType()))
        c_param = swizzle.addParameter('channels')
        c_param.setValue(swizzle_string)
        mtlx_node = swizzle
    new_output = mtlx_graph.addOutput(output_name, mtlx_node.getType())
    new_output.setConnectedNode(mtlx_node)
    mtlx_node_def.addOutput(output_name, mtlx_node.getType())

    # Add material and shader ref
    importMtlxDocsForModule('stdlib/bxdf', mtlx_document)
    mtlx_material = mtlx_document.addMaterial(material_name)
    mtlx_shaderref = mtlx_material.addShaderRef(material_name)
    mtlx_shaderref.setAttribute('node', 'standard_surface')
    mtlx_bind = mtlx_shaderref.addBindInput('emission_color', 'color3')
    mtlx_bind.setOutputString(new_output.getName())
    mtlx_bind.setNodeGraphString(mtlx_graph.getName())

    emission_bind = mtlx_shaderref.addBindInput('emission', 'float')
    emission_bind.setValue(1.0)
    base_bind = mtlx_shaderref.addBindInput('base', 'float')
    base_bind.setValue(0.0)
    spec_bind = mtlx_shaderref.addBindInput('specular', 'float')
    spec_bind.setValue(0.0)
    return mtlx_material


def forwardOutputs(material_name, mtlx_document, mtlx_graph, mtlx_node_def):
    # Creates a new top level nodegraph forwarding all outputs
    # from the material graph.
    # This graph is then bound to the Shader ref
    # This behavior will make sure we only see the exposed inputs as opposed
    # to all inputs when generating a glsl file from it
    entry_graph = mtlx_document.addNodeGraph('{}_Bind'.format(material_name))
    # entry_graph.setNodeDef(mtlx_node_def)
    material_instance = entry_graph.addNode(
        mtlx_node_def.getNodeString(), '{}_Graph'.format(material_name))
    for i in mtlx_node_def.getInputs():
        new_i = material_instance.addInput(i.getName(), i.getType())
        # new_i.setInterfaceName(i.getName())
    for p in mtlx_node_def.getParameters():
        new_p = material_instance.addParameter(p.getName(), p.getType())
        # new_p.setInterfaceName(p.getName())
    is_multi_output = len(mtlx_node_def.getOutputs()) > 1
    if is_multi_output:
        material_instance.setType('multioutput')
    else:
        material_instance.setType(mtlx_node_def.getOutputs()[0].getType())
    for o in mtlx_node_def.getOutputs():
        new_output = entry_graph.addOutput(o.getName(), type=o.getType())
        new_output.setConnectedNode(material_instance)
        if is_multi_output:
            new_output.setAttribute('output', o.getName())

    material = mtlx_document.getMaterial(material_name)
    shader_ref = material.getShaderRefs()[0]
    for bi in shader_ref.getBindInputs():
        output_string = bi.getOutputString()
        if output_string:
            output = material_instance.getOutput(output_string)
            bi.setNodeGraphString(entry_graph.getName())


def _mdl2mtlx(material_name, mtlx_document, mtlx_graph, mtlx_node_def,
              resource_root, sd_graph, sd_package, force_root=None):
    '''
    :param material_name:
    :param mtlx_document:
    :param mtlx_graph:
    :param mtlx_node_def:
    :param resource_root:
    :param sd_graph:
    :type sd_graph: sd.api.mdl.sdmdlgraph.SDMDLGraph
    :param sd_package:
    :param force_root: A node forced to be the output
    :type force_root: sd.api.mdl.sdmdlnode.SDMDLNode
    :return:
    '''

    mdl2mtlx_caches = _Mdl2MtlxCaches()

    # Always include stdlib since there are situations where
    # nodes are introduced without checking for its presence causing
    # issues
    importMtlxDocsForModule('stdlib', mtlx_document)

    outputs = []
    for sd_node in sd_graph.getNodes():
        # Expecting valid nodes. matx_* nodes and special primitive nodes
        if sd_node.getDefinition() is None:
            raise UnsupportedMDLType('Failed to find mdl definition for node ' +
                                     sd_node.getIdentifier())
        sd_node_id = sd_node.getDefinition().getId()

        mtlx_name, mtlx_return, parameter_modifiers = _getMtlxNameAndType(
            sd_node, mtlx_document, mdl2mtlx_caches)
        new_mtlx_node = None
        if mtlx_name is None:
            raise MissingMaterialXType('MaterialX Name for node not found')
        is_selected = sd_node.getIdentifier() == force_root.getIdentifier() \
            if force_root else False
        is_root = False
        if mtlx_return == 'surfaceshader':
            # Export if it's the selection and we are forcing the root
            # or we are not forcing root and it's the root
            is_root = _isRoot(sd_node, sd_graph)
            if (is_selected and force_root) or (is_root and not force_root):
                outputs.append(_bindMaterial(sd_node,
                                             material_name,
                                             mtlx_document,
                                             mtlx_graph,
                                             mtlx_node_def,
                                             sd_package,
                                             resource_root,
                                             mdl2mtlx_caches))
        elif _isSubgraphOutputProxyNode(sd_node_id, mtlx_name):
            # Only bind subgraph if we are not forcing a root
            if not force_root:
                outputs.append(_addSubgraphOutput(mtlx_graph,
                                                  mtlx_node_def,
                                                  mtlx_return,
                                                  sd_node,
                                                  mtlx_document,
                                                  mdl2mtlx_caches))
        elif _isInputProxyNode(sd_node_id, mtlx_name):
            new_mtlx_node = _addInputProxyNode(mtlx_node_def,
                                               mtlx_graph,
                                               mtlx_return,
                                               sd_node,
                                               sd_package,
                                               resource_root,
                                               force_root)
        elif _isParameterProxyNode(sd_node_id, mtlx_name):
            new_mtlx_node = _addParameterProxyNode(mtlx_node_def,
                                                   mtlx_graph,
                                                   mtlx_return,
                                                   sd_node,
                                                   sd_package,
                                                   resource_root,
                                                   force_root)
        elif _isSamplerProxyNode(sd_node_id, mtlx_name):
            # Ignore, everything related to this is done
            # when adding the image node in _addMaterialXNode
            new_mtlx_node = None
        elif _isTexturedInputProxyNode(sd_node_id, mtlx_name):
            new_mtlx_node = _addTexturedInputProxyNode(
                mtlx_graph, mtlx_return, sd_node, mdl2mtlx_caches)
        elif mtlx_return is None:
            raise MissingMaterialXType(
                'Unknown return type in node {}'.format(mtlx_name))
        else:
            new_mtlx_node = _addMaterialXNode(mtlx_graph,
                                              mtlx_name,
                                              mtlx_return,
                                              sd_node,
                                              sd_node_id,
                                              parameter_modifiers,
                                              mtlx_document,
                                              sd_package,
                                              resource_root,
                                              mdl2mtlx_caches)
        # If we are forcing the root and this is the selection, make sure we
        # append a surface shader unless it's an surface shader, then it has
        # already been exported
        if force_root and is_selected and not (mtlx_return == 'surfaceshader'):
            if not new_mtlx_node:
                raise MDLToMaterialXException('Output node not converted to '
                                              'MaterialX {}'.format(sd_node_id))
            output_material = _bindNodeToMaterial(mtlx_graph, mtlx_node_def,
                                                  new_mtlx_node, mtlx_document,
                                                  material_name)
            outputs.append(output_material)
    return outputs


def _isRoot(sd_node, sd_graph):
    output_nodes = sd_graph.getOutputNodes()
    if len(output_nodes) < 1:
        raise MDLToMaterialXException('No output node defined in the graph')
    if len(output_nodes) > 1:
        raise MDLToMaterialXException('Multiple output nodes defined in the '
                                      'graph')
    output_node = output_nodes[0]
    return output_node.getIdentifier() == sd_node.getIdentifier()


def _hasBoundInput(material):
    '''
    Checks if there is at least one bound input/parameter on the material
    :param material: The material to check
    :type material: MaterialX.Material
    :return: bool
    '''
    shader_ref = material.getShaderRefs()[0]
    for i in shader_ref.getBindInputs() + shader_ref.getBindParams():
        if i.getOutputString() != '':
            return True
    return False


def mdl2mtlx_material(sd_graph,
                      material_name,
                      sd_package,
                      materialx_searchpaths,
                      resource_root=None):
    '''
    Given a substance mdl graph, generate a materialx document
    :type sd_graph: sd.api.SDGraph
    :param resource_root: The directory to make the resources relative to. If
    set to None it will use absolute paths
    :type resource_root: None or str
    :param materialx_searchpaths: A semi-colon separated string for search
    paths when including materialx documents
    :type materialx_searchpaths: str
    '''

    logger.info('Converting MDL to Mtlx')

    mtlx_document = mtx.createDocument()

    # TODO: Make the naming of the nodedef based on the shader name
    mtlx_node_def = mtlx_document.addNodeDef("ND{}".format(material_name))

    mtlx_node_def.removeOutput('out')
    mtlx_node_def.setNodeString("{}".format(material_name))

    mtlx_graph = mtlx_document.addNodeGraph(material_name + '_graph')
    mtlx_graph.setNodeDef(mtlx_node_def)
    outputs = _mdl2mtlx(material_name, mtlx_document, mtlx_graph,
                        mtlx_node_def, resource_root, sd_graph,
                        sd_package)
    # Pick the first output of material type
    mat = next(iter([o for o in outputs if isinstance(o, mtx.Material)]), None)
    # Special case when no nodes are bound to any material
    # Remove the graph entirely for now

    if not mat:
        raise InvalidGraphType('No material output in graph')
    if len(outputs) > 1:
        logger.warning('Warning, multiple outputs found in graph, using '
                       '{node_name}'.format(node_name=mat.getName()))
    if _hasBoundInput(mat):
        forwardOutputs(material_name, mtlx_document, mtlx_graph, mtlx_node_def)
    else:
        mtlx_document.removeNodeGraph(mtlx_graph.getName())
        mtlx_document.removeNodeDef(mtlx_node_def.getName())

    validation_result, validation_log = mtlx_document.validate()
    if not validation_result:
        logger.warning(validation_log)
    return mtlx_document


def _removeIncludedChildren(mtlx_doc):
    '''
    :param mtlx_doc:
    :type mtlx_doc: MaterialX.Document
    :return:
    '''
    for c in mtlx_doc.getChildren():
        if c.getSourceUri() != '':
            mtlx_doc.removeChild(c.getName())


def mdl2mtlx_subgraph(sd_graph,
                      node_name,
                      sd_package,
                      materialx_searchpaths,
                      resource_root=None):
    '''
    Given a substance mdl graph, generate a materialx document
    :type sd_graph: sd.api.SDGraph
    :param resource_root: The directory to make the resources relative to. If
    set to None it will use absolute paths
    :type resource_root: None or str
    :param materialx_searchpaths: A semi-colon separated string for search
    paths when including materialx documents
    :type materialx_searchpaths: str
    '''

    logger.info('Converting MDL to Mtlx')

    mtlx_document = mtx.createDocument()

    mtlx_node_def = mtlx_document.addNodeDef("ND_" + node_name)
    mtlx_node_def.removeOutput('out')
    mtlx_node_def.setNodeString(node_name)

    mtlx_graph = mtlx_document.addNodeGraph(node_name + '_graph')
    mtlx_graph.setNodeDef(mtlx_node_def)
    outputs = _mdl2mtlx(node_name, mtlx_document, mtlx_graph,
                        mtlx_node_def, resource_root, sd_graph,
                        sd_package)

    # Pick the first output
    output = next(
        iter([o for o in outputs if isinstance(o, mtx.Output)]), None)

    if not output:
        raise InvalidGraphType('No material output in graph')

    validation_result, validation_log = mtlx_document.validate()
    if not validation_result:
        logger.warning(validation_log)

    return mtlx_document


def mdl2mtlx_custom_root(sd_graph,
                         node_name,
                         sd_package,
                         materialx_searchpaths,
                         custom_root=None,
                         resource_root=None):
    '''
    Given a substance mdl graph, generate a materialx document
    :type sd_graph: sd.api.SDGraph
    :param resource_root: The directory to make the resources relative to. If
    set to None it will use absolute paths
    :type resource_root: None or str
    :param materialx_searchpaths: A semi-colon separated string for search
    paths when including materialx documents
    :type materialx_searchpaths: str
    :param custom_root: A node forced to be the output
    :type custom_root: sd.api.mdl.sdmdlnode.SDMDLNode
    '''

    logger.info('Converting MDL to Mtlx')

    mtlx_document = mtx.createDocument()

    mtlx_node_def = mtlx_document.addNodeDef("ND_" + node_name)
    mtlx_node_def.removeOutput('out')
    mtlx_node_def.setNodeString(node_name)

    mtlx_graph = mtlx_document.addNodeGraph(node_name + '_graph')
    mtlx_graph.setNodeDef(mtlx_node_def)

    # Move custom root to parent if we are on a subgraph output
    if custom_root.getDefinition().getId().startswith(
            'mdl::mtlx::shared::subgraph_output'):
        from sd.api.sdproperty import SDPropertyCategory
        p = custom_root.getPropertyFromId('p', SDPropertyCategory.Input)
        connections = custom_root.getPropertyConnections(p)
        if len(connections) > 0:
            custom_root = connections[0].getInputPropertyNode()
        else:
            raise MDLToMaterialXException('Nothing connected to subgraph '
                                          'output')

    outputs = _mdl2mtlx(node_name, mtlx_document, mtlx_graph,
                        mtlx_node_def, resource_root, sd_graph,
                        sd_package, force_root=custom_root)

    # Pick the first output of material type
    mat = next(iter([o for o in outputs if isinstance(o, mtx.Material)]), None)
    # Special case when no nodes are bound to any material
    # Remove the graph entirely for now

    if not mat:
        raise InvalidGraphType('No material output in graph')
    if len(outputs) > 1:
        logger.warning('Warning, multiple outputs found in graph, using '
                       '{node_name}'.format(node_name=mat.getName()))
    if _hasBoundInput(mat):
        forwardOutputs(node_name, mtlx_document, mtlx_graph, mtlx_node_def)
    else:
        mtlx_document.removeNodeGraph(mtlx_graph.getName())
        mtlx_document.removeNodeDef(mtlx_node_def.getName())

    validation_result, validation_log = mtlx_document.validate()
    if not validation_result:
        logger.warning(validation_log)

    return mtlx_document


def _findFilenames(mtlx_document):
    it = mtlx_document.traverseTree()
    all_paths = set()
    for element in it:
        if isinstance(element, mtx.Parameter) and \
                element.getType() == 'filename':
            value_string = element.getValueString()
            if value_string != '':
                all_paths.add(value_string)
    return all_paths


def exportDependentFiles(target_directory,
                         mtlx_document,
                         mtlx_search_path,
                         ignore_modules=set()):
    # Find all potentially dependent uri's
    src_uris = set()
    for element in mtlx_document.getChildren():
        uri = element.getSourceUri()
        if uri != '':
            src_uris.add(os.path.dirname(uri))

    # Copy all documents associated with uri's except explicitly ignored modules
    for uri in src_uris.difference(ignore_modules):
        docs = getMtlxModuleDocs(uri, mtlx_search_path, absolute=True)
        for doc_path in docs:
            dest_path = os.path.join(target_directory, uri)
            if not os.path.isdir(dest_path):
                os.makedirs(dest_path)
            logger.info('Copying: {src}, {dest}'.format(
                src=doc_path, dest=dest_path))
            shutil.copy(doc_path, dest_path)


def findImageNodes(mtlx_document):
    '''
    Finds all image nodes in a materialx document and returns them as a list
    :param mtlx_document: The document to transform
    :type mtlx_document: mtx.Document
    '''
    it = mtlx_document.traverseTree()
    all_paths = set()
    image_types = {'image', 'tiledimage', 'triplanarprojection'}
    all_image_nodes = []
    for element in it:
        if isinstance(element, mtx.Node) and \
                element.getCategory() in image_types:
            all_image_nodes.append(element)
    return all_image_nodes


def convertSRGBToLinear(mtlx_document, mtlx_search_path):
    '''
    This is a destructive conversion adding an explicit conversion of srgb
    textures to linear between the sampler and the operation using the texture
    It will also convert the texture sampler to have the linear color space
    to make sure this file behaves correctly if viewed in a viewer correctly
    interpreting sRGB textures.
    Note this operation doesn't support hiarc
    THIS OPERATION IS ONLY MEANT TO BE APPLIED ON GRAPHS TO BE VIEWED IN
    VIEWERS NOT SUPPORTING COLORSPACE ANNOTATIONS SUCH AS THE DESIGNER VIEWPORT
    :param mtlx_document: The document to transform
    :type mtlx_document: mtx.Document
    :return:
    '''

    def _addSrgbToLinearConversion(mtlx_node, mtlx_document, mtlx_search_path):
        '''
        Adds srgb output node and changes all input filename properties to be
        in colorspace linear
        :param mtlx_node: the node to do the conversion for
        :type mtlx_node: mtx.Node
        :param mtlx_document: The document the node lives in
        :type mtlx_document: mtx.Document
        :return:
        '''
        # Find all connected nodes
        # Note, this is a pretty expensive operation looking at all nodes in
        # the graph and identifies if it has an upstream connection to the
        # node we are operating on.
        # TODO: Is there a faster way of doing this?
        parent = mtlx_node.getParent()
        assert (isinstance(parent, mtx.NodeGraph))
        affected_nodes = []
        for n in parent.getNodes():
            edge_count = n.getUpstreamEdgeCount()
            for idx in range(0, edge_count):
                e = n.getUpstreamEdge(None, idx)
                upstream = e.getUpstreamElement()
                if upstream == mtlx_node:
                    affected_nodes.append(n)
                    continue

        # Create correction node
        if not mtlxDocContainsModule('alglib', mtlx_document):
            importMtlxDocsForModule('alglib', mtlx_document, mtlx_search_path)
        correction_node = parent.addNode('algsrgb_to_linear',
                                         'correct_cs_' + mtlx_node.getName())
        correction_node.setConnectedNode('in', mtlx_node)

        # Find all nodes connected to the current node's output
        for node in affected_nodes:
            for input in node.getInputs():
                if input.getConnectedNode() == mtlx_node:
                    input.setConnectedNode(correction_node)

        # Find all outputs connected to the affected node
        for o in parent.getOutputs():
            if o.getConnectedNode() == mtlx_node:
                o.setConnectedNode(correction_node)

        # Change the color space setting for filenames on the node to linear
        for p in image.getParameters():
            if p.getType() != 'filename':
                # Skip non-filename paramters
                continue
            cs = p.getColorSpace()
            if cs == 'srgb_texture':
                p.setColorSpace('linear')

    all_image_nodes = findImageNodes(mtlx_document)
    for image in all_image_nodes:
        if image.getNamespace() != '':
            # Only converting image nodes local to this file
            continue
        needs_conversion = False
        needs_no_conversion = False
        for p in image.getParameters():
            if p.getType() != 'filename':
                # Skip non-filename paramters
                continue
            cs = p.getColorSpace()
            if cs == 'srgb_texture':
                needs_conversion = True
            else:
                needs_no_conversion = True
        if needs_conversion and needs_no_conversion:
            # We have inconsistent color spaces on this image
            # Report a warning
            logger.warning('Inconsistent input color spaces on image node {}, '
                           'no conversion applied'.format(
                               image.getName()))
            continue
        if needs_conversion:
            _addSrgbToLinearConversion(image, mtlx_document, mtlx_search_path)


def findRootNode(sd_graph):
    for sd_node in sd_graph.getNodes():
        if _isRoot(sd_node, sd_graph):
            return sd_node
