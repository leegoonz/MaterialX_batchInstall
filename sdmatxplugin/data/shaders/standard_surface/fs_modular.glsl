/*
Copyright (c) 2019, Allegorithmic. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
   * Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
   * Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.
   * Neither the name of the Allegorithmic nor the
     names of its contributors may be used to endorse or promote products
     derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL ALLEGORITHMIC BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

//////////////////////////////// Fragment shader
#version 400

#include "../common/common.glsl"

// input geometry properties
in vec3 iFS_Normal;
in vec2 iFS_UV;
in vec3 iFS_Tangent;
in vec3 iFS_Binormal;
in vec3 iFS_PointWS;

// final fragment color
out vec4 ocolor0;

// camera
uniform mat4 viewInverseMatrix;
uniform mat4 worldMatrix;
uniform mat4 worldInverseTransposeMatrix;

// illumination
uniform vec3 Lamp0Pos = vec3(0.0,0.0,70.0);
uniform vec3 Lamp0Color = vec3(1.0,1.0,1.0);
uniform float Lamp0Intensity = 1.0;
uniform vec3 Lamp1Pos = vec3(70.0,0.0,0.0);
uniform vec3 Lamp1Color = vec3(0.198,0.198,0.198);
uniform float Lamp1Intensity = 1.0;

// Globals
// comes from the lighting parameters
uniform float AmbiIntensity = 1.0;
// this is exposed... not sure we want to keep it
uniform float EmissiveIntensity = 1.0;
// comes from the rendering parameters
uniform int parallax_mode = 0;

// substance variables
uniform float tiling = 1.0;
uniform vec3 uvwScale = vec3(1.0, 1.0, 1.0);
uniform bool uvwScaleEnabled = false;
uniform float envRotation = 0.0;
uniform float tessellationFactor = 4.0;
uniform float heightMapScale = 1.0;
uniform bool flipY = true;
uniform bool perFragBinormal = true;
uniform bool sRGBBaseColor = true;

// uniform sampler2D heightMap;
//uniform sampler2D normalMap;
//uniform sampler2D baseColorMap;
//uniform sampler2D metallicMap;
//uniform sampler2D roughnessMap;
//uniform sampler2D aoMap;
//uniform sampler2D emissiveMap;
//uniform sampler2D specularLevel;
//uniform sampler2D opacityMap;
uniform sampler2D environmentMap;

// Number of miplevels in the envmap
uniform float maxLod = 12.0;

// Actual number of samples in the table
uniform int nbSamples = 16;

// Irradiance spherical harmonics polynomial coefficients
// This is a color 2nd degree polynomial in (x,y,z), so it needs 10 coefficients
// for each color channel. This is used by pbr_ibl.glsl
uniform vec3 shCoefs[10];

// This must be included after the declaration of the uniform arrays since they
// can't be passed as functions parameters for performance reasons (on macs)
#include "../common/pbr_ibl.glsl"

// This file is often regenerated. Must be in a search path.
#include "matx.glsl"

void main()
{
    //////////////////////// COMPUTE PATTERNS /////////////////////////
    float base;
    vec3 base_color;
    float diffuse_roughness;
    float specular;
    vec3 specular_color;
    float specular_roughness;
    float specular_IOR;
    float specular_anisotropy;
    float specular_rotation;
    float metalness;
    float transmission;
    vec3 transmission_color;
    float transmission_depth;
    vec3 transmission_scatter;
    float transmission_scatter_anisotropy;
    float transmission_dispersion;
    float transmission_extra_roughness;
    float subsurface;
    vec3 subsurface_color;
    vec3 subsurface_radius;
    float subsurface_scale;
    float subsurface_anisotropy;
    float sheen;
    vec3 sheen_color;
    float sheen_roughness;
    bool thin_walled;
    vec3 normal = vec3(0.0,0.0,0.0);
    vec3 tangent;
    float coat;
    vec3 coat_color;
    float coat_roughness;
    float coat_anisotropy;
    float coat_rotation;
    float coat_IOR;
    vec3 coat_normal;
    float coat_affect_color;
    float coat_affect_roughness;
    float thin_film_thickness;
    float thin_film_IOR;
    float emission;
    vec3 emission_color;
    vec3 opacity;
    vec2 uv;
    bool disableFragment;

    // Call generated code, fill all pattern outputs
    matx_compute(base,
                 base_color,
                 diffuse_roughness,
                 metalness,
                 specular,
                 specular_color,
                 specular_roughness,
                 specular_IOR,
                 specular_anisotropy,
                 specular_rotation,
                 transmission,
                 transmission_color,
                 transmission_depth,
                 transmission_scatter,
                 transmission_scatter_anisotropy,
                 transmission_dispersion,
                 transmission_extra_roughness,
                 subsurface,
                 subsurface_color,
                 subsurface_radius,
                 subsurface_scale,
                 subsurface_anisotropy,
                 sheen,
                 sheen_color,
                 sheen_roughness,
                 coat,
                 coat_color,
                 coat_roughness,
                 coat_anisotropy,
                 coat_rotation,
                 coat_IOR,
                 coat_normal,
                 coat_affect_color,
                 coat_affect_roughness,
                 thin_film_thickness,
                 thin_film_IOR,
                 emission,
                 emission_color,
                 opacity,
                 thin_walled,
                 normal,
                 tangent,
                 uv,
                 disableFragment);


    //////////////////////// COMPUTE ILLUMINATION /////////////////////////

    // rewire normals
    // Note: everything expects the shading normal to be in world space.
    // If a network reads the tangent space normal, it needs to be transformed in
    // the network itself before being fed to this shader.
    vec3 normalWS = iFS_Normal;
    vec3 tangentWS = iFS_Tangent;
    vec3 binormalWS = perFragBinormal ?
        fixBinormal(normalWS,tangentWS,iFS_Binormal) : iFS_Binormal;

    vec3 cameraPosWS = viewInverseMatrix[3].xyz;
    vec3 pointToLight0DirWS = Lamp0Pos - iFS_PointWS;
    float pointToLight0Length = length(pointToLight0DirWS);
    pointToLight0DirWS *= 1.0 / pointToLight0Length;
    vec3 pointToLight1DirWS = Lamp1Pos - iFS_PointWS;
    float pointToLight1Length = length(Lamp1Pos - iFS_PointWS);
    pointToLight1DirWS *= 1.0 / pointToLight1Length;
    vec3 pointToCameraDirWS = normalize(cameraPosWS - iFS_PointWS);

    // ------------------------------------------
    // Light precomputation
    float NdotL0 = max(0.0, dot(normal, pointToLight0DirWS));
    vec3 lamp0Illum = NdotL0*Lamp0Color*lampAttenuation(pointToLight0Length)*
        Lamp0Intensity*M_PI;
    float NdotL1 = max(0.0, dot(normal, pointToLight1DirWS));
    vec3 lamp1Illum = NdotL1*Lamp1Color*lampAttenuation(pointToLight1Length)*
        Lamp1Intensity*M_PI;

    // ------------------------------------------
    // BRDF precomputation
    const vec3 white = vec3(1.0,1.0,1.0);
    // we use flat (non squared) roughness here, it matches squared roughness in MDL
    // if you see mismatches, try cranking up the sample count.
    const float minRoughness=1e-4;

    vec3 diffColor = base_color*base;

    vec3 specColor = specular_color*specular; // tints the whole spec lobe
    float vdh = max(0.0, dot(normal, pointToCameraDirWS));
    float specularF0 = abs((1.0 - specular_IOR) / (1.0 + specular_IOR));
    specularF0 = specularF0 * specularF0;
    vec3 specularF0C = vec3(specularF0,specularF0,specularF0); // reflectivity
    // this is rather approximate:
    // face-forward based on fresnel and IOR
    // This must be computed before metalness is applied.
    vec3 spec_reflectanceEnv = fresnel(vdh, specularF0C);
    vec3 spec_reflectanceEnvColored = specColor*spec_reflectanceEnv;
    specular_roughness = max(minRoughness, specular_roughness);

    float coat_vdh = max(0.0, dot(coat_normal, pointToCameraDirWS));
    float coatF0 = abs((1.0 - coat_IOR) / (1.0 + coat_IOR));
    coatF0 = coatF0 * coatF0;
    vec3 coatF0C = vec3(coatF0,coatF0,coatF0); // reflectivity
    vec3 coat_reflectanceEnv = fresnel(coat_vdh, coatF0C);
    vec3 coat_attenuation = (white-coat*coat_reflectanceEnv) * // conservation
        mix(white, coat_color, coat); // coat tinting
    coat_roughness = max(minRoughness, coat_roughness);

    vec3 sheenColor = sheen * sheen_color;

    vec3 emisColor = emission_color * emission;

    // apply metalness
    specularF0C = mix(specularF0C, diffColor, metalness); // replace by diffuse color
    vec3 specularF90C = mix(white, specColor, metalness); // tint extinctionCoefficient
    specColor = mix(specColor, white, metalness); // no longer affect all lobe
    diffColor *= 1.0-metalness; // fade out diffuse black

    // apply coat tint
    specColor *= coat_attenuation;
    diffColor *= coat_attenuation;
    emisColor *= coat_attenuation;
    sheenColor *= coat_attenuation;

    // apply transmission. Premultiply unaffected lobes, and then multiply final opacity
    float transmission_attenuation = max(0.001, 1.0-transmission);
    float transmission_amplifier = 1.0/transmission_attenuation;
    emisColor *= transmission_amplifier;
    specColor *= transmission_amplifier;
    coat *= transmission_amplifier;
    sheenColor *= transmission_amplifier;

    // TODO: anisotropy
    // TODO: thin film
    // ------------------------------------------
    // Point Lights Illumination

    // TODO add some tinting using extinction color:
    // specularF90C. Empirically, it should depend on light direction and view direction
    // (not so much normal)
    vec3 contrib0Coat = coat*microfacets_brdf(
        coat_normal, pointToLight0DirWS, pointToCameraDirWS, coatF0C, coat_roughness);
    vec3 contrib0Spec = specColor * microfacets_brdf(
        normal, pointToLight0DirWS, pointToCameraDirWS, specularF0C, specular_roughness);
    vec3 contrib0Sheen = sheenColor * sheen_brdf(
        normal, pointToLight0DirWS, pointToCameraDirWS, sheen_roughness);
    vec3 contrib0Diff = diffuse_brdf(
        normal, pointToLight0DirWS, pointToCameraDirWS, diffColor);
    vec3 contrib0Thin = diffuse_brdf(
        -normal, pointToLight0DirWS, pointToCameraDirWS, subsurface_color);
    vec3 contrib0 = lamp0Illum * (
        contrib0Spec +
        mix(contrib0Diff,contrib0Thin,subsurface) +
        contrib0Coat +
        contrib0Sheen);

    vec3 contrib1Coat = coat*microfacets_brdf(
        coat_normal, pointToLight1DirWS, pointToCameraDirWS, coatF0C, coat_roughness);
    vec3 contrib1Spec = specColor * microfacets_brdf(
        normal, pointToLight1DirWS, pointToCameraDirWS, specularF0C, specular_roughness);
    vec3 contrib1Sheen = sheenColor * sheen_brdf(
        normal, pointToLight1DirWS, pointToCameraDirWS, sheen_roughness);
    vec3 contrib1Diff = diffuse_brdf(
        normal, pointToLight1DirWS, pointToCameraDirWS, diffColor);
    vec3 contrib1Thin = diffuse_brdf(
        -normal, pointToLight1DirWS, pointToCameraDirWS, subsurface_color);
    vec3 contrib1 = lamp1Illum * (
        contrib1Spec +
        mix(contrib1Diff,contrib1Thin,subsurface) +
        contrib1Coat +
        contrib1Sheen);

    // ------------------------------------------
    // IBL Illumination
    vec3 Tp,Bp;
    computeSamplingFrame(tangentWS, binormalWS, coat_normal, Tp, Bp);
    vec3 contribEnvCoat = IBLSpecularContribution(
        environmentMap, envRotation, maxLod, nbSamples,
        normalWS, coat_normal,
        Tp, Bp,
        pointToCameraDirWS,
        coatF0C, coat_roughness);
    contribEnvCoat *= coat;

    computeSamplingFrame(tangentWS, binormalWS, normal, Tp, Bp);
    vec3 contribEnvSpec = IBLSpecularContribution(
        environmentMap, envRotation, maxLod, nbSamples,
        normalWS, normal,
        Tp, Bp,
        pointToCameraDirWS,
        specularF0C, specular_roughness);
    // this is also approximate...
    contribEnvSpec *= specColor * mix(
        white, specularF90C, spec_reflectanceEnv);

    // TODO: this is busted
    vec3 contribEnvSheen = IBLSheenContribution(
        environmentMap, envRotation, maxLod, nbSamples,
        normal, Tp, Bp, pointToCameraDirWS,
        sheen_roughness);
    contribEnvSheen *= sheenColor;

    vec3 contribEnvDiff = (white-spec_reflectanceEnvColored) *
        diffColor *
        irradianceFromSH(rotate(normal,envRotation));
    // Thin Wall always true in this implementation
    vec3 contribEnvThin = (white-spec_reflectanceEnvColored) *
        subsurface_color *
        irradianceFromSH(rotate(-normal,envRotation));

    vec3 contribEnv = AmbiIntensity*(
        mix(contribEnvDiff, contribEnvThin, subsurface) +
        contribEnvSpec + contribEnvCoat + contribEnvSheen);

    // ------------------------------------------
    //Emissive
    vec3 contribEmissive = emisColor * EmissiveIntensity;

    // ------------------------------------------
    // Gather results
    vec3 finalColor = contrib0 + contrib1 + contribEnv + contribEmissive;

    // ------------------------------------------
    // Compute total opacity
    // we cannot support colored opacity.
    float finalOpacity = opacity[0] * transmission_attenuation;

    // Final Color
    ocolor0 = vec4(finalColor, finalOpacity);
}
