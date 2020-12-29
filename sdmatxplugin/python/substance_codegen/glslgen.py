# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os

import MaterialX as mx
import MaterialX.PyMaterialXGenShader as mxgen
import mx_utils


class MTLX2GLSLException(BaseException):
    pass


class GLSLScope:
    def __init__(self, output_stream, tab_level):
        '''
        :param output_stream:
        :type output_stream: TextIO
        :param tab_level:
        :type tab_level: [int]
        '''
        self.tab_level = tab_level
        self.output_stream = output_stream

    def __enter__(self):
        self.output_stream.write('{\n')
        self.tab_level[0] += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tab_level[0] -= 1
        self.output_stream.write('}\n')


def load_impl_libraries_rec(library_names,
                            search_path,
                            doc):
    '''

    :param library_names:
    :type library_names: [str]
    :param search_path:
    :type search_path: str
    :param doc:
    :type doc: mx.Document
    :return:
    '''
    for library in library_names:
        library_path = os.path.join(search_path, library)
        for dir, subdir_list, file_list in os.walk(library_path):
            for f in file_list:
                if os.path.splitext(f)[1] == '.mtlx':
                    if 'impl' in f:
                        new_doc = mx.createDocument()
                        full_path = os.path.join(dir, f)
                        mx.readFromXmlFile(new_doc, full_path)
                        mx_utils.importSkipConflicting(doc, new_doc)


def get_bound_node_graph_and_def(shader_ref, doc):
    '''
    :param shader_ref:
    :type shader_ref: mx.ShaderRef
    :param doc
    :type doc: mx.Document
    :return:
    '''
    bind_node_graph = ''
    bind_output_string = ''
    for i in shader_ref.getBindInputs():
        ngs = i.getNodeGraphString()
        if bind_node_graph != ngs and ngs != '':
            if bind_node_graph == '':
                bind_node_graph = ngs
            else:
                raise MTLX2GLSLException('Multiple node graphs bound')
        if bind_output_string == '':
            bind_output_string = i.getOutputString()

    if bind_node_graph != '':
        shader_ref.getDocument().getNodeGraph(bind_node_graph)
        bind_ng = shader_ref.getDocument().getNodeGraph(bind_node_graph)
        # Assuming the first node in the bind node graph is the instance
        # of the material node graph
        imp_node = bind_ng.getNodes()[0]
        assert(imp_node is not None)
        imp_graph = imp_node.getImplementation()
        bind_node_def = imp_graph.getNodeDef()
        return bind_ng, bind_node_def, imp_graph
    else:
        # TODO: When do we hit this code path?
        doc = shader_ref.getDocument()
        node_graph = doc.getNodeGraph(bind_node_graph)
        return node_graph
    return mx.NodeGraph()


def _generate_code(context,
                   shader_name,
                   element,
                   # log,
                   stages,
                   source_code_out):
    '''

    :param context:
    :type context: mxgen.GenContext
    :param shader_name:
    :type shader_name: str
    :param element:
    :type element: mx.TypedElement
    :param stages:
    :type stages: [str]
    :param source_code_out:
    :type source_code_out: [str]
    :return: mx.Shader
    '''
    shader = context.getShaderGenerator().generate(shader_name, element, context)
    if not shader:
        raise MTLX2GLSLException('Failed to generate shader for element {}'.format(
            element.getNamePath()
        ))
    for stage in stages:
        code = shader.getSourceCode(stage)
        if code == '':
            raise MTLX2GLSLException('Failed to generate source doe for element {}'.format(
                element.getNamePath()
            ))
        source_code_out.append(code)
    return shader


def generate_node(element_name,
                  generator,
                  node_def,
                  context,
                  element,
                  out_file_stream):
    '''

    :param element_name:
    :type element: str
    :param generator:
    :type generator: mxgen.ShaderGenerator
    :param node_def:
    :type node_def: mx.NodeDef
    :param context:
    :type context: mxgen.GenContext
    :param element:
    :type element: mx.TypedElement
    :param out_file_stream:
    :return: mxgen.ShaderPtr
    '''
    impl = node_def.getImplementation(
        generator.getTarget(), generator.getLanguage())
    if not impl:
        raise MTLX2GLSLException('Failed to find implementation for root node')
    source_code = []
    shader = _generate_code(context,
                            element_name,
                            element,
                            # log
                            [mxgen.PIXEL_STAGE],
                            source_code)
    out_file_stream.write(source_code[0])
    return shader


def replace_symbols(input_stream, output_stream, symbols_to_replace):
    '''
    :param input_stream:
    :type input_stream: TextIO
    :param output_stream:
    :type output_stream: TextIO
    :return:
    '''
    indata = input_stream.getvalue()
    for k, v in symbols_to_replace.items():
        indata = indata.replace(k, v)
    output_stream.write(indata)


def remove_main(input_stream, output_stream):
    '''
    :param input_stream:
    :type input_stream: TextIO
    :param output_stream:
    :type output_stream: TextIO
    :return:
    '''
    for line in input_stream.readlines():
        if line.startswith('void main()'):
            break
        output_stream.write(line)


def remove_version(input_stream, output_stream):
    '''
    :param input_stream:
    :type input_stream: TextIO
    :param output_stream:
    :type output_stream: TextIO
    :return:
    '''
    for line in input_stream.readlines():
        if line.startswith('#version'):
            continue
        output_stream.write(line)


def remove_vertex_data(input_stream, output_stream):
    '''
    :param input_stream:
    :type input_stream: TextIO
    :param output_stream:
    :type output_stream: TextIO
    :return:
    '''
    scope_started = False
    for line in input_stream.readlines():
        if line.startswith('in VertexData'):
            scope_started = True
        if scope_started:
            if line.startswith('}'):
                scope_started = False
            continue
        output_stream.write(line)


_tab_str = '    '


def _mk_tabstr(n):
    return _tab_str * n


def _has_default(i):
    '''
    :param i:
    :type i: mx.ValueElement
    :return:
    '''
    return i.getValue() != None


def _add_tabs(n, output_stream):
    output_stream.write(_mk_tabstr(n))


def write_line_tabbed(message, output_stream, tab_level):
    '''
    :param message:
    :type message: str
    :param output_stream:
    :type output_stream: TextIO
    :param tab_level:
    :type tab_level: [int]
    :return:
    '''
    _add_tabs(tab_level[0], output_stream)
    output_stream.write(message)
    output_stream.write('\n')


def _get_glsl_type(input):
    type_mappings = {"color3": "vec3",
                     "float": "float",
                     "vector3": "vec3",
                     "boolean": "bool"}
    t = input.getType()
    if t in type_mappings:
        return type_mappings[t]
    else:
        raise MTLX2GLSLException(
            'Failed to find type mapping for type {}'.format(t))


def _get_glsl_value(i, value_string=None):
    '''
    :param i:
    :type i: mx.ValueElement
    :return:
    '''
    return '{type_name}({value_string})'.format(
        type_name=_get_glsl_type(i),
        value_string=value_string if value_string else i.getValueString().strip()
    )


def _format_variable(i, declare_result_parameter):
    '''
    :param i:
    :type i: mx.ValueElement
    :param declare_result_parameter:
    :type declare_result_parameter: bool
    :return: str
    '''
    return '{type}{name}{default};'.format(
        type=_get_glsl_type(i) + ' ' if declare_result_parameter else '',
        name=i.getName(),
        default='' if not _has_default(
            i) else ' = {}'.format(_get_glsl_value(i))
    )


def _clamp_variable(i):
    '''
    :param i:
    :type i: mx.ValueElement
    :param declare_result_parameter:
    :type declare_result_parameter: bool
    :return: str
    '''
    # return '{type}{name}{default};'.format(
    #     type= _get_glsl_type(i) + ' ' if declare_result_parameter else '',
    #     name=i.getName(),
    #     default='' if not _has_default(i) else ' = {}'.format(_get_glsl_default(i))
    # )
    ui_min = i.getAttribute('uimin')
    ui_max = i.getAttribute('uimax')
    if ui_min and ui_max:
        return '{name} = clamp({name}, {min_val}, {max_val});'.format(name=i.getName(),
                                                                      min_val=_get_glsl_value(
                                                                          i, ui_min),
                                                                      max_val=_get_glsl_value(i, ui_max))
    else:
        return '// Skipping clamping for {}, missing uimin/uimax'.format(i.getName())


def _get_input_name_from_bound_output(shader_ref, output_name):
    '''
    :param shader_ref:
    :type shader_ref: mx.ShaderRef
    :param output_name:
    :type output_name: str
    :return: str
    '''
    # TODO: This function should use a cache to avoid n^2 performance
    for b in shader_ref.getBindInputs():
        output_string = b.getOutputString()
        if output_string == output_name:
            return b.getName()
        # if output_string != '':
        #     doc = shader_ref.getDocument()
        #     output_node = doc.getOutput(output_string)
        #     assert (output_node is not None)
        #     # Interface::getOutputString is missing from python bindings
        #     if output_node.getAttribute('output') == output_name:
        #         return b.getName()
    raise MTLX2GLSLException(
        'Unbound output {} when generating call'.format(output_name))


def _get_input_name_from_single_bound_output(shader_ref):
    '''
    :param shader_ref:
    :type shader_ref: mx.ShaderRef
    :return: str
    '''
    for b in shader_ref.getBindInputs():
        output_string = b.getOutputString()
        if output_string != '':
            return b.getName()
    raise MTLX2GLSLException('No bound output found when generating wrapper')


def call_node_graph(output_stream,
                    declare_result_params,
                    parallax_support,
                    shader,
                    root_node_def,
                    shader_ref,
                    surface_shader_node_def,
                    tabs,
                    clamp_to_min_max):
    '''
    :param output_stream:
    :type output_stream: TextIO
    :param declare_result_params:
    :type declare_result_params: bool
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
    :param tabs:
    :type tabs: [int]
    :param clamp_to_min_max:
    :type clamp_to_min_max: bool
    :return:
    '''
    for p in surface_shader_node_def.getActiveValueElements():
        pp = shader_ref.getBindInput(p.getName())
        if not isinstance(p, mx.Output):
            write_line_tabbed(_format_variable(pp if pp else p, declare_result_params),
                              output_stream,
                              tabs)

    # Call main shader if we have one
    if shader:
        node_graph, node_def, imp_node_graph = get_bound_node_graph_and_def(
            shader_ref, shader_ref.getDocument())
        _add_tabs(tabs[0], output_stream)
        imp_node_graph_name = imp_node_graph.getName()
        output_stream.write(imp_node_graph_name)
        output_stream.write('(')
        UNIFORM_PREFIX = node_graph.getNodes()[0].getName() + '_'
        inputs = [UNIFORM_PREFIX + i.getName()
                  for i in root_node_def.getActiveValueElements()
                  if isinstance(i, mx.Input) or isinstance(i, mx.Parameter)]
        outputs = None
        if root_node_def.getType() == 'multioutput':
            outputs = [_get_input_name_from_bound_output(shader_ref, o.getName())
                       for o in root_node_def.getOutputs()]
        else:
            outputs = [_get_input_name_from_single_bound_output(shader_ref)]
        output_stream.write(
            (',\n' + _mk_tabstr(tabs[0] + 2)).join(inputs + outputs))
        output_stream.write(');\n')
    if clamp_to_min_max:
        for p in surface_shader_node_def.getActiveValueElements():
            if not isinstance(p, mx.Output):
                write_line_tabbed(_clamp_variable(p),
                                  output_stream,
                                  tabs)


def generate_signature(output_stream, surface_shader_node_def):
    output_stream.write('void matx_compute(\n')
    for i in surface_shader_node_def.getActiveValueElements():
        if isinstance(i, mx.Input):
            _add_tabs(1, output_stream)
            output_stream.write('out {type} {name},\n'.format(type=_get_glsl_type(i),
                                                              name=i.getName()))
    default_params = [
        ('vec2', 'uv'),
        ("bool", "disableFragment")
    ]
    # TODO: This should probably be disabled for now since we don't support
    #  parallax mapping
    for idx, (k, v) in enumerate(default_params):
        _add_tabs(1, output_stream)
        output_stream.write('out {type} {name}'.format(type=k,
                                                       name=v))
        if idx != len(default_params) - 1:
            output_stream.write(',\n')
    output_stream.write(')\n')


def get_graph_prefix(node_graph):
    return node_graph.getNodes()[0].getName() + '_'


def subtract_prefix(source, prefix):
    if source[:len(prefix)] != prefix:
        raise MTLX2GLSLException(
            '{} is not a prefix of {}'.format(source, prefix))
    return source[len(prefix):]
