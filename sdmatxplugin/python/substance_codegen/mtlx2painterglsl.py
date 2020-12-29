# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import MaterialX as mx
import MaterialX.PyMaterialXGenShader as mxgen
import MaterialX.PyMaterialXGenGlsl as mxglslgen
import io
import os
import shutil
from substance_codegen.glslgen import load_impl_libraries_rec, get_bound_node_graph_and_def, MTLX2GLSLException, generate_node, \
    remove_main, remove_version, remove_vertex_data, replace_symbols, call_node_graph, GLSLScope, get_graph_prefix, subtract_prefix
import logging

logger = logging.getLogger("SDMaterialX")


class MTLXPainterGLSLException(MTLX2GLSLException):
    pass


def _find_all_samplers(shader, node_graph):
    pixel_stage = shader.getStage(mxgen.PIXEL_STAGE)
    input_blocks = pixel_stage.getInputBlocks()
    uniform_blocks = pixel_stage.getUniformBlocks()
    public_uniforms = uniform_blocks.get("PublicUniforms", None)
    result = []
    for port in public_uniforms:
        if port.getType().getName() == "filename":
            name = port.getName()
            cropped_name = name[0:name.rfind('_')]
            node = node_graph.getNode(cropped_name)
            if node:
                usage = node.getAttribute("GLSLFX_usage")
                result.append((name, usage))
    return result


_usage_mapping = {
    'ambientOcclusion': 'channel_ambientocclusion',
    'anisotropyAngle': 'channel_anisotropyangle',
    'anisotropyLevel': 'channel_anisotropylevel',
    'baseColor': 'channel_basecolor',
    'blendingmask': 'channel_blendingmask',
    'diffuse': 'channel_diffuse',
    'displacement': 'channel_displacement',
    'emissive': 'channel_emissive',
    'glossiness': 'channel_glossiness',
    'height': 'channel_height',
    'IOR': 'channel_ior',
    'metallic': 'channel_metallic',
    'normal': 'channel_normal',
    'opacity': 'channel_opacity',
    'reflection': 'channel_reflection',
    'roughness': 'channel_roughness',
    'scattering': 'channel_scattering',
    'specular': 'channel_specular',
    'specularLevel': 'channel_specularLevel',
    'transmissive': 'channel_transmissive',
    'user0': 'channel_user0',
    'user1': 'channel_user1',
    'user2': 'channel_user2',
    'user3': 'channel_user3',
    'user4': 'channel_user4',
    'user5': 'channel_user5',
    'user6': 'channel_user6',
    'user7': 'channel_user7',
    'texture_ambientocclusion': 'texture_ambientocclusion',
    'texture_curvature': 'texture_curvature',
    'texture_id': 'texture_id',
    'texture_normal': 'texture_normal',
    'texture_normal_ws': 'texture_normal_ws',
    'texture_position': 'texture_position',
    'texture_thickness': 'texture_thickness'
}


def _rename_painter_samplers(input_stream,
                             output_stream,
                             shader_ref,
                             shader,
                             mtlx_doc):
    node_graph, node_def, imp_node_graph = get_bound_node_graph_and_def(
        shader_ref, mtlx_doc)
    all_samplers = _find_all_samplers(shader, imp_node_graph)
    symbols_to_replace = {}
    for node, usage in all_samplers:
        sampler = _usage_mapping.get(usage, None)
        if sampler:
            symbols_to_replace["sampler2D " + node] = "SamplerSparse " + node
            symbols_to_replace["(" + node] = "(" + node + ".tex"
    replace_symbols(input_stream, output_stream, symbols_to_replace)


def _get_painter_sampler_name(usage):
    if usage in _usage_mapping:
        return "param auto " + _usage_mapping[usage]
    else:
        return "param custom {\"default\":\"empty\", \"usage\":\"texture\", \"label\":\"" + usage + "\"}"


def _wrap_mtlx_name(value_string):
    split_val = value_string.split(',')
    if len(split_val) == 1:
        return value_string
    else:
        return '[' + value_string + ']'


def _get_painter_metadata_line(line, shader, node_graph, prefix):
    _, type_name, name = [a.replace(';', '') for a in (line.split(' ')[:3])]
    if type_name in ['SamplerSparse', 'sampler2D']:
        cropped_name = name[0:name.rfind('_')]
        node = node_graph.getNode(cropped_name)
        if not node:
            raise MTLXPainterGLSLException(
                'Sampler node not found for exposed sampler {}'.format(cropped_name))
        usage = node.getAttribute('GLSLFX_usage')
        return '//: ' + _get_painter_sampler_name(usage)
    else:
        node_def = node_graph.getNodeDef()
        # cropped_name = name[name.find('_') + 1:]
        cropped_name = subtract_prefix(name, prefix)
        input = node_def.getInput(cropped_name)
        param = node_def.getParameter(cropped_name)
        value_elem = input if input else param
        if not value_elem:
            raise MTLXPainterGLSLException(
                'Input node not found for exposed uniform {}'.format(cropped_name))
        default_val = _wrap_mtlx_name(value_elem.getValueString())
        result = '//: param custom {\"default\":' + \
            default_val + ', \"label\":\"' + cropped_name + '\"'
        if value_elem.getType() == 'color3':
            result += ', \"widget\":\"color\"'
        else:
            uimin = value_elem.getAttribute('uimin')
            uimax = value_elem.getAttribute("uimax")
            if uimin != '' and uimax != '':
                result += ', \"min\":' + \
                    _wrap_mtlx_name(uimin) + ', \"max\":' + \
                    _wrap_mtlx_name(uimax)
        return result + '}'


def _append_painter_uniform_metadata(input_stream,
                                     output_stream,
                                     shader_ref,
                                     shader,
                                     mtlx_doc):
    node_graph, node_def, imp_node_graph = get_bound_node_graph_and_def(
        shader_ref, mtlx_doc)
    for line in input_stream.readlines():
        if line.startswith('uniform '):
            metadata_line = _get_painter_metadata_line(
                line, shader, imp_node_graph, get_graph_prefix(node_graph)) + '\n'
            output_stream.write(metadata_line)
        output_stream.write(line)


def _append_painter_entry_point(input_stream,
                                output_stream,
                                parallax_support,
                                shader,
                                root_node_def,
                                shader_ref,
                                surface_shader_node_def,
                                painter_template_directory):
    # TODO: Split out strings as data
    output_stream.writelines(l + '\n' for l in [
        'import lib-sampler.glsl',
        'import lib-pbr.glsl',
        'import lib-emissive.glsl',
        'import lib-utils.glsl',
        '',
        '//: param auto scene_original_radius',
        'uniform float scene_original_radius;',
    ])
    shutil.copyfileobj(input_stream, output_stream)
    output_stream.write('void shade(V2F inputs)\n')
    tab_level = [0]
    with GLSLScope(output_stream, tab_level):
        call_node_graph(output_stream, True, parallax_support, shader, root_node_def, shader_ref,
                        surface_shader_node_def, tab_level, True)
        node_string = surface_shader_node_def.getNodeString()
        template_file_path = os.path.join(
            painter_template_directory, '{}_template.glsl'.format(node_string))
        if not os.path.isfile(template_file_path):
            raise MTLXPainterGLSLException(
                'Can\'t find template for surface shader: {}, explected {}'.format(node_string, template_file_path))
        with open(template_file_path, 'r') as template_file:
            shutil.copyfileobj(template_file, output_stream)


def _post_process_painter_glsl(input_stream,
                               output_stream,
                               shader,
                               root_node_def,
                               shader_ref,
                               surface_shader_node_def,
                               mtlx_doc,
                               painter_template_directory):
    import functools
    symbols_to_replace = {
        'vd.texcoord_0': 'var_tex_coord0',
        # transform
        'vd.positionObject': '(var_position * scene_original_radius)',
        'vd.normalObject': 'var_normal',  # transform
        'vd.tangentObject': 'var_tangent',  # transform
        'vd.bitangentObject': 'var_bitangent',  # transform
        'vd.positionWorld': '(var_position * scene_original_radius)',
        'vd.normalWorld': 'var_normal',
        'vd.tangentWorld': 'var_tangent',
        'vd.bitangentWorld': 'var_bitangent'
    }
    operations = [remove_main,
                  remove_version,
                  remove_vertex_data,
                  functools.partial(replace_symbols,
                                    symbols_to_replace=symbols_to_replace),
                  functools.partial(_rename_painter_samplers,
                                    shader_ref=shader_ref,
                                    shader=shader,
                                    mtlx_doc=mtlx_doc),
                  functools.partial(_append_painter_uniform_metadata,
                                    shader_ref=shader_ref,
                                    shader=shader,
                                    mtlx_doc=mtlx_doc),
                  functools.partial(_append_painter_entry_point,
                                    parallax_support=True,
                                    shader=shader,
                                    root_node_def=root_node_def,
                                    shader_ref=shader_ref,
                                    surface_shader_node_def=surface_shader_node_def,
                                    painter_template_directory=painter_template_directory)
                  ]
    next_input = input_stream
    for o in operations:
        new_output = io.StringIO()
        o(next_input, new_output)
        next_input = new_output
        next_input.seek(0)
    shutil.copyfileobj(next_input, output_stream)


def mtlx2PainterGLSL(doc,
                     output_glsl,
                     matx_doc_paths,
                     root_material,
                     painter_template_directory):
    '''

    :param doc:
    :type doc: mx.Document
    :param output_shader:
    :param output_glsl:
    :param matx_doc_paths: List of paths the materialx tool should look in
    for definition documents
    :param root_material:
    :return:
    '''
    logger.info('Creating Python GLSL file: %s' % output_glsl)
    glsl_gen = mxglslgen.GlslShaderGenerator()
    language = glsl_gen.getLanguage()
    color_management = mxgen.DefaultColorManagementSystem.create(language)
    glsl_gen.setColorManagementSystem(color_management)
    depend_lib = mx.createDocument()

    # Load dependedent libraries
    for p in matx_doc_paths:
        load_impl_libraries_rec(['stdlib', 'pbrlib', 'bxdf'], p, depend_lib)

    color_management.loadLibrary(depend_lib)

    context = mxgen.GenContext(glsl_gen)
    gen_options = context.getOptions()
    for p in matx_doc_paths:
        context.registerSourceCodeSearchPath(p)
    doc.importLibrary(depend_lib)
    material = doc.getMaterial(root_material)

    # Questionable to just take the first shader ref
    shader_ref = material.getShaderRefs()[0]
    surface_shader_node_def = shader_ref.getNodeDef()
    node_graph, node_def, imp_node_graph = get_bound_node_graph_and_def(
        shader_ref, doc)
    with open(output_glsl, 'w') as out_glsl_file:
        if node_graph:
            # This path is for when there is a graph connected to the
            # shader ref
            # node_def = node_graph.getNodeDef()
            if not node_def:
                raise MTLXPainterGLSLException(
                    'Failed to find node def for graph to generate')
            node_name = node_def.getNodeString()
            target_node = node_graph.getOutputs()[0]
            name_path = node_def.getNamePath()
            # skipping path replacement for now

            element_name = mx.createValidName(name_path)
            glsl_stream = io.StringIO()
            shader = generate_node(element_name,
                                   glsl_gen,
                                   node_def,
                                   context,
                                   target_node,
                                   glsl_stream)
            glsl_stream.seek(0)
            _post_process_painter_glsl(glsl_stream,
                                       out_glsl_file,
                                       shader,
                                       node_def,
                                       shader_ref,
                                       surface_shader_node_def,
                                       doc,
                                       painter_template_directory)

        else:
            # No inputs bound
            glsl_stream = io.StringIO()
            _post_process_painter_glsl(glsl_stream,
                                       out_glsl_file,
                                       None,
                                       None,
                                       shader_ref,
                                       surface_shader_node_def,
                                       doc)
