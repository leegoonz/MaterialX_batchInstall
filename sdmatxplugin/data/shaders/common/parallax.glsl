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

float ray_intersect_rm(    // use linear and binary search
	in sampler2D heightmap,
	in vec2 dp,
	in vec2 ds)
{
	const int linear_search_steps=200;
	const int binary_search_steps=20;

	// current size of search window
	float size = 1.0/float(linear_search_steps);
	// current depth position
	float depth = 0.0;
	// search front to back for first point inside object
	for( int i=0;i<linear_search_steps;i++ )
	{
		float t = texture(heightmap,dp+ds*depth).r;

		if (depth<(1.0-t))
			depth += size;
	}
	// recurse around first point (depth) for closest match
	for( int ii=0;ii<binary_search_steps;ii++ )
	{
		size*=0.5;
		float t = texture(heightmap,dp+ds*depth).r;
		if (depth<(1.0-t))
			depth += (2.0*size);
		depth -= size;
	}
	return depth;
}

vec2 updateUV(
	in sampler2D heightmap,
	in vec3 pointToCameraDirWS,
	in vec3 n,
	in vec3 t,
	in vec3 b,
	in float Depth,
	in vec2 uv,
	in vec2 uvScale,
	in float tiling)
{
	if (Depth > 0.0)
	{
		float a = dot(n,-pointToCameraDirWS);
		vec3 s = vec3(
			dot(pointToCameraDirWS,t),
			dot(pointToCameraDirWS,b),
			a);
		s *= Depth/a*0.01;
		vec2 ds = s.xy*uvScale;
		uv = uv*tiling*uvScale;
		float d = ray_intersect_rm(heightmap,uv,ds);
		return uv+ds*d;
	}
	else return uv*tiling*uvScale;
}

