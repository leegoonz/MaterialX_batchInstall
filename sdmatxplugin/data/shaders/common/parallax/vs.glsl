/*
Copyright (c) 2018, Allegorithmic. All rights reserved.

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

/////////////////////////////// Vertex shader
#version 330

in vec4 iVS_Position;
in vec4 iVS_Normal;
in vec2 iVS_UV;
in vec4 iVS_Tangent;
in vec4 iVS_Binormal;

out vec3 iFS_Normal;
out vec2 iFS_UV;
out vec3 iFS_Tangent;
out vec3 iFS_Binormal;
out vec3 iFS_PointWS;

uniform mat4 worldMatrix;
uniform mat4 worldViewProjMatrix;
uniform mat4 worldInverseTransposeMatrix;

void main()
{
    gl_Position = worldViewProjMatrix * iVS_Position;
    iFS_Normal = normalize((worldInverseTransposeMatrix * iVS_Normal).xyz);
    iFS_UV = iVS_UV;
    iFS_Tangent = normalize((worldInverseTransposeMatrix * iVS_Tangent).xyz);
    iFS_Binormal = normalize((worldInverseTransposeMatrix * iVS_Binormal).xyz);
    iFS_PointWS = (worldMatrix * iVS_Position).xyz;
}
