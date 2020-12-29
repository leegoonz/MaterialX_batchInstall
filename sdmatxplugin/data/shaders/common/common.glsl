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

#define M_PI 3.1415926535897932384626433832795

#define DISTANCE_ATTENUATION_MULT 0.001

float srgb_to_linear(float c)
{
	float lin = c <= 0.04045 ? c/12.92 : pow(((c+0.055)/1.055), 2.4);
    return lin;
}


vec3 srgb_to_linear(vec3 c)
{
	return vec3(srgb_to_linear(c.x), srgb_to_linear(c.y), srgb_to_linear(c.z));
}



vec3 fixNormalSample(vec3 v, bool flipY)
{
	vec3 res = (v - vec3(0.5,0.5,0.5))*2.0;
	res.y = flipY ? -res.y : res.y;
	return res;
}

vec3 fixBinormal(vec3 n, vec3 t, vec3 b)
{
	vec3 nt = cross(n,t);
	return sign(dot(nt,b))*nt;
}

vec3 rotate(vec3 v, float a)
{
	float angle =a*2.0*M_PI;
	float ca = cos(angle);
	float sa = sin(angle);
	return vec3(v.x*ca+v.z*sa, v.y, v.z*ca-v.x*sa);
}

float lampAttenuation(float distance)
{
	return 1.0/(1.0+DISTANCE_ATTENUATION_MULT*distance*distance);
}
