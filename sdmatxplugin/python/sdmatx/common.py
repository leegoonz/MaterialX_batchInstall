# Copyright 2020 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from collections import OrderedDict

mdlCustomTypes = [
    'export struct color2 { float r; float g; };',
    'export typedef color color3;',
    'export struct color4 { float r; float g; float b; float a; };']

mtlx_skippedTypes = ['color2', 'color4']
mtlx_connectableParameters = ['filename']  # requires a constructor

mtlxToMdl_types = OrderedDict([
    ('integer', 'int'),
    ('boolean', 'bool'),
    ('float', 'float'),
    ('vector2', 'float2'),
    ('vector3', 'float3'),
    ('vector4', 'float4'),
    ('matrix33', 'float3x3'),
    ('matrix44', 'float4x4'),
    ('string', 'string'),
    ('color2', 'color2'),
    ('color3', 'color3'),
    ('color4', 'color4'),
    ('filename', 'texture_2d'),
    ('surfaceshader', 'material')])

mdlTypes_defaultValues = {
    'int': '0',
    'bool': 'false',
    'float': '0.f',
    'float2': '0.f,0.f',
    'float3': '0.f,0.f,0.f',
    'float4': '0.f,0.f,0.f,0.f',
    'float3x3': '0.f',
    'float4x4': '0.f',
    'string': '""',
    'color2': '0.f, 0.f',
    'color3': '0.f, 0.f, 0.f',
    'color4': '0.f, 0.f, 0.f, 0.f',
    'texture_2d': '',
    'material': '',
}
mdl_vector_sizes = {
    'float':  1,
    'float2': 2,
    'float3': 3,
    'float4': 4,
    'color3': 3
}
mdl_swizzle_names = {
    'float':  ['r', 'x'],
    'float2': ['xy'],
    'float3': ['xyz'],
    'float4': ['xyzw'],
    'color3': ['rgb']
}
mtlx_force_type_decoration = {
    'image',
    'tiledimage'
}

mdl_unsupported_types = {'color2', 'color4'}
mtlx_unsupported_nodes = {
}

mdl_ubershader_implementation_map = {
    'physicallyMetallicRoughnessDk': """
let{
    //- Ambient occlusion mix
    color diffuse_color = baseColor*ambientOcclusion;

     //- Specular BTDF
    bsdf specular_btdf = df::microfacet_ggx_smith_bsdf(tint: diffuse_color, 
        roughness_u: 0.0, mode: df::scatter_transmit);
        
    //- Diffuse BRDF (connect roughness parameter to diffuse as well ?)
    bsdf diffuse_brdf = df::diffuse_reflection_bsdf(
        tint: diffuse_color, roughness: 0.0);

    //- Transparency mix
    bsdf transparent_opaque_mix = df::weighted_layer(
        weight: refraction, layer: specular_btdf , base: diffuse_brdf);

    //- Specular Anisotropy
    base::anisotropy_return specular_anisotropy = base::anisotropy_conversion(
        roughness: roughness*roughness,
        anisotropy: anisotropyLevel, anisotropy_rotation: anisotropyAngle,
        tangent_u: state::texture_tangent_u(0));

    //- Specular BRDF
    bsdf specular_brdf = df::microfacet_ggx_smith_bsdf(tint: color(1.0),
        roughness_u: specular_anisotropy.roughness_u,
        roughness_v: specular_anisotropy.roughness_v,
        tangent_u: specular_anisotropy.tangent_u);

    //- Dielectric Model
    float dielectric_reflectivity = specularLevel*0.08;

    //- Custom curve for specular/diffuse angular mix
    bsdf dielectric_model_ior_mixed = df::custom_curve_layer(
        normal_reflectivity: dielectric_reflectivity,
        grazing_reflectivity: 1.0, exponent: 5.0,
        weight: 1.0, layer: specular_brdf, base: transparent_opaque_mix);

    //- Metallic Model
    bsdf metallic_model = df::directional_factor(
        normal_tint: baseColor,
        grazing_tint: color(1.0),
        exponent: 3.0,
        base: specular_brdf);

    //- Metallic mix
    bsdf metallic_dielectric_mix = df::weighted_layer(
        weight: metallic,
        layer: metallic_model,
        base: dielectric_model_ior_mixed);

} in material(

    ior: color(refractionIOR),

    surface: material_surface(
        scattering: metallic_dielectric_mix,
        emission: material_emission(
            emission: df::diffuse_edf(),
            intensity: emissiveColor*2.86*emissiveIntensity,
            mode: intensity_radiant_exitance
        )
    ),

    volume: material_volume(
        absorption_coefficient: alg::base::core::volume_absorption(
            absorption: absorption, absorptionColor: absorptionColor),
        scattering_coefficient: alg::base::core::volume_scattering(
            scattering: scattering)
    ),

    geometry: material_geometry(
        normal: normal,
        displacement: alg::base::core::displacement(
            height: height, heightScale: heightScale),
        cutout_opacity: opacity
    )
);
""",
    'standard_surface': """
let{
    //
    //  MDL implementation of Autodesk StandardSurface
    //  https://autodesk.github.io/standard-surface/
    //

    //- SSS BRDF
    // TODO: this is a placeholder
    bsdf sss_bsdf = df::diffuse_reflection_bsdf(
        tint: base_color*base);
    bsdf upToSSS_bsdf = df::weighted_layer(
        weight: 1,
        layer: sss_bsdf,
        normal: normal);

    //- Diffuse transmission BRDF
    // TODO: parameterize. This transmission doesn't look great...
    bsdf diffuse_btdf = df::diffuse_transmission_bsdf(
        tint: subsurface_color);
    bsdf upToDiffuseBtdf_bsdf = df::weighted_layer(
        weight: thin_walled?1.0:0.0,
        layer: diffuse_btdf,
        base: upToSSS_bsdf,
        normal: -normal);

    //- Diffuse BRDF
    bsdf diffuse_brdf = df::diffuse_reflection_bsdf(
        tint: base_color*base,
        roughness: diffuse_roughness);
    bsdf upToDiffuse_bsdf = df::weighted_layer(
        weight: 1.0-subsurface,
        layer: diffuse_brdf,
        base: upToDiffuseBtdf_bsdf,
        normal: normal);


    //- Sheen BRDF
    // TODO: not available in MDL, using backscattering
    // (not a very good approximation)
    // Should be available with MDL 1.6
    bsdf sheen_brdf = df::backscattering_glossy_reflection_bsdf(
        tint: sheen_color, // sheen_color does not tint underlying layers
        roughness_u: sheen_roughness);
    // TODO: correct layering for sheen not available yet.
    bsdf upToSheen_bsdf = df::fresnel_layer(
        ior: 1.5,
        weight: sheen,
        layer: sheen_brdf,
        base: upToDiffuse_bsdf);

    //- Specular BTDF
    float transmission_roughness = specular_roughness+transmission_extra_roughness;
    base::anisotropy_return transmission_anisotropy2 = base::anisotropy_conversion(
        roughness: transmission_roughness*transmission_roughness,
        anisotropy: specular_anisotropy,
        anisotropy_rotation: specular_rotation*.5,
        tangent_u: state::texture_tangent_u(0));
    // TODO:
    // it's not fully clear in the spec whether transmission color should be
    // used here, as constant or combined with depth.
    // Both cases are documented and in conflict with each other.
    bsdf specular_btdf = df::simple_glossy_bsdf(
        // tint: transmission_color, // ?? see note above
        roughness_u: transmission_anisotropy2.roughness_u,
        roughness_v: transmission_anisotropy2.roughness_v,
        tangent_u: transmission_anisotropy2.tangent_u,
        mode: df::scatter_transmit);
    bsdf upToTransmission_bsdf = df::weighted_layer(
        weight: transmission,
        layer: specular_btdf,
        base: upToSheen_bsdf,
        normal: normal);

    //- Specular
    base::anisotropy_return specular_anisotropy2 = base::anisotropy_conversion(
        roughness: specular_roughness*specular_roughness,
        anisotropy: specular_anisotropy,
        anisotropy_rotation: specular_rotation*.5,
        tangent_u: state::texture_tangent_u(0));
    // TODO: thin film
    // note that coat_color only affects layers below, not coat itself
    bsdf specular_base_layer_brdf = df::microfacet_ggx_smith_bsdf(
        roughness_u: specular_anisotropy2.roughness_u,
        roughness_v: specular_anisotropy2.roughness_v,
        tangent_u: specular_anisotropy2.tangent_u);

    bsdf upToSpec_bsdf = df::color_fresnel_layer(
        ior: color(specular_IOR),
        weight: specular*specular_color,
        layer: specular_base_layer_brdf,
        base: upToTransmission_bsdf,
        normal: normal);

    //-  Metallic BRDF
    // The spec requires using Gulbrandsen parametrization where base_color is
    // reflectivity, and "g" (bias) is affected by specular_color.
    // Grazing tint is still white.
    // TODO: thin film
    mtlx::utilities::FresnelComplex fc =
        mtlx::utilities::artisticToConductorFresnel(
            base*base_color, specular*specular_color);
    bsdf metal_layer_brdf = df::fresnel_factor(
        ior: fc.real,
        extinction_coefficient: fc.imaginary,
        base: specular_base_layer_brdf
    );
    bsdf upToMetal_bsdf = df::weighted_layer(
        weight: metalness,
        layer: metal_layer_brdf,
        base: upToSpec_bsdf,
        normal: normal);

    //- Emission BRDF
    material_emission emission_layer = material_emission(
        emission: df::diffuse_edf(),
        intensity: emission_color*2.86*emission* // TODO: what is this constant
            math::lerp(color(1), coat_color, coat), // dim by coat
        mode: intensity_radiant_exitance);

    //- Coat BRDF
    // Caveat: we are unable to modulate the intensity of emission at grazing
    //         angles because that feature is not possible in MDL.
    base::anisotropy_return coat_anisotropy2 = base::anisotropy_conversion(
        roughness: coat_roughness*coat_roughness,
        anisotropy: coat_anisotropy,
        anisotropy_rotation: coat_rotation*.5,
        tangent_u: state::texture_tangent_u(0));
    // note that coat_color only affects layers below, not coat itself
    bsdf coat_layer_brdf = df::microfacet_ggx_smith_bsdf(
            roughness_u: coat_anisotropy2.roughness_u,
            roughness_v: coat_anisotropy2.roughness_v,
            tangent_u: coat_anisotropy2.tangent_u);
    bsdf upToCoat_bsdf = df::weighted_layer(
        weight: coat,
        layer: df::fresnel_layer(
            ior: coat_IOR,
            layer: coat_layer_brdf,
            base: df::color_weighted_layer(
                coat_color,
                layer: upToMetal_bsdf
            ),
            normal: coat_normal
        ),
        base: upToMetal_bsdf);

    // TODO: coat_affect_roughness and coat_affect_color are unsupported

    ////////////////////////////////////////////

} in material(

    ior: color(1.52),

    surface: material_surface(
        scattering: upToCoat_bsdf,
        emission: emission_layer
    ),

    // TODO: MDL expects this in meters.
    // TODO: transmission dispersion
    volume: material_volume(
        scattering: df::anisotropic_vdf(
            directional_bias: transmission_scatter_anisotropy
        ),
        absorption_coefficient: (
            color(1.0)-transmission_color)/transmission_depth,
        // TODO: the use transmission_depth here is undocumented, but seems to
        // make sense. Need to verify.
        scattering_coefficient: transmission_scatter/transmission_depth
    ),
    //    scattering_coefficient: alg::base::core::volume_scattering(
    //        scattering:
    //        scattering)

    geometry: material_geometry(
        displacement: alg::base::core::displacement(
            height: 0.0,
            heightScale: 0.0),
        //alg::base::core::displacement(
        //  height: height, heightScale: heightScale),
        cutout_opacity: math::luminance(opacity)
    )
);
"""
}


def getMdlVersion():
    return 'mdl 1.4;'


def getMdlType(mtlx_typedElement):
    mtlx_type = mtlx_typedElement.getType()
    mdl_type = mtlxToMdl_types[mtlx_type]
    return mdl_type


def getMtxType(mtlx_typedElement):
    return mtlx_typedElement.getType()


def isTypeSkipped(mtlx_typedElement):
    return mtlx_typedElement.getType() in mtlx_skippedTypes


def correctMdlInputForReservedWords(name):
    invalid_names = {
        'in',
        'default',
        'rotate'
    }
    if name in invalid_names:
        return name + '_'
    return name


def correctMdlFunctionForReservedWords(name):
    invalid_names = {
        'switch'
    }
    if name in invalid_names:
        return name + '_'
    return name


def getMdlName(mtlx_element):
    mdl_name = mtlx_element.getName()
    return correctMdlInputForReservedWords(mdl_name)


def getGeomPropDef(name):
    return 'getGeomPropDef_' + name + "()"


def getGeomPropDefs(doc):
    retval = '\n'
    geomprop_defs = doc.getGeomPropDefs()

    for geomprop_def in geomprop_defs:
        if geomprop_def.getSourceUri() != '':
            # Don't include geomprofs defined in an imported
            # document
            continue
        if not geomprop_def.hasGeomProp():
            raise BaseException('misidentified geometry property')

        geomProp = geomprop_def.getGeomProp()
        geomPropName = geomprop_def.getName()
        dataMap = {
            'position': 'state::position()',
            'normal': 'state::normal()',
            'tangent': 'state::texture_tangent_u({0})',
            'texcoord':
                'float2(state::texture_coordinate({0}).x, '
                'state::texture_coordinate({0}).y)'
        }
        typeMap = {
            'position': 'float3',
            'normal': 'float3',
            'tangent': 'float3',
            'texcoord': 'float2'
        }
        if geomProp not in dataMap.keys():
            retval += (
                '// Warning: No data map for geometry property {}\n'
                .format(geomProp))
            continue
        data = dataMap[geomProp]
        if '{0}' in data:
            index = 0
            if geomprop_def.hasIndex():
                index = geomprop_def.getIndex()
            data = data.format(str(index))

        if geomprop_def.hasSpace():
            transformMap = {
                'position': 'state::transform_point',
                'normal': 'state::transform_normal',
                'tangent': 'state::transform_vector',
            }
            space = 'state::coordinate_' + geomprop_def.getSpace()
            data = transformMap[geomProp] + "(state::coordinate_internal, " +\
                space + ", " + data + ")"

        retval += (
            'export {0} getGeomPropDef_{1}() [[ anno::hidden() ]]\n'
            '{{\n'
            '    return {2};\n'
            '}}\n'
            .format(typeMap[geomProp], geomPropName, data))

    return retval + '\n'


def getMdlDefaultValue(mtlx_valueElement, used_mdl_modules):
    from .modules import getMdlModulePathFromMtlxElement, \
        importMtlxDocsForModule
    mdl_type = getMdlType(mtlx_valueElement)
    defaultgeomprop = mtlx_valueElement.getAttribute('defaultgeomprop')
    if defaultgeomprop:
        geomprops = {
            'position': 'state::position()',
            'normal': 'state::normal()',
            'texcoord': 'float2(state::texture_coordinate(0).x, '
            'state::texture_coordinate(0).y)'
        }
        mdl_defaultValue = geomprops.get(defaultgeomprop, '')
        if mdl_defaultValue == '':
            geom_prop = getGeomPropDef(defaultgeomprop)
            # TODO: Make this more generic, here we assume geom props are in
            #  stdlib, they can come from anywhere
            importMtlxDocsForModule('stdlib', mtlx_valueElement.getDocument())
            mtlx_geomprop = mtlx_valueElement.getDocument().getGeomPropDef(
                defaultgeomprop)
            mdl_namespace = getMdlModulePathFromMtlxElement(mtlx_geomprop)
            if mdl_namespace != '':
                used_mdl_modules.add(mdl_namespace)
            mdl_defaultValue = \
                mdl_namespace + '::' + geom_prop if mdl_namespace != '' \
                else geom_prop
    else:
        value_string = mtlx_valueElement.getValueString()
        if value_string:
            if mdl_type == 'string':
                value_string = '"' + value_string + '"'
        else:
            value_string = mdlTypes_defaultValues[mdl_type]
        mdl_defaultValue = mdl_type + '({val})'.format(val=value_string)
    return mdl_defaultValue


def getMdlVariableDeclaration(mtlx_valueElement, used_mdl_modules):
    mdl_name = getMdlName(mtlx_valueElement)
    mdl_type = getMdlType(mtlx_valueElement)
    mdl_defaultValue = getMdlDefaultValue(mtlx_valueElement, used_mdl_modules)
    return (mdl_name, mdl_type, mdl_defaultValue)


def _getIsUIAdvanced(mtlx_input):
    ui_advanced_attr = mtlx_input.getAttribute('uiadvanced')
    if ui_advanced_attr == 'true':
        return True
    return False


def _getUIFolder(mtlx_input):
    ui_folder = mtlx_input.getAttribute('uifolder')
    if ui_folder:
        return ui_folder
    return ''


def getMdlParameters_mtlxInputs(mtlx_nodeDef, warnings, used_mdl_modules):
    # returns tuple: (name, type, default value, widgetHints)
    result = []
    for mtlx_input in mtlx_nodeDef.getInputs():
        if not isTypeSkipped(mtlx_input):
            widgetHints = {}
            widgetHints['connectableByDefault'] = not _getIsUIAdvanced(
                mtlx_input)
            page = _getUIFolder(mtlx_input)
            if page:
                widgetHints['uifolder'] = page
            mdl_name, mdl_type, mdl_defaultValue = \
                getMdlVariableDeclaration(mtlx_input, used_mdl_modules)
            variability = 'varying '
            result.append(
                (mdl_name, variability + mdl_type,
                    mdl_defaultValue, widgetHints))
        else:
            warnings.append(getSkippedTypeComment(mtlx_nodeDef, mtlx_input))
    return result


def getMdlParameters_mtlxParameters(mtlx_nodeDef, warnings, used_mdl_modules):
    # returns tuple: (name, type, default value, widgetHints)
    result = []
    for mtlx_parameter in mtlx_nodeDef.getParameters():
        if not isTypeSkipped(mtlx_parameter):
            widgetHints = {}
            widgetHints['connectableByDefault'] = \
                mtlx_parameter.getType() in mtlx_connectableParameters
            page = _getUIFolder(mtlx_parameter)
            if page:
                widgetHints['uifolder'] = page
            mdl_name, mdl_type, mdl_defaultValue = getMdlVariableDeclaration(
                mtlx_parameter, used_mdl_modules)
            variability = 'uniform '
            result.append(
                (mdl_name, variability + mdl_type,
                    mdl_defaultValue, widgetHints))
        else:
            warnings.append(getSkippedTypeComment(
                mtlx_nodeDef, mtlx_parameter))
    return result


def getMdlParameters(mtlx_nodeDef, warnings, used_mdl_modules):
    # TODO: this isn't great: inputs are always sorted before parameters,
    # which breaks the relative order that was given.
    return getMdlParameters_mtlxInputs(mtlx_nodeDef,
                                       warnings,
                                       used_mdl_modules) + \
        getMdlParameters_mtlxParameters(mtlx_nodeDef,
                                        warnings,
                                        used_mdl_modules)


def getHintString(widgetHints):
    ''' Given a dictionary of widget hints, generate mdl annotations '''
    hintString = ''
    hints = []

    if not widgetHints.get('connectableByDefault', True):
        hints.append('alg::base::annotations::visible_by_default(false)')
    if 'uifolder' in widgetHints:
        hints.append('anno::in_group("' + widgetHints['uifolder'] + '")')
    if hints:
        hintString = ',\n        '.join(hints)
        hintString = '[[\n        ' + hintString + '\n    ]]'
    return hintString


def getMdlSignature(mtx_func_name, mdl_parameters):
    mdlSignature_format = '{name}(\n    {parameters})'

    formatted_parameters = ""

    for mdl_name, mdl_type, default_val, widgetHints in mdl_parameters:
        assert mdl_name != "in"
        if default_val == '':
            formatted_parameters += "{type} {name}".format(
                type=mdl_type, name=mdl_name)
        else:
            formatted_parameters += "{type} {name}={default_val}".format(
                type=mdl_type, name=mdl_name, default_val=default_val)
        formatted_parameters += getHintString(widgetHints)
        formatted_parameters += ',\n    '
    if len(mdl_parameters) != 0:
        formatted_parameters = formatted_parameters.rstrip(',\n    ')
    return mdlSignature_format.format(name=mtx_func_name,
                                      parameters=formatted_parameters)
