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
import xml.etree.ElementTree as ET
from typing import TextIO
import shutil
from substance_codegen.glslgen import load_impl_libraries_rec, get_bound_node_graph_and_def, MTLX2GLSLException, generate_node, \
    remove_main, remove_version, remove_vertex_data, replace_symbols, call_node_graph, generate_signature, GLSLScope, subtract_prefix, \
    get_graph_prefix
import logging

logger = logging.getLogger("SDMaterialX")

GLSLFX_USAGE_TAG = 'GLSLFX_usage'


class MTLX2GLSLFXException(MTLX2GLSLException):
    pass


def _append_designer_entry_point(input_stream,
                                 output_stream,
                                 parallax_support,
                                 shader,
                                 root_node_def,
                                 shader_ref,
                                 surface_shader_node_def):
    '''
    :param input_stream:
    :type input_stream: TextIO
    :param output_stream:
    :type output_stream: TextIO
    :param parallax_support:
    :type parallax_support: bool
    :param shader:
    :type shader: mx.Shader
    :param root_node_def:
    :type root_node_def: mx.NodeDef
    :param shader_ref:
    :type shader_ref: mx.ShaderRef
    :param surface_shader_node_def:
    :type surface_shader_node_def: mx.NodeDef
    :return:
    '''
    # First copy the original data to the output so we can append to the end
    shutil.copyfileobj(input_stream, output_stream)
    generate_signature(output_stream, surface_shader_node_def)
    tab_level = [0]
    with GLSLScope(output_stream, tab_level):
        call_node_graph(output_stream,
                        False,
                        parallax_support,
                        shader,
                        root_node_def,
                        shader_ref,
                        surface_shader_node_def,
                        tab_level,
                        True)


def _post_process_designer_glsl(input_stream,
                                output_stream,
                                shader,
                                root_node_def,
                                shader_ref,
                                surface_shader_node_def):
    import functools
    symbols_to_replace = {
        'vd.texcoord_0': 'iFS_UV',
        'vd.positionObject': 'vec3(inverse(worldMatrix) * vec4(iFS_PointWS, 1.0))',
        'vd.normalObject': 'normalize(vec3(inverse(worldInverseTransposeMatrix) * vec4(iFS_Normal, 0.0)))',
        'vd.tangentObject': 'normalize(vec3(inverse(worldMatrix) * vec4(iFS_Tangent, 0.0)))',
        'vd.bitangentObject': 'normalize(vec3(inverse(worldMatrix) * vec4(iFS_Binormal, 0.0)))',
        'vd.positionWorld': 'iFS_PointWS',
        'vd.normalWorld': 'iFS_Normal',
        'vd.tangentWorld': 'iFS_Tangent',
        'vd.bitangentWorld': 'iFS_Binormal'
    }
    operations = [remove_main,
                  remove_version,
                  remove_vertex_data,
                  functools.partial(replace_symbols,
                                    symbols_to_replace=symbols_to_replace),
                  functools.partial(_append_designer_entry_point,
                                    parallax_support=True,
                                    shader=shader,
                                    root_node_def=root_node_def,
                                    shader_ref=shader_ref,
                                    surface_shader_node_def=surface_shader_node_def)
                  ]
    next_input = input_stream
    for o in operations:
        new_output = io.StringIO()
        o(next_input, new_output)
        next_input = new_output
        next_input.seek(0)
    shutil.copyfileobj(next_input, output_stream)


def _append_sampler(sampler_port, node, tree):
    '''
    :param sampler_port:
    :type sampler_port: mxgen.ShaderPort
    :param node:
    :type node: mx.Element
    :param tree:
    :type tree: xml.etree.ElementTree.ElementTree
    :return:
    '''
    usage = ''
    if node.hasAttribute(GLSLFX_USAGE_TAG):
        usage = node.getAttribute(GLSLFX_USAGE_TAG)
    root = tree.getroot()
    if not root.tag == 'glslfx':
        raise MTLX2GLSLFXException('No glslfx tag found in glslfx document')
    sampler = ET.Element('sampler')
    sampler.set('name', sampler_port.getName())
    sampler.set('usage', usage)
    root.append(sampler)


def _remove_whitespace_XML(tree):
    for elem in tree.getroot().iter('*'):
        if elem.text is not None:
            elem.text = elem.text.strip()
        if elem.tail is not None:
            elem.tail = elem.tail.strip()


def _pretty_write_XML(output_stream, tree):
    import xml.dom.minidom as minidom
    _remove_whitespace_XML(tree)
    unformatted_xml = io.StringIO()
    tree.write(unformatted_xml, encoding='unicode')
    unformatted_xml.seek(0)
    formatted_tree = minidom.parse(unformatted_xml)
    output_stream.write(formatted_tree.toprettyxml())


def _convert_matx_constant_to_glslfx(parameter_string):
    return ';'.join(parameter_string.split(','))


def _append_uniform(uniform_port, node, tree, force_constant):
    '''
    :param uniform_port:
    :type uniform_port: mxgen.ShaderPort
    :param node:
    :type node: mx.TypedElement
    :param tree:
    :type tree: xml.etree.ElementTree.ElementTree
    :param force_constants: Force constants to have min and max values set to default to trigger a change in designer
    :type force_constants: bool
    :return:
    '''
    root = tree.getroot()
    if not root.tag == 'glslfx':
        raise MTLX2GLSLFXException('No glslfx tag found in glslfx document')
    uniform = ET.Element('uniform')
    uniform.set('name', uniform_port.getName())
    if node.hasAttribute('uiname'):
        uniform.set('guiName', node.getAttribute('uiname'))
    else:
        uniform.set('guiName', node.getName())
    node_type = node.getType()
    if node_type in {'color3', 'color4', 'color2'}:
        uniform.set('guiWidget', 'color')
    elif node_type == 'boolean':
        uniform.set('guiWidget', 'checkbox')
    else:
        uniform.set('guiWidget', 'slider')

    default_constant_value = _convert_matx_constant_to_glslfx(
        uniform_port.getValue().getValueString())
    uniform.set('default', default_constant_value)

    if force_constant:
        uniform.set('min', default_constant_value)
        uniform.set('max', default_constant_value)
    vector_size = len(default_constant_value.split(';'))

    def _expand_vector(val, size):
        return '; '.join([val] * size)
    if node.hasAttribute('uimin') and not force_constant:
        uniform.set('guiMin', _expand_vector(
            node.getAttribute('uisoftmin'), vector_size))
        uniform.set('min', _expand_vector(
            node.getAttribute('uimin'), vector_size))
    if node.hasAttribute('uimax') and not force_constant:
        uniform.set('guiMax', _expand_vector(
            node.getAttribute('uisoftmax'), vector_size))
        uniform.set('max', _expand_vector(
            node.getAttribute('uimax'), vector_size))

    if node.hasAttribute('uifolder'):
        uniform.set('guiGroup', node.getAttribute('uiFolder'))
    else:
        uniform.set('guiGroup', 'MaterialX')

    uniform.set('guiStep', '.0001')

    root.append(uniform)


def _generate_designer_glslfx(output_glslfx_stream,
                              glslfx_template,
                              shader_ref,
                              shader,
                              doc,
                              force_constants):
    '''
    :param output_glslfx_stream:
    :type output_glslfx_stream: TextIO
    :param glslfx_template:
    :type glslfx_template: str
    :param shader_ref:
    :type shader_ref: mx.ShaderRef
    :param shader:
    :type shader: mxgen.Shader
    :param doc:
    :type shader: mx.Document
    :param force_constants: Force constants to have min and max values set to default to trigger a change in designer
    :type force_constants: bool
    :return:
    '''
    tree = ET.parse(glslfx_template)
    node_graph, node_def, imp_node_graph = get_bound_node_graph_and_def(
        shader_ref, doc)
    if not shader:
        raise MTLX2GLSLFXException('No shader found when generating GLSLFX')
    if node_graph:
        # Generate index of nodes
        graph_prefix = get_graph_prefix(node_graph)
        exposed_nodes = {
            i.getName(): i for i in node_def.getActiveValueElements()
        }
        pixel_stage = shader.getStage(mxgen.PIXEL_STAGE)
        public_uniforms = pixel_stage.getUniformBlock('PublicUniforms')
        for i in public_uniforms:
            name = i.getName()
            type = i.getType()
            type_name = type.getName()
            if type_name == 'filename':
                cropped_name = name[:name.rindex('_')]
                node = imp_node_graph.getNode(cropped_name)
                if not node:
                    raise MTLX2GLSLFXException(
                        'Texture sampler not associated with any node: {}'.format(cropped_name))
                _append_sampler(i, node, tree)
            else:
                separated_name = subtract_prefix(
                    name, graph_prefix)
                if separated_name not in exposed_nodes:
                    raise MTLX2GLSLFXException(
                        'Exposed parameter not associated with any node: {}'.format(separated_name))
                _append_uniform(
                    i, exposed_nodes[separated_name], tree, force_constants)
    _pretty_write_XML(output_glslfx_stream, tree)


def mtlx2GLSLFX(doc,
                output_shader,
                output_glslfx,
                glslfx_template,
                matx_doc_paths,
                root_material,
                force_constants=False):
    '''

    :param doc:
    :type doc: mx.Document
    :param output_shader:
    :param output_glslfx:
    :param glslfx_template:
    :param matx_doc_paths: List of paths the materialx tool should look in
    for definition documents
    :param root_material:
    :param force_constants: Force constants to have min and max values set to default to trigger a change in designer
    :type force_constants: bool
    :return:
    '''
    logger.info('Creating GLSLFX file: %s' % output_glslfx)
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

    with open(output_shader, 'w') as out_glsl_file:
        if node_graph:
            # This path is for when there is a graph connected to the
            # shader ref
            if not node_def:
                raise MTLX2GLSLFXException(
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
            _post_process_designer_glsl(glsl_stream,
                                        out_glsl_file,
                                        shader,
                                        node_def,
                                        shader_ref,
                                        surface_shader_node_def)

            with open(output_glslfx, 'w') as glslfx_stream:
                _generate_designer_glslfx(glslfx_stream,
                                          glslfx_template,
                                          shader_ref,
                                          shader,
                                          doc,
                                          force_constants)
        else:
            # No inputs bound
            glsl_stream = io.StringIO()
            _post_process_designer_glsl(glsl_stream,
                                        out_glsl_file,
                                        None,
                                        None,
                                        shader_ref,
                                        surface_shader_node_def)
            with open(output_glslfx, 'w') as glslfx_stream:
                _generate_designer_glslfx(glslfx_stream,
                                          glslfx_template,
                                          shader_ref,
                                          None,
                                          doc,
                                          force_constants)
