#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import math
import automatx as ax
import MaterialX as mx

def makeDesaturatedNetwork(node_graph, node_def, shader_ref, lib):
    scale = ax.createInput('noiseScale', 'float', node_graph, node_def, lib, default=1.0, min=0.001, max=10.0)
    texCoord = lib.texcoord(node_graph, _outputType='vector2')
    tcScaled = ax.swizzle(scale, channels='xx', target_type='vector2')
    texCoordScaled = lib.multiply(node_graph, in1=texCoord, in2=tcScaled)
    base_color_tex = lib.image(node_graph, texcoord=texCoordScaled, _outputType='color3', _nodeName='baseColorMapBanan',
                               _attrs={'expose': 'true', 'GLSLFX_usage': 'basecolor,diffuse,specular'})
    roughness = lib.image(node_graph, texcoord=texCoordScaled, _outputType='float', _nodeName='roughnessMap',
                          _attrs={'expose': 'true', 'GLSLFX_usage': 'roughness'})
    metalness = lib.image(node_graph, texcoord=texCoordScaled, _outputType='float', _nodeName='metalnessMap',
                          _attrs={'expose': 'true', 'GLSLFX_usage': 'metallic'})
    normal = lib.image(node_graph, texcoord=texCoordScaled, _outputType='color3', _nodeName='normalMap',
                       _attrs={'expose': 'true', 'GLSLFX_usage': 'normal'})
    mask = lib.image(node_graph, texcoord=texCoordScaled, _outputType='vector3', _nodeName='maskMap',
                     _attrs={'expose': 'true', 'GLSLFX_usage': 'user1'})

    leather_col = ax.createInput('leatherColor', 'color3', node_graph, node_def, lib,
                                 default=mx.Color3(.3, .3, .3),
                                 min=mx.Color3(0.0, 0.0, 0.0),
                                 max=mx.Color3(1.0, 1.0, 1.0),
                                 uiName='Leather Color',
                                 uiFolder='Colors')
    metal_col = ax.createInput('metalColor', 'color3', node_graph, node_def, lib,
                               default=mx.Color3(.1, .1, .1),
                               min=mx.Color3(0.0, 0.0, 0.0),
                               max=mx.Color3(1.0, 1.0, 1.0),
                               uiName='Metal Color',
                               uiFolder='Colors')
    lamp_col = ax.createInput('lampColor', 'color3', node_graph, node_def, lib,
                              default=mx.Color3(.2, .2, .2),
                              min=mx.Color3(0.0, 0.0, 0.0),
                              max=mx.Color3(1.0, 1.0, 1.0),
                              uiName='Lamp Color',
                              uiFolder='Colors')
    plastic_col = ax.createInput('plasticColor', 'color3', node_graph, node_def, lib,
                                 default=mx.Color3(.5, .5, .5),
                                 min=mx.Color3(0.0, 0.0, 0.0),
                                 max=mx.Color3(1.0, 1.0, 1.0),
                                 uiName='Plastic Color',
                                 uiFolder='Colors')

    blend = [(leather_col, mx.Vector3(1.0, 0.0, 0.0)),
             (lamp_col, mx.Vector3(0.0, 0.0, 1.0)),
             (metal_col, mx.Vector3(0.0, 1.0, 0.0))]
    a = None
    weight = None
    one = lib.constant(node_graph, value=1.0)
    emission = lamp_col * ax.dot(mx.Vector3(0.0, 0.0, 1.0), mask)
    for layer, factor in blend:
        dp = ax.dot(mask, factor)
        s = ax.swizzle(dp, target_type='color3', channels='xxx')
        aa = s * layer
        if a is None:
            a = aa
            weight = dp
        else:
            a = a + aa
            weight = weight + dp
    # The odd node is black which is whatever is left
    # in weight when done with the other colors
    plastic_weight = one - ax.min_(1.0, weight)
    ws = ax.swizzle(plastic_weight, target_type='color3', channels='xxx')
    a = a + ws * plastic_col
    bc2 = base_color_tex * a

    ax.bind_output('base_color', bc2, node_graph, shader_ref)
    ax.bind_output('roughness', roughness, node_graph, shader_ref)
    ax.bind_output('metalness', metalness, node_graph, shader_ref)
    ax.bind_output('normal', normal, node_graph, shader_ref)
    ax.bind_output('emissionColor', emission, node_graph, shader_ref)


@ax.param_promoter
def rustLevelBlend(rustMask, rustLevel):
    return ax.levels(rustMask, rustLevel, 1.0, 1.0 / 4.0)


def ifelse(pred, onif, onelse):
    pass


def makeRustNetwork(node_graph, node_def, shader_ref, lib):
    rustLevel = ax.createInput('rustLevel', 'float', node_graph, node_def, lib,
                               default=.5,
                               min=0.0,
                               max=1.0,
                               uiFolder='Material Parameters',
                               uiName='Rust Level')

    patternTiling = ax.createInput('patternTiling', 'float', node_graph, node_def, lib,
                                   default=10.0,
                                   min=1.0,
                                   max=20.0,
                                   uiFolder='Material Parameters',
                                   uiName='Pattern Tiling')
    rustTiling = ax.createInput('rustTiling', 'float', node_graph, node_def, lib,
                                default=1.0,
                                min=.1,
                                max=5.0,
                                uiFolder='Material Parameters')


    texCoord = lib.texcoord(node_graph, _outputType='vector2')
    tiledTexCoord = texCoord * patternTiling
    rustTexCoord = texCoord * rustTiling
    base_color_tex = lib.image(node_graph, texcoord=texCoord, _outputType='color3', _nodeName='baseColorMap',
                               _attrs={'expose': 'true', 'GLSLFX_usage': 'basecolor,diffuse,specular'})
    roughness_tex = lib.image(node_graph, texcoord=texCoord, _outputType='float', _nodeName='roughnessMap',
                              _attrs={'expose': 'true', 'GLSLFX_usage': 'roughness'})
    metalness_tex = lib.image(node_graph, texcoord=texCoord, _outputType='float', _nodeName='metalnessMap',
                              _attrs={'expose': 'true', 'GLSLFX_usage': 'metallic'})
    normal_tex = lib.image(node_graph, texcoord=tiledTexCoord, _outputType='color3', _nodeName='normalMap',
                           _attrs={'expose': 'true', 'GLSLFX_usage': 'normal'})

    rust_base_color_tex = lib.image(node_graph, texcoord=rustTexCoord, _outputType='color3',
                                    _nodeName='rustBaseColorMap', _attrs={'expose': 'true', 'GLSLFX_usage': 'user0'})
    rust_roughness_tex = lib.image(node_graph, texcoord=rustTexCoord, _outputType='float', _nodeName='rustRoughnessMap',
                                   _attrs={'expose': 'true', 'GLSLFX_usage': 'user1'})
    rust_metalness_tex = lib.image(node_graph, texcoord=rustTexCoord, _outputType='float', _nodeName='rustMetalnessMap',
                                   _attrs={'expose': 'true', 'GLSLFX_usage': 'user2'})
    rust_normal_tex = lib.image(node_graph, texcoord=rustTexCoord, _outputType='color3', _nodeName='rustNormalMap',
                                _attrs={'expose': 'true', 'GLSLFX_usage': 'user3'})

    rust_mask = lib.image(node_graph, texcoord=texCoord, _outputType='float', _nodeName='rust_mask',
                          _attrs={'expose': 'true', 'GLSLFX_usage': 'user4'})
    tileAO = lib.image(node_graph, texcoord=tiledTexCoord, _outputType='float', _nodeName='tileAO',
                       _attrs={'expose': 'true', 'GLSLFX_usage': 'user5'})

    rustBlended = ax.clamp(
        rustLevelBlend(rust_mask * tileAO, lib.constant(node_graph, value=1.0) - rustLevel) + rust_mask * rustLevel,
        0.0, 1.0)
    # rustBlended = tileAO * rust_mask

    final_base_color = ax.blend(base_color_tex, rust_base_color_tex, rustBlended)
    final_roughness = ax.blend(roughness_tex, rust_roughness_tex, rustBlended)
    final_metalness = ax.blend(metalness_tex, rust_metalness_tex, rustBlended)
    final_normal = ax.blend(normal_tex, rust_normal_tex, rustBlended)

    ax.bind_output('base_color', final_base_color, node_graph, shader_ref)
    ax.bind_output('roughness', final_roughness, node_graph, shader_ref)
    ax.bind_output('metalness', final_metalness, node_graph, shader_ref)
    ax.bind_output('normal', final_normal, node_graph, shader_ref)


def simplest(node_graph, node_def, shader_ref, lib):
    texCoord = lib.texcoord(node_graph, _outputType='vector2')
    base_color_tex = lib.image(node_graph, texcoord=texCoord, _outputType='color3', _nodeName='baseColorMap',
                               _attrs={'expose': 'true', 'GLSLFX_usage': 'basecolor,diffuse,specular'})
    roughness_tex = lib.image(node_graph, texcoord=texCoord, _outputType='float', _nodeName='roughnessMap',
                              _attrs={'expose': 'true', 'GLSLFX_usage': 'roughness'})
    metalness_tex = lib.image(node_graph, texcoord=texCoord, _outputType='float', _nodeName='metalnessMap',
                              _attrs={'expose': 'true', 'GLSLFX_usage': 'metallic'})
    normal_tex = lib.image(node_graph, texcoord=texCoord, _outputType='color3', _nodeName='normalMap',
                           _attrs={'expose': 'true', 'GLSLFX_usage': 'normal'})


    ax.bind_output('base_color', base_color_tex, node_graph, shader_ref)
    ax.bind_output('roughness', roughness_tex, node_graph, shader_ref)
    ax.bind_output('metalness', metalness_tex, node_graph, shader_ref)
    ax.bind_output('normal', normal_tex, node_graph, shader_ref)


def ball(node_graph, node_def, shader_ref, lib):
    planes = 5
    starPlanes = 3.0
    radius = ax.createInput('star_size', 'float', node_graph, node_def, lib,
                            uiName='Star Size',
                            uiFolder='Procedural',
                            default=8.0,
                            min=0.0,
                            max=20.0)
    band_width = ax.createInput('band_width', 'float', node_graph, node_def, lib,
                                uiName='Band Width',
                                uiFolder='Procedural',
                                default=5.0,
                                min=0.0,
                                max=20.0)
    band_offset = ax.createInput('band_offset', 'float', node_graph, node_def, lib,
                                 uiName='Band Offset',
                                 uiFolder='Procedural',
                                 default=-50.0,
                                 min=-100.0,
                                 max=100.0)

    star_color = ax.createInput('star_color', 'color3', node_graph, node_def, lib,
                                uiName='Star Color',
                                uiFolder='Procedural',
                                default=mx.Color3(1.0, 0.0, 0.0),
                                min=mx.Color3(0.0, 0.0, 0.0),
                                max=mx.Color3(1.0, 1.0, 1.0))
    ball_color = ax.createInput('ball_color', 'color3', node_graph, node_def, lib,
                                uiName='Ball Color',
                                uiFolder='Procedural',
                                default=mx.Color3(1.0, 1.0, 0.0),
                                min=mx.Color3(0.0, 0.0, 0.0),
                                max=mx.Color3(1.0, 1.0, 1.0))
    band_color = ax.createInput('band_color', 'color3', node_graph, node_def, lib,
                                uiName='Band Color',
                                uiFolder='Procedural',
                                default=mx.Color3(.1, .1, 1.0),
                                min=mx.Color3(0.0, 0.0, 0.0),
                                max=mx.Color3(1.0, 1.0, 1.0))

    pos = lib.position(node_graph, _outputType='vector3')
    p2d = ax.swizzle(pos, target_type='vector2', channels='xz')
    plane_count = lib.constant(node_graph, value=0.0)
    base_color = ball_color

    zero = lib.constant(node_graph, value=0.0)
    one = lib.constant(node_graph, value=1.0)
    for p in range(planes):
        angle = p * 2.0 * math.pi / float(planes)
        pp = mx.Vector2(math.sin(angle), math.cos(angle))
        dp = ax.dot(pp, p2d)
        plane_count = plane_count + lib.ifgreater(node_graph, value1=0.0, value2=dp - radius, in1=one, in2=zero)
    base_color = lib.ifgreater(node_graph, value1=plane_count, value2=starPlanes, in1=star_color, in2=base_color)

    depth = ax.swizzle(pos, target_type='float', channels='y')
    c1 = lib.ifgreater(node_graph, value1=0.0, value2=depth + band_offset - band_width, in1=one, in2=zero)
    c2 = lib.ifgreater(node_graph, value1=0.0, value2=depth + band_offset + band_width, in1=zero, in2=one)
    base_color = lib.ifgreater(node_graph, value1=1.5, value2=c1 + c2, in1=base_color, in2=band_color)

    # c1 = depth - magic_band_offset < -band_width
    # c2 = depth - magic_band_offset > -band_width
    # base_color = lib.compare(node_graph, intest=c1 + c2, cutoff=1.5, in1=base_color, in2=band_color)

    # pp = _swizzle(pos, target_type='color3', channels='xyz')
    final_roughness = lib.constant(node_graph, value=.3)
    final_metalness = lib.constant(node_graph, value=0.0)
    final_normal = lib.constant(node_graph, value=mx.Vector3(.5, .5, 1.0))

    ax.bind_output('base_color', base_color, node_graph, shader_ref)
    ax.bind_output('specular_roughness', final_roughness, node_graph, shader_ref)
    ax.bind_output('metalness', final_metalness, node_graph, shader_ref)

    # TODO: Move this to bind_output?
    node_def.addOutput(name='base_color', type=base_color.node.getType())
    node_def.addOutput(name='specular_roughness', type=final_roughness.node.getType())
    node_def.addOutput(name='metalness', type=final_metalness.node.getType())
