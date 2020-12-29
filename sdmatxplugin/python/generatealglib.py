#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import argparse
import os
import sys

import MaterialX as mx

import automatx as ax

import mx_utils

class AlgLibException(BaseException):
    pass


class Type:
    def __init__(self, name, vector_size, base_type):
        self.name = name
        self.vector_size = vector_size
        self.base_type = base_type

    def __str__(self):
        return self.name

    def is_scalar(self):
        return self.vector_size == 1

    def is_vector(self):
        return not self.is_scalar()

    def make_default(self, hint=0.0):
        if self.is_scalar():
            return hint
        else:
            return ','.join([str(hint)] * self.vector_size)


def write_mx_doc_to_stream(doc, stream):
    s = mx.writeToXmlString(doc)
    stream.write(s)


all_types = [float,
             mx.Vector2,
             mx.Vector3,
             mx.Vector4,
             # mx.Color2,
             mx.Color3,
             # mx.Color4
             ]

all_color_types = [
    # mx.Color2,
    mx.Color3,
    # mx.Color4
]

type_to_name = {float: 'float',
                mx.Vector2: 'vector2',
                mx.Vector3: 'vector3',
                mx.Vector4: 'vector4',
                # mx.Color2: 'color2',
                mx.Color3: 'color3',
                # mx.Color4: 'color4'
                }


def _generate_clamp(type,
                    node_name,
                    declaration_doc,
                    definition_doc,
                    lib):
    node_def_name = 'ND_' + node_name + '_' + type_to_name[type]
    node_graph_name = 'NG_' + node_name + '_' + type_to_name[type]
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    i_val = ax.createInput('val',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(0.0),
                           uiName='Value')
    i_min = ax.createInput('i_min',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(0.0),
                           uiName='Min')
    i_max = ax.createInput('i_max',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(1.0),
                           uiName='Max')

    ax.createOutput(name='out',
                    op=ax.min_(ax.max_(i_val, i_min), i_max),
                    node_graph=node_graph,
                    node_def=node_def)


def _generate_levels(type,
                     node_name,
                     declaration_doc,
                     definition_doc,
                     lib):
    node_def_name = 'ND_' + node_name + '_' + type_to_name[type]
    node_graph_name = 'NG_' + node_name + '_' + type_to_name[type]
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    i_val = ax.createInput('pixel',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(0.0),
                           uiName='Value')
    i_min = ax.createInput('i_min',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(0.0),
                           uiName='Min')
    i_max = ax.createInput('i_max',
                           type_to_name[type],
                           node_graph,
                           node_def,
                           lib,
                           default=type(1.0),
                           uiName='Max')
    i_gamma = ax.createInput('i_gamma',
                             'float',
                             node_graph,
                             node_def,
                             lib,
                             default=1.0,
                             uiName='Gamma')
    f = (i_val - i_min) / (i_max - i_min)
    f = ax.pow_(ax.clamp(f, type(0.0), type(1.0)),
                lib.constant(node_graph, value=1.0) / i_gamma)
    ax.createOutput(name='out',
                    op=f,
                    node_graph=node_graph,
                    node_def=node_def)


def _generate_dot_products(type,
                           node_name,
                           declaration_doc,
                           definition_doc,
                           lib):
    node_def_name = 'ND_' + node_name + '_' + type_to_name[type]
    node_graph_name = 'NG_' + node_name + '_' + type_to_name[type]
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    in1 = ax.createInput('in1',
                         type_to_name[type],
                         node_graph,
                         node_def,
                         lib,
                         default=type(0.0),
                         uiName='Value')
    in2 = ax.createInput('in2',
                         type_to_name[type],
                         node_graph,
                         node_def,
                         lib,
                         default=type(0.0),
                         uiName='Min')
    elem_count = len(type(0))
    channels = ['r', 'g', 'b', 'a']

    res = None
    for i in range(elem_count):
        c = channels[i]
        f = ax.swizzle(in1, channels=c, target_type='float') * \
            ax.swizzle(in2,
                       channels=c,
                       target_type='float')
        res = res + f if res else f

    ax.createOutput(name='out',
                    op=res,
                    node_graph=node_graph,
                    node_def=node_def)


def _generate_ts_normal_to_ws(node_name,
                              declaration_doc,
                              definition_doc,
                              lib):
    node_def_name = 'ND_' + node_name + '_vector3'
    node_graph_name = 'NG_' + node_name + '_vector3'
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    normalTS = ax.createInput('normalTS',
                              type_to_name[mx.Vector3],
                              node_graph,
                              node_def,
                              lib,
                              default=mx.Vector3(.5, .5, 1.0),
                              uiName='Normal Tangent Space')
    openGLTS = ax.createParameter('openGL',
                                  'boolean',
                                  node_graph,
                                  node_def,
                                  lib,
                                  default=True,
                                  uiName='OpenGL Tangent Space')
    index = ax.createParameter('index',
                               'int',
                               node_graph,
                               node_def,
                               lib,
                               default=0,
                               uiName='UV Index')

    decoded_normal = (normalTS - .5) * 2.0
    normal_components = [ax.swizzle(decoded_normal,
                                    channels=c,
                                    target_type='float') for c in
                         ['x', 'y', 'z']]
    base = [lib.tangent(node_graph, space='world', index=index.node),
            lib.bitangent(node_graph, space='world', index=index.node),
            lib.normal(node_graph, space='world')]
    base[1] = lib.ifequal(node_graph,
                          value1=openGLTS.node,
                          value2=False,
                          in1=base[1],
                          in2=base[1] * -1.0)
    proj = [base[i] * normal_components[i] for i in range(3)]
    result = lib.normalize(node_graph, in_=proj[0] + proj[1] + proj[2])
    ax.createOutput(name='out',
                    op=result,
                    node_graph=node_graph,
                    node_def=node_def)


def _generate_height_to_normal(node_name,
                               declaration_doc,
                               definition_doc,
                               lib):
    node_def_name = 'ND_' + node_name
    node_graph_name = 'NG_' + node_name
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    h = ax.createInput('h',
                       type_to_name[float],
                       node_graph,
                       node_def,
                       lib,
                       default=0.0,
                       uiName='Height')

    dU = ax.createInput('dU',
                        type_to_name[float],
                        node_graph,
                        node_def,
                        lib,
                        default=0.0,
                        uiName='HeightU')

    dV = ax.createInput('dV',
                        type_to_name[float],
                        node_graph,
                        node_def,
                        lib,
                        default=0.0,
                        uiName='HeightV')
    delta = ax.createInput('delta',
                           type_to_name[float],
                           node_graph,
                           node_def,
                           lib,
                           default=.0001,
                           uiName='Delta')
    intensity = ax.createInput(name='intensity',
                               type=type_to_name[float],
                               node_graph=node_graph,
                               node_def=node_def,
                               lib=lib,
                               uiName='Normal Intensity',
                               default=1.0,
                               min=.001,
                               max=10.0)
    du = (dU - h) / delta
    dv = (dV - h) / delta
    one = lib.constant(node_graph, value=1.0)
    normal = lib.combine3(node_graph, in1=du, in2=dv, in3=one / intensity,
                          _outputType='vector3')
    normal2 = lib.normalize(node_graph, in_=normal, _outputType='vector3')
    ts_normal = (normal2 + mx.Vector3(1.0, 1.0, 1.0)) / 2.0
    ax.createOutput(name='out',
                    op=ts_normal,
                    node_graph=node_graph,
                    node_def=node_def)


def _generate_srgb_to_linear(node_name,
                             declaration_doc,
                             definition_doc,
                             lib):
    node_def_name = 'ND_' + node_name
    node_graph_name = 'NG_' + node_name
    node_def = declaration_doc.addNodeDef(name=node_def_name)
    node_def.setNodeString(node_name)
    node_graph = definition_doc.addNodeGraph(name=node_graph_name)
    node_graph.setNodeDef(node_def)
    input = ax.createInput('in',
                           type_to_name[mx.Color3],
                           node_graph,
                           node_def,
                           lib,
                           default=mx.Color3(0.0, 0.0, 0.0),
                           uiName='In')
    linear_part = input / 12.92
    exp_part = lib.power(node_graph, in1=(input + .055) / 1.055, in2=2.4)
    # TODO: Reintroduce linear part
    components = [ax.swizzle(input, channels=c , target_type='float') for c in 'rgb']
    components_l = [ax.swizzle(linear_part, channels=c , target_type='float') for c in 'rgb']
    components_e = [ax.swizzle(exp_part, channels=c , target_type='float') for c in 'rgb']
    selected = [lib.ifgreater(node_graph,
                              value1=components[i],
                              value2=.045045,
                              in1=components_e[i],
                              in2=components_l[i]) for i in range(3)]
    result = lib.combine3(node_graph, in1=selected[0], in2=selected[1], in3=selected[2], _outputType='color3')
    ax.createOutput(name='out',
                    op=result,
                    node_graph=node_graph,
                    node_def=node_def)


_method_prefix = 'alg'
_all_polymorphic_functions = {_method_prefix + 'clamp': _generate_clamp,
                              _method_prefix + 'levels': _generate_levels}
_all_color_functions = {_method_prefix + 'dot': _generate_dot_products}


def generate_library(declaration_file,
                     definition_file,
                     materialx_search_path):
    import sdmatx
    definition_doc = mx.createDocument()
    declaration_doc = mx.createDocument()

    stdlib = mx.createDocument()
    stdlib_defs = mx.createDocument()
    mx.readFromXmlFile(stdlib,
                       filename=sdmatx.makeConsistentPath(
                           os.path.join('stdlib', 'stdlib_defs.mtlx')),
                       searchPath=materialx_search_path)
    mx.readFromXmlFile(stdlib_defs,
                       filename=sdmatx.makeConsistentPath(
                           os.path.join('stdlib', 'stdlib_ng.mtlx')),
                       searchPath=materialx_search_path)
    stdlib.importLibrary(stdlib_defs)

    # Import stdlib into alglib
    mx_utils.importSkipConflicting(declaration_doc, stdlib)
    mx_utils.importSkipConflicting(declaration_doc, stdlib_defs)
    mx_utils.importSkipConflicting(definition_doc, stdlib)
    mx_utils.importSkipConflicting(definition_doc, stdlib_defs)

    lib = ax.Library(stdlib)

    for f_name, f in _all_polymorphic_functions.items():
        for t in all_types:
            f(node_name=f_name,
              declaration_doc=declaration_doc,
              definition_doc=definition_doc,
              lib=lib,
              type=t)

    for f_name, f in _all_color_functions.items():
        for t in all_color_types:
            f(node_name=f_name,
              declaration_doc=declaration_doc,
              definition_doc=definition_doc,
              lib=lib,
              type=t)
    _generate_height_to_normal(node_name=_method_prefix + 'heighttonormal',
                               declaration_doc=declaration_doc,
                               definition_doc=definition_doc,
                               lib=lib)
    _generate_ts_normal_to_ws(node_name=_method_prefix + 'normalTStoWS',
                              declaration_doc=declaration_doc,
                              definition_doc=definition_doc,
                              lib=lib)
    _generate_srgb_to_linear(node_name=_method_prefix + 'srgb_to_linear',
                             declaration_doc=declaration_doc,
                             definition_doc=definition_doc,
                             lib=lib)
    if not declaration_doc.validate():
        raise AlgLibException('Declaration doc failed validation')
    write_mx_doc_to_stream(declaration_doc, declaration_file)

    if not definition_doc.validate():
        raise AlgLibException('Definition doc failed validation')
    write_mx_doc_to_stream(definition_doc, definition_file)


def main():
    parser = argparse.ArgumentParser(
        description='Generate a standard library for materialX.')
    parser.add_argument('--declaration-file',
                        type=argparse.FileType('w'),
                        default=sys.stdout,
                        help='The file to write declarations (nodedefs) to, '
                             'defaults to stdout')
    parser.add_argument('--definition-file',
                        type=argparse.FileType('w'),
                        default=sys.stdout,
                        help='The file to write definitions (nodegraphs) to, '
                             'defaults to stdout')
    parser.add_argument('--materialx-search-path',
                        required=True,
                        type=str,
                        help='Materialx search path for libraries')
    args = parser.parse_args()
    generate_library(args.declaration_file, args.definition_file,
                     args.materialx_search_path)


if __name__ == '__main__':
    main()
