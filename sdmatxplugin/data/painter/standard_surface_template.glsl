            // Template for standard surfacc
            // hack to compute full normal including baked normals and painted
            // Transform normal from shader to tangent space
            mat3 to_ts = transpose(mat3(inputs.tangent,
                                        inputs.bitangent,
                                        inputs.normal));
            vec3 channel_normal_ts_unpacked = normalize(to_ts * normal);
            // Unpack baked normal
            vec3 texture_normal_ts = texture(base_normal_texture.tex, var_tex_coord0).xyz;

            // base_normal_y_coeff will be fed in from painter having the value 1 if the
            // baked maps are in GL tangent space and -1 in DX tangent space
            texture_normal_ts = normalUnpack(vec4(texture_normal_ts, 1.0), base_normal_y_coeff);
            // Blend normals
            vec3 normal_blended = normalBlendOriented(texture_normal_ts, channel_normal_ts_unpacked);
            // Transform blended normal to world space
            vec3 blended_normal_ws = normalize(normal_blended.x * inputs.tangent +
                                               normal_blended.y * inputs.bitangent +
                                               normal_blended.z * inputs.normal);

            LocalVectors vectors = computeLocalFrame(inputs, blended_normal_ws, 0);
            
            // Compute Standard Surface:ish
            float occlusion = getAO(inputs.sparse_coord) * getShadowFactor();
            float specOcclusion = specularOcclusionCorrection(occlusion, metalness, specular_roughness);
            vec3 diffColor = base_color * base;
            vec3 specColor = specular_color * specular;
            vec3 white = vec3(1);
            
            float specularF0 = abs((1.0 - specular_IOR) / (1.0 + specular_IOR));
            specularF0 = specularF0 * specularF0;
            vec3 specularF0C = vec3(specularF0,specularF0,specularF0); // reflectivity
            
            // apply metalness
            specularF0C = mix(specularF0C, diffColor, metalness); // replace by diffuse color
            specColor = specularF0C * mix(specColor, white, metalness); // no longer affect all lobe
            diffColor *= 1.0-metalness; // fade out diffuse black
            emissiveColorOutput(emission_color * emission);
            albedoOutput(diffColor);
            diffuseShadingOutput(occlusion * envIrradiance(blended_normal_ws));
            specularShadingOutput(specOcclusion * pbrComputeSpecular(vectors, specColor, specular_roughness));
