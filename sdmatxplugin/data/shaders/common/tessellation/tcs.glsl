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

/////////////////////////////////// Control shader    
 
#version 410

layout(vertices = 3) out;

in vec4 oVS_Normal[];
in vec2 oVS_UV[];
in vec4 oVS_Tangent[];
in vec4 oVS_Binormal[];

out vec4 oTCS_Normal[];
out vec2 oTCS_UV[];
out vec4 oTCS_Tangent[];
out vec4 oTCS_Binormal[];

uniform float tessellationFactor;

void main()
{
   gl_TessLevelOuter[0] = tessellationFactor;
   gl_TessLevelOuter[1] = tessellationFactor;
   gl_TessLevelOuter[2] = tessellationFactor;
   gl_TessLevelInner[0] = tessellationFactor;
   gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;

   oTCS_Normal[gl_InvocationID]     = oVS_Normal[gl_InvocationID];
   oTCS_UV[gl_InvocationID]         = oVS_UV[gl_InvocationID];
   oTCS_Tangent[gl_InvocationID]    = oVS_Tangent[gl_InvocationID];
   oTCS_Binormal[gl_InvocationID]   = oVS_Binormal[gl_InvocationID];
}
