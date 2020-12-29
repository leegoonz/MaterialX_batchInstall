# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging

from .common import *
from .convertNodeGraphToMdl import convertNodeGraphToMdlBody

logger = logging.getLogger("SDMaterialX")


class MDLGenerationException(BaseException):
    pass


def _generateFunctionSignature(mtx_func_name, mdl_parameters):
    """
    This function creates a string that uniquely identifies a function based on name and parameter types
    In order to identify functions that will cause problems with mdl's support for polymorphism
    :param mtx_func_name:
    :param mdl_parameters:
    :return:
    """
    return mtx_func_name + ','.join(
        [a[1].split(' ')[1] for a in mdl_parameters])


def getMdlOutputNodes():
    result = []
    outputNode_format = \
        "export {mdl_type} output({mdl_type} v, string name){{ return v; }}"
    processedTypes = set()
    for mtx_type, mdl_type in mtlxToMdl_types.items():
        # mdl_type = mtlxToMdl_types[mtx_type]
        # don't output strings and materials.
        if mtx_type in ['string', 'surfaceshader', 'filename']:
            continue
        if mtx_type not in processedTypes:
            processedTypes.add(mtx_type)
            result.append(outputNode_format.format(
                type=mtx_type,
                mdl_type=mdl_type))
    return result


def getMdlInputNodes():
    result = []
    inputNode_format = \
        "export {mdl_type} input_{type}({mdl_type} v, string name){{ return v; }}"
    processedTypes = set()
    for mtx_type, mdl_type in mtlxToMdl_types.items():
        if mtx_type in ['filename', 'surfaceshader']:
            continue
        if mtx_type not in processedTypes:
            processedTypes.add(mtx_type)
            result.append(inputNode_format.format(
                type=mtx_type,
                default=mdlTypes_defaultValues[mdl_type],
                mdl_type=mdl_type))
    return result


def getMdlParameterNodes():
    result = []
    paramNode_format = \
        "export uniform {mdl_type} parameter_{type}(uniform {mdl_type} v, " \
        "string name){{ return v; }}"
    processedTypes = set()
    for mtx_type, mdl_type in mtlxToMdl_types.items():
        if mtx_type in ['filename', 'surfaceshader']:
            continue
        if mtx_type not in processedTypes:
            processedTypes.add(mtx_type)
            result.append(paramNode_format.format(
                type=mtx_type,
                default=mdlTypes_defaultValues[mdl_type],
                mdl_type=mdl_type))
    return result


def getSkippedTypeComment(mtlx_nodeDef, mtlx_typedElement):
    mtlx_nodeName = mtlx_nodeDef.getName()
    mtlx_name = mtlx_typedElement.getName()
    mtlx_type = mtlx_typedElement.getType()
    message = "// MaterialX parameter {name} from node {node_name} " \
              "skipped because it is of type {type}"
    return message.format(
        name=mtlx_name, node_name=mtlx_nodeName, type=mtlx_type)


def getSkippedNodeComment(mtlx_nodeDef):
    mtlx_name = mtlx_nodeDef.getName()
    message = "// Unsupported MaterialX nodedef {name} skipped"
    return message.format(name=mtlx_name)


def isNodeSupported(mtlx_nodeDef):
    '''
    Nodes including color2 and color4 types are not supported at the moment
    We also have a blacklist of nodes not to convert since they depend on unimplemented
    functions in the standard library
    '''
    try:
        nodeTypeSupported = mtlx_nodeDef.getType() in mtlxToMdl_types
        types_to_check = set(mtlxToMdl_types.keys()
                             ).difference(mtlx_skippedTypes)
        interfaceTypesSupported = \
            all(element.getType() in
                types_to_check
                for element in mtlx_nodeDef.getParameters() +
                mtlx_nodeDef.getInputs())
        # Special case to remove mdl ambiguity
        if mtlx_nodeDef.getNodeString() == 'switch':
            if mtlx_nodeDef.getParameter('which').getType() == 'float':
                return False
        return nodeTypeSupported and interfaceTypesSupported
    except BaseException as e:
        logger.warning('Node {} not supported {}'.format(
            mtlx_nodeDef.getName(), str(e)))


def _generateSwizzleBody(out_type, in_type, src_var, swizzle_string_var, warnings):
    def _generateIndices(out_size, in_size):
        if out_size == 0:
            return [[]]
        out_data = []
        prev_data = _generateIndices(out_size - 1, in_size)
        for prev in prev_data:
            for i in range(0, in_size):
                out_data.append(prev + [i])
        return out_data

    def _generateConstructorParamsFromChannels(in_type, out_type, channels, src_var):
        if in_type == 'float':
            return ','.join([src_var] * mdl_vector_sizes[out_type])
        else:
            return ','.join([src_var + '.' + list(mdl_swizzle_names[in_type][0])[c] for c in channels])

    in_type = swizzle_type = in_type.split(' ')[1]
    result = '\n'
    if in_type == 'color3':
        # special case treatment for color inputs since they don't have components in mdl
        result += '    float3 fColor({});\n'.format(src_var)
        src_var = 'fColor'
        in_type = 'float3'
    permutations = _generateIndices(
        mdl_vector_sizes[out_type], mdl_vector_sizes[in_type])
    for iidx, channel_map in enumerate(mdl_swizzle_names[swizzle_type]):
        for idx, channels in enumerate(permutations):
            result += '    '
            result += 'if     ' if (idx == 0 and iidx == 0) else 'else if'
            comparison_format = '({swizzle_var} == \"{swizzle_string}\") return {out_type}({channel_select});\n'
            swizzle_string = ''.join([channel_map[i] for i in channels])
            channel_select = _generateConstructorParamsFromChannels(
                in_type, out_type, channels, src_var)
            result += comparison_format.format(swizzle_var=swizzle_string_var,
                                               swizzle_string=swizzle_string,
                                               out_type=out_type,
                                               channel_select=channel_select)
    result += '    else return {}(0.0);\n'.format(out_type)
    return result


def initValue(mdl_type, value):
    """
    Simple cast of value to mdl_type.
    TODO: Doesn't handle matrices and strings
    """
    # if '2' in mdl_type:
    #     return mdl_type + '(' + value + ', ' + value + ')'
    # elif '3' in mdl_type:
    #     return mdl_type + '(' + value + ', ' + value + ', ' + value + ')'
    # else:
    return mdl_type + '(' + value + ')'


def getMdlBody(
        mtx_func_name, mdl_return_type, mdl_parameters,
        body_annotations, node_graph, warnings,
        clashing_nodes, used_mdl_modules):
    body = ''
    description = ''

    # for mdl_name, mdl_type, default_val in mdl_parameters:
    if mdl_return_type in mdl_unsupported_types:
        # TODO!! not supported yet
        pass
    elif mtx_func_name in mdl_ubershader_implementation_map:
        # Special list of hard-coded implementations
        return mdl_ubershader_implementation_map[mtx_func_name]
    elif mdl_return_type == 'material':
        # Special case to deal with materials since they have
        # slightly odd semantics
        warnings.append(
            '// Error: material type nodes are dummy implemented'.format(
                mdl_return_type=mdl_return_type,
                mtx_func_name=mtx_func_name))
        # Special case for materials since it has a crazy syntax
        if 'multiply' in mtx_func_name:
            warnings.append(
                '// Error: material multiplication polymorphy not implemented')
        return 'mtlx::utilities::dummyMaterial();'
    else:
        # MATH NODES #
        simple_unary_mappings = {
            'absval': 'math::abs',
            'floor': 'math::floor',
            'ceil': 'math::ceil',
            'sin': 'math::sin',
            'cos': 'math::cos',
            'tan': 'math::tan',
            'asin': 'math::asin',
            'acos': 'math::acos',
            'sqrt': 'math::sqrt',
            'sign': 'math::sign',
            'ln': 'math::log',
            'exp': 'math::exp',
            'normalize': 'math::normalize',
            'magnitude': 'math::length',
            'transpose': 'math::transpose',
            'dot': '',
        }
        simple_binary_mappings_cast = {
            'min': 'math::min',
            'max': 'math::max',
        }
        simple_binary_mappings_no_cast = {
            'dotproduct': 'math::dot',
            'crossproduct': 'math::cross',
            'atan2': 'math::atan2',
        }
        if mtx_func_name in simple_unary_mappings:
            if mdl_return_type == 'color3':
                body += '\n    return color3({op}(float3(in_)));\n'.format(
                    op=simple_unary_mappings[mtx_func_name])
            else:
                body += '\n    return {op}(in_);\n'.format(
                    op=simple_unary_mappings[mtx_func_name])
        elif mtx_func_name in simple_binary_mappings_cast:
            body += '\n    return {op}(in1, {mdl_return_type}(in2));\n'.format(
                op=simple_binary_mappings_cast[mtx_func_name],
                mdl_return_type=mdl_return_type)
        elif mtx_func_name in simple_binary_mappings_no_cast:
            body += '\n    return {op}(in1, in2);\n'.format(
                op=simple_binary_mappings_no_cast[mtx_func_name])
        elif mtx_func_name == 'add':
            body += '\n    return (in1 + {mdl_return_type}(in2));\n'
        elif mtx_func_name == 'subtract':
            body += '\n    return (in1 - {mdl_return_type}(in2));\n'
        elif mtx_func_name == 'multiply':
            body += '\n    return (in1 * {mdl_return_type}(in2));\n'
        elif mtx_func_name == 'modulo':
            description = \
                'The remaining fraction after dividing the incoming ' \
                'float/color/vector by the constant amount and subtracting ' \
                'the integer portion. The modulo amount cannot be 0. '
            if mdl_return_type == 'color3':
                # not implemented in MDL for colors
                body += '\n    return color3(float3(in1) - float3(in2) * math::floor(float3(in1)/float3(in2)));\n'
            else:
                body += '\n    return in1 - in2 * math::floor(in1/in2);\n'
        elif mtx_func_name == 'power':
            body += '\n    return math::pow(in1, {mdl_return_type}(in2));\n'
        elif mtx_func_name == 'clamp':
            body += '\n    return math::clamp(in_, low, high);\n'
        elif mtx_func_name == 'smoothstep':
            if mdl_return_type == 'color3':
                body += '\n    return color3(math::smoothstep(' \
                        'float3(low), float3(high), float3(in_)));\n'
            else:
                body += '\n    return math::smoothstep(' \
                        '{mdl_return_type}(low), ' \
                        '{mdl_return_type}(high), in_);\n'
        elif mtx_func_name == 'remap':
            # TODO: cannot use negative values on color3 remapping, unless you
            # connect float nodes
            body += '\n    return outlow + (in_ - inlow) * ' \
                    '(outhigh - outlow) / ' \
                    '(inhigh - inlow);\n'
        elif mtx_func_name == 'divide':
            if mdl_return_type not in ['float3x3', 'float4x4']:
                body += '\n    return (in1 / {mdl_return_type}(in2));\n'
        elif mtx_func_name == 'invert':
            if mdl_return_type not in ['float3x3', 'float4x4']:
                body += '\n    return {mdl_return_type}(amount) - in_;\n'

        # STATE NODES #
        elif mtx_func_name == 'texcoord':
            if mdl_return_type == 'float2':
                body += '\n    float3 tmp = state::texture_coordinate(' \
                        'index);\n'
                body += '    return float2(tmp[0],tmp[1]);\n'
            elif mdl_return_type == 'float3':
                body += '\n    return (state::texture_coordinate(' \
                        'index));\n'
        elif mtx_func_name == 'position':
            body += '\n    return state::transform_point(' \
                    'state::coordinate_internal, ' \
                    'mtlx::utilities::getSpaceByString(space), ' \
                    'state::position());\n'
        elif mtx_func_name == 'normal':
            body += '\n    return math::normalize(' \
                    'state::transform_normal(' \
                    'state::coordinate_internal, ' \
                    'mtlx::utilities::getSpaceByString(space), ' \
                    'state::normal()));\n'
        elif mtx_func_name == 'tangent':
            body += '\n    return math::normalize(' \
                    'state::transform_vector(' \
                    'state::coordinate_internal, ' \
                    'mtlx::utilities::getSpaceByString(space), ' \
                    'state::texture_tangent_u(index)));\n'
        elif mtx_func_name == 'bitangent':
            body += '\n    return math::normalize(' \
                    'state::transform_vector(' \
                    'state::coordinate_internal, ' \
                    'mtlx::utilities::getSpaceByString(space), ' \
                    'state::texture_tangent_v(index)));\n'
        elif mtx_func_name == 'time':
            body += '\n    return state::animation_time();\n'
        elif mtx_func_name in ['geompropvalue', 'geomattrvalue']:
            # TODO: legal but not supported in mdl
            body += '\n    return {mdl_return_type}(' + \
                    mdlTypes_defaultValues[mdl_return_type] + ');\n'

        # TEXTURING NODES #
        elif mtx_func_name == 'image':
            type_format = 'color' if mdl_return_type == 'color3' \
                else mdl_return_type
            body += '\n    if(tex::texture_isvalid(file)) {\n'
            body += '        return tex::lookup_{type_format}(\n'. \
                format(type_format=type_format)
            body += '            file, texcoord, ' \
                    'mtlx::utilities::get_wrap_mode(' \
                    'uaddressmode),mtlx::utilities::get_wrap_mode(' \
                    'vaddressmode));\n'
            body += '    } else {\n'
            body += '        return default_;\n'
            body += '    }\n'
        elif mtx_func_name == 'tiledimage':
            type_format = 'color' if mdl_return_type == 'color3' \
                else mdl_return_type
            body += '\n    if(tex::texture_isvalid(file)) {\n'
            body += '        return tex::lookup_{type_format}(\n'. \
                format(type_format=type_format)
            body += '            file, (texcoord*uvtiling)-' \
                    'uvoffset);\n'
            body += '    } else {\n'
            body += '        return default_;\n'
            body += '    }\n'
        elif mtx_func_name == 'triplanarprojection':
            type_format = 'color' if mdl_return_type == 'color3' \
                else mdl_return_type
            template = '''
    {mdl_return_type} filex_val;
    if (tex::texture_isvalid(filex)) {{
        filex_val = tex::lookup_{type_format}(
            filex, float2(position[1], position[2]));
    }} else {{
        filex_val = default_;
    }}
    {mdl_return_type} filey_val;
    if (tex::texture_isvalid(filey)) {{
        filey_val = tex::lookup_{type_format}(
            filey, float2(position[0], position[2]));
    }} else {{
        filey_val = default_;
    }}
    {mdl_return_type} filez_val;
    if (tex::texture_isvalid(filez)) {{
        filez_val = tex::lookup_{type_format}(
            filez, float2(position[0], position[1]));
    }} else {{
        filez_val = default_;
    }}

    float3 blend = math::abs(math::normalize(normal));
    {mdl_return_type} accum =
        filex_val*blend.x + filey_val*blend.y + filez_val*blend.z;
    return accum/(blend.x+blend.y+blend.z);
'''
            body += template.format(
                mdl_return_type=mdl_return_type,
                type_format=type_format)

        # PROCEDURAL NODES #
        elif mtx_func_name == 'ramplr':
            body += '\n    return math::lerp(valuel, valuer, ' \
                    'math::clamp(texcoord.x, 0.0, 1.0));\n'
        elif mtx_func_name == 'ramptb':
            body += '\n    return math::lerp(valuet, valueb, ' \
                    'math::clamp(texcoord.y, 0.0, 1.0));\n'
        elif mtx_func_name == 'ramp4':
            body += \
                '\n    float ss = math::clamp(texcoord.x, 0, 1);\n' \
                '    float tt = math::clamp(texcoord.y, 0, 1);\n' \
                '    return math::lerp(\n' \
                '        math::lerp(valuetl, valuetr, ss),\n' \
                '        math::lerp(valuebl, valuebr, ss), tt);\n'
        elif mtx_func_name == 'splitlr':
            body += '\n    return math::lerp(valuel, valuer,\n' \
                    '        math::step(center, math::clamp(' \
                    'texcoord.x,0,1)));\n'
        elif mtx_func_name == 'splittb':
            body += '\n    return math::lerp(valuet, valueb,\n' \
                    '        math::step(center, math::clamp(' \
                    'texcoord.y,0,1)));\n'
        elif mtx_func_name in ['noise2d', 'noise3d']:
            posParam = 'texcoord' if mtx_func_name == 'noise2d' else 'position'
            type_suffix = 'float3'
            if mdl_return_type == 'float':
                type_suffix = 'float'
            body += \
                '\n    {mdl_return_type} ns = ' \
                'mtlx::utilities::to_{mdl_return_type}' \
                '(mtlx::utilities::perlin_noise_{type_suffix}({posParam}));\n' \
                '    return mtlx::utilities::to_{mdl_return_type}(amplitude*(' \
                'ns - {mdl_return_type}(pivot)) + ' \
                '{mdl_return_type}(pivot));\n'.format(
                    mdl_return_type=mdl_return_type,
                    type_suffix=type_suffix,
                    posParam=posParam)
        elif mtx_func_name == 'fractal3d':
            body += \
                '\n    return mtlx::utilities::fBm_{mdl_return_type}(' \
                'position, octaves, lacunarity, ' \
                'diminish) * amplitude;\n'
        elif mtx_func_name == 'cellnoise2d':
            body += '\n    return mtlx::utilities::cellnoise(texcoord);\n'
        elif mtx_func_name == 'cellnoise3d':
            body += '\n    return mtlx::utilities::cellnoise(position);\n'

        # TRANFORMS #
        elif mtx_func_name in [
                'transformpoint', 'transformvector', 'transformnormal']:
            mdl_name, mdl_type, default_val, _ = mdl_parameters[1]
            if mdl_name == 'mat':
                # Identify matrix size
                mat_size = int(mdl_type[-1:])
                _, src_type, _, _ = mdl_parameters[0]
                vec_size = int(src_type[-1:])
                if not mat_size == vec_size:
                    # TODO: this is now legal, need to support it at some point
                    warnings.append(
                        '// Error: Ignoring incompatible vector sizes')
                body += '\n    return in_*mat;\n'
            else:
                body += '\n' \
                        '    state::coordinate_space fromMdlSpace = ' \
                        'mtlx::utilities::getSpaceByString(fromspace);\n' \
                        '    state::coordinate_space toMdlSpace = ' \
                        'mtlx::utilities::getSpaceByString(tospace);\n'
                if mtx_func_name == 'transformpoint':
                    body += \
                        '    return mtlx::utilities::to_{mdl_return_type}(' \
                        'state::transform_point(' \
                        'fromMdlSpace, toMdlSpace, ' \
                        'mtlx::utilities::to_float3(in_)));\n'
                elif mtx_func_name == 'transformvector':
                    body += \
                        '    return mtlx::utilities::to_{mdl_return_type}(' \
                        'state::transform_vector(' \
                        'fromMdlSpace, toMdlSpace, ' \
                        'mtlx::utilities::to_float3(in_)));\n'
                elif mtx_func_name == 'transformnormal':
                    body += \
                        '    return mtlx::utilities::to_{mdl_return_type}(' \
                        'state::transform_normal(' \
                        'fromMdlSpace, toMdlSpace, ' \
                        'mtlx::utilities::to_float3(in_)));\n'
        elif mtx_func_name == 'determinant':
            body += '\n    return mtlx::utilities::determinant(in_);\n'
        elif mtx_func_name == 'rotate':
            body += '\n    return mtlx::utilities::rotate_{mdl_return_type}(' \
                    'in_, amount'
            if mdl_return_type == 'float3':
                body += ', axis'
            body += ');\n'

        elif mtx_func_name == 'determinant':
            body += '\n    return mtlx::utilities::determinant(in_);\n'
        elif mtx_func_name == 'rotate':
            body += '\n    return mtlx::utilities::rotate_{mdl_return_type}(' \
                    'in_, amount'
            if mdl_return_type == 'float3':
                body += ', axis'
            body += ');\n'
        elif mtx_func_name == 'normalmap':
            body += '\n    float3 result;\n' \
                '    if (space == "tangent")\n' \
                '    {\n' \
                '        float3 v = in_ * 2.0 - 1.0;\n' \
                '        float3 B = normalize(math::cross(normal, tangent));\n' \
                '        result = normalize(tangent * v.x * scale + B * v.y * scale + normal * v.z);\n' \
                '    }\n' \
                '    // Object space\n' \
                '    else\n' \
                '    {\n' \
                '        float3 n = in_ * 2.0 - 1.0;\n' \
                '        result = normalize(n);\n' \
                '    }\n' \
                '    return result;\n'
        # TODO: COLOR CORRECTION NODES #
        # all float4 implementations will need special treatment for alpha
        elif mtx_func_name == 'luminance':
            body += '\n    return color3(' \
                    'math::dot(float3(in_), float3(lumacoeffs)));\n'
        elif mtx_func_name == 'rgbtohsv':
            body += '\n    return mtlx::utilities::rgb2hsv(in_);\n'
        elif mtx_func_name == 'hsvtorgb':
            body += '\n    return mtlx::utilities::hsv2rgb(in_);\n'
        elif mtx_func_name == 'contrast':
            body += '\n    return (in_ - pivot)*' \
                    '{mdl_return_type}(amount) + pivot;\n'
        elif mtx_func_name == 'range':
            body += '\n' \
                    '    {mdl_return_type} retval = outlow + (in_ - inlow)*' \
                    '(outhigh - outlow)/(inhigh - inlow);\n' \
                    '    retval = math::pow(retval, 1.0/gamma);\n' \
                    '    if (doclamp) \n' \
                    '        retval = math::clamp(retval, outlow, outhigh);\n' \
                    '    return retval;\n'
        elif mtx_func_name == 'hsvadjust':
            body += '\n' \
                    '    float3 hsvval = float3(mtlx::utilities::rgb2hsv(in_));\n' \
                    '    hsvval = float3(hsvval.x+amount.x, ' \
                    'hsvval.y*amount.y, hsvval.z*amount.z);\n' \
                    '    return mtlx::utilities::hsv2rgb(color3(hsvval));\n'
        elif mtx_func_name == 'saturate':
            body += '\n' \
                    '    return math::lerp(\n' \
                    '       color3(math::dot(float3(in_), float3(lumacoeffs))),' \
                    ' in_, amount);\n'
        elif mtx_func_name == 'premult':
            body += '\n    return in_*alpha;\n'
        elif mtx_func_name == 'unpremult':
            body += '\n    return in_/alpha;\n'

        # COMPOSITING NODES #
        elif mtx_func_name == 'mix':
            body += '\n    return math::lerp(bg, fg, mix);\n'
        elif mtx_func_name == 'plus':
            body += '\n    return math::lerp(bg, bg+fg, mix);\n'
        elif mtx_func_name == 'minus':
            body += '\n    return math::lerp(bg, bg-fg, mix);\n'
        elif mtx_func_name == 'difference':
            body += '\n    return math::lerp(bg, math::abs(bg-fg), mix);\n'
        elif mtx_func_name == 'burn':
            body += '\n    return math::lerp(bg, ' \
                    '{mdl_return_type}(1.0)-({mdl_return_type}(1.0)-bg)/fg, mix);\n'
        elif mtx_func_name == 'dodge':
            body += '\n    return math::lerp(bg, ' \
                    'bg/({mdl_return_type}(1.0)-fg), mix);\n'
        elif mtx_func_name == 'screen':
            body += '\n    return math::lerp(bg, bg+fg-bg*fg, mix);\n'
        elif mtx_func_name == 'overlay':
            ct = 'float3' if mdl_return_type == 'color3' else 'float'
            overlaybody = '\n    {ct} upper, lower, mask, overlayval;\n'
            overlaybody += '    {ct} fg_ = {ct}(fg);\n'
            overlaybody += '    {ct} bg_ = {ct}(bg);\n'
            overlaybody += '    lower = 2.0*bg_*fg_;\n'
            overlaybody += '    upper = bg_+fg_-bg_*fg_;\n'
            overlaybody += '    mask = math::step({ct}(.5), fg_);\n'
            overlaybody += '    overlayval = math::lerp(lower, upper, mask);\n'
            overlaybody = overlaybody.format(ct=ct)
            body += overlaybody
            body += '    return {mdl_return_type}(math::lerp(bg, overlayval, mix));\n'
        elif mtx_func_name == 'inside':
            body += '\n    return in_*mask;\n'
        elif mtx_func_name == 'outside':
            body += '\n    return in_*(1.0-mask);\n'
        elif mtx_func_name == 'compare':
            body += '\n    float mask = math::step(cutoff, intest);\n'
            body += '    return math::lerp(in1, in2, mask);\n'

        # SWIZZLE NODES #
        elif mtx_func_name.startswith('combine'):
            # special cases. Check type of first parameter
            param_name, param_type, param_default_val, _ = mdl_parameters[0]
            if mdl_return_type == 'float4' and param_type.endswith('float3'):
                body += '\n    return float4(in1.x, in1.y, in1.z, in2);\n'
            elif mdl_return_type == 'float4' and param_type.endswith('float2'):
                body += '\n    return float4(in1.x, in1.y, in2.x, in2.y);\n'
            # TODO: color2 and color4
            else:
                # standard cases: combine floats
                if len(mdl_parameters) == 2:
                    body += '\n    return {mdl_return_type}(in1, in2);\n'
                elif len(mdl_parameters) == 3:
                    body += '\n    return {mdl_return_type}(in1, in2, in3);\n'
                elif len(mdl_parameters) == 4:
                    body += '\n    return {mdl_return_type}(in1, in2, in3, in4);\n'
        elif mtx_func_name == 'switch':
            if len(mdl_parameters) == 3:
                # boolean version
                body += '\n    if (which) return in2;\n'
            else:
                # 5 inputs plus a switch int or float
                body += '\n'
                if mdl_parameters[5][1].endswith('float'):
                    body += '    int which_ = math::floor(which);\n'
                else:
                    body += '    int which_ = which;\n'

                body += '    if (which_ == 1) return in2;\n'
                body += '    if (which_ == 2) return in3;\n'
                body += '    if (which_ == 3) return in4;\n'
                body += '    if (which_ >= 4) return in5;\n'
            body += '    return in1;\n'
        elif mtx_func_name == 'swizzle':
            body += _generateSwizzleBody(
                mdl_return_type, mdl_parameters[0][1], 'in_', 'channels',
                warnings)
        elif mtx_func_name == 'convert':
            body += '    return mtlx::utilities::to_{mdl_return_type}(in_);\n'

        # OTHER NODES #
        elif mtx_func_name == 'constant':
            body += '\n    return value;\n'
        elif mtx_func_name == 'ifequal':
            body += '\n    return (value1 == value2) ? in1 : in2;\n'
        elif mtx_func_name == 'ifgreater':
            body += '\n    return (value1 > value2) ? in1 : in2;\n'
        elif mtx_func_name == 'ifgreatereq':
            body += '\n    return (value1 >= value2) ? in1 : in2;\n'
        elif mtx_func_name == 'rotate2d':
            body += '\n    float rotationRadians = math::radians(amount);'
            body += '\n    float sa = math::sin(rotationRadians);'
            body += '\n    float ca = math::cos(rotationRadians);'
            body += '\n    return float2(ca*in_.x + sa*in_.y, -sa*in_.x + ca*in_.y);\n'
        elif mtx_func_name == 'rotate3d':
            body += '\n    float rotationRadians = math::radians(amount);'
            body += '\n    axis = normalize(axis);'
            body += '\n    float s = math::sin(rotationRadians);'
            body += '\n    float c = math::cos(rotationRadians);'
            body += '\n    float oc = 1.0 - c;'
            body += '\n    float4x4 rot = float4x4('
            body += '\n         oc * axis.x * axis.x + c, oc * axis.x * axis.y - axis.z * s, oc * axis.z * axis.x + axis.y * s, 0.0,'
            body += '\n         oc * axis.x * axis.y + axis.z * s, oc * axis.y * axis.y + c, oc * axis.y * axis.z - axis.x * s, 0.0,'
            body += '\n         oc * axis.z * axis.x - axis.y * s, oc * axis.y * axis.z + axis.x * s, oc * axis.z * axis.z + c, 0.0,'
            body += '\n         0.0, 0.0, 0.0, 1.0);'
            body += '\n    float4 result = (rot * float4(in_.x, in_.y, in_.z, 1.0));'
            body += '\n    return float3(result.x, result.y, result.z);\n'
        elif node_graph:
            body += convertNodeGraphToMdlBody(
                node_graph, warnings, clashing_nodes, used_mdl_modules)

    if body:
        if '{mdl_return_type}' in body:
            body = body.format(mdl_return_type=mdl_return_type)
        # Many annotations are not yes supported at the node
        # level, only at the param level
        body_annotations.append(
            '    anno::display_name("Matx {name}"),\n'.format(
                name=mtx_func_name))
        body_annotations.append(
            '    anno::description("{description}'
            'MaterialX compliant node"),\n'.format(description=description))
        body_annotations.append('    anno::author("Allegorithmic")\n')
        return body

    else:
        # unrecognized node, just return default
        warnings.append(
            '// Error: Implementation for {mdl_return_type} {mtx_func_name} '
            'missing'.format(
                mdl_return_type=mdl_return_type,
                mtx_func_name=mtx_func_name))

        return ' return {mdl_return_type}({value}); '.format(
            mdl_return_type=mdl_return_type,
            value=mdlTypes_defaultValues[mdl_return_type])


def formatMdlFunc(mtx_func_name,
                  node_def,
                  node_graph,
                  mdl_parameters,
                  warnings,
                  clashing_nodes,
                  used_mdl_modules):
    mdl_return_type = getMdlType(node_def)
    if mdl_return_type.startswith("texture_2d"):
        warnings.append(
            '// skipping {mtx_func_name}, cannot return texture_* types'.
            format(mtx_func_name=mtx_func_name))
        return ''
    signature = getMdlSignature(mtx_func_name,
                                mdl_parameters)
    body_annotations = []
    body = getMdlBody(node_def.getNodeString(),
                      mdl_return_type,
                      mdl_parameters,
                      body_annotations,
                      node_graph,
                      warnings,
                      clashing_nodes,
                      used_mdl_modules)
    body_annotations_string = ''
    if body_annotations:
        body_annotations_string = '\n[[\n' + ''.join(body_annotations) + ']]\n'

    if mdl_return_type == 'material':
        # Special case code for material functions
        mdlFunc_format = \
            "export {return_type} {signature}{body_annotations}={body}"
        return mdlFunc_format.format(
            return_type=mdl_return_type,
            signature=signature,
            body_annotations=body_annotations_string,
            body=body)
    else:
        mdlFunc_format = \
            "export {return_type} {signature}{body_annotations}{{{body}}}"
        return mdlFunc_format.format(
            return_type=mdl_return_type,
            signature=signature,
            body_annotations=body_annotations_string,
            body=body)


def _makeOutputMdlFunction(mdl_type):
    '''
    Generates a function for an output node for subgraphs
    :param mdl_type: The MDL type to generate for
    :return: str
    '''
    return 'export {mdl_type} subgraph_output(varying {mdl_type} p)\n' \
           '{{\n' \
           '    return p;\n' \
           '}}\n'.format(mdl_type=mdl_type)


def mtlx2mdl_shared():
    """generate shared mdl file"""
    retval = getMdlVersion() + '\n'
    retval += '\n// shared library for mdl on substance\n'
    retval += '\n// types declarations\n'
    for typedef in mdlCustomTypes:
        retval += typedef + '\n'
    # retval += '\n// output nodes\n'
    # for output_node in getMdlOutputNodes():
    #     retval += output_node + '\n'
    # retval += '\n// input nodes\n'
    # for input_node in getMdlInputNodes():
    #     retval += input_node + '\n'
    # retval += '\n// parameter nodes\n'
    # for parameter_node in getMdlParameterNodes():
    #     retval += parameter_node + '\n'

    # Create proxies for returning data from a subgraph
    for mtlx_type, mdl_type in mtlxToMdl_types.items():
        if mdl_type not in {'material', 'texture_2d'}:
            retval += _makeOutputMdlFunction(mdl_type)
    return retval


def _findFirstLocalImplementation(node_def, mtlx_doc, warnings):
    implementations = mtlx_doc.getMatchingImplementations(
        node_def.getName())
    local_implementations = []
    for i in implementations:
        if i.getSourceUri() == '':
            local_implementations.append(i)
    if len(local_implementations) == 0:
        return None
    if len(local_implementations) > 1:
        warnings.append('// Multiple local implementations found for function: '
                        '{node_def_name}. Using {node_graph_name}'.format(
                            node_def_name=node_def.getNodeString(),
                            node_graph_name=local_implementations[0].getName()))
    return local_implementations[0]


def mtlx2mdl_library(module_name,
                     shared_name,
                     mtlx_search_path,
                     exception_on_omissions=False):
    from .modules import loadMtlxDocsForModule, \
        importMtlxDocsForModule, getAllMtlxModules, hashMtlxDocsForModule, generateSourceHashString

    def _definedInCurrentFile(element):
        return element.getSourceUri() == ''

    import MaterialX

    doc = MaterialX.createDocument()

    loadMtlxDocsForModule(module_name, doc, mtlx_search_path)
    node_defs = doc.getNodeDefs()
    module_doc_hash = hashMtlxDocsForModule(module_name, mtlx_search_path)
    header = generateSourceHashString(module_doc_hash)
    # Import the standard library
    header += getMdlVersion() + '\n'

    header += 'using mtlx::{module} import *;\n'.format(module=shared_name)
    header += 'import mtlx::utilities::*;\n'
    header += 'import math::*;\n'
    header += 'import anno::*;\n'
    header += 'import base::*;\n'
    header += 'import tex::*;\n'
    header += 'import state::*;\n'
    header += 'import df::*;\n'
    header += 'import alg::base::core::*;\n'
    header += 'import alg::base::annotations::*;\n'

    # Import all modules in the materialx search path to identify any clashing
    # symbols and deal with them in an mdl friendly way
    all_modules = getAllMtlxModules(mtlx_search_path)

    for module in all_modules:
        if not module == module_name:
            # Read and import namespaces from a temp document
            importMtlxDocsForModule(module, doc, mtlx_search_path)

    retval = getGeomPropDefs(doc)

    processed_nodes = []

    # These sets keeps track of node defs that will cause problems as mdl
    # functions because they have identical
    # names and parameter lists but different return values
    known_signatures = {}
    clashing_nodes = set()

    used_mdl_modules = set()
    # Identify clashing nodes
    # Note that we go through both the node defs in all documents here to
    # make sure they are identified in all namespaces
    for node_def in doc.getNodeDefs():
        if isNodeSupported(node_def):
            warnings = []
            mdl_parameters = getMdlParameters(node_def,
                                              warnings,
                                              used_mdl_modules)
            mtx_func_name = correctMdlFunctionForReservedWords(
                node_def.getNodeString())
            function_signature = _generateFunctionSignature(
                mtx_func_name, mdl_parameters)

            # Check if we are having a signature clash or if the node is
            # forced to have type decorated for usability reasons
            if mtx_func_name in mtlx_force_type_decoration:
                clashing_nodes.add(node_def)
            elif function_signature in known_signatures:
                clashing_nodes.add(node_def)
                clashing_nodes.add(known_signatures[function_signature])
            else:
                known_signatures[function_signature] = node_def
    # Generate all nodes
    for node_def in node_defs:
        if not _definedInCurrentFile(node_def):
            # Skip node defs that are not from the source documents
            continue
        warnings = []
        node_graph = _findFirstLocalImplementation(node_def, doc, warnings)
        # node_graph = None if len(implementations) == 0 else implementations[0]
        if isNodeSupported(node_def):
            mdl_parameters = getMdlParameters(node_def,
                                              warnings,
                                              used_mdl_modules)
            mtx_func_name = correctMdlFunctionForReservedWords(
                node_def.getNodeString())
            if node_def in clashing_nodes:
                mtx_func_name += '_' + node_def.getType()
            mdlFunc = formatMdlFunc(
                mtx_func_name,
                node_def,
                node_graph,
                mdl_parameters,
                warnings,
                clashing_nodes,
                used_mdl_modules) + '\n'
            omit = False
            for warning in warnings:
                retval += warning + '\n'
                if warning.lower().find('error') != -1:
                    omit = True
            if omit:
                retval += "/*" + mdlFunc + "*/\n"
                if exception_on_omissions:
                    raise MDLGenerationException('\n'.join(warnings))
            else:
                retval += mdlFunc
            processed_nodes.append(node_def)
        else:
            if exception_on_omissions:
                raise MDLGenerationException(
                    getSkippedNodeComment(node_def))
            retval += getSkippedNodeComment(node_def) + '\n'

    # Insert import statements for used modules in the header
    # Sorted to be deterministic
    for imp_module in sorted(used_mdl_modules):
        header += 'import {}::*;\n'.format(imp_module)

    return header + retval
