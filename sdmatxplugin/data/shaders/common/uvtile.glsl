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

uniform bool displayUVTileOnly = false;
uniform vec2 uvTileCoords = vec2(0,0);

// WARNING: Don't change declaration order without changing the initialization order of 
// cDefaultColor variable below !
struct DefaultColor
{
	vec4 mBaseColor;
	vec4 mNormal;
	vec4 mSpecularColor;
	vec4 mSpecularLevel;
	vec4 mMetallic;
	vec4 mRoughness;
	vec4 mAO;
	vec4 mEmissive;
	vec4 mOpacity;
	vec4 mGlossiness;
	vec4 mHeight;	
};

DefaultColor cDefaultColor = DefaultColor(
	vec4(0.5, 0.5, 0.5, 1.0),	// mBaseColor
	vec4(0.5, 0.5, 1.0, 1.0),	// mNormal
	vec4(0.0, 0.0, 0.0, 1.0),	// mSpecularColor
	vec4(0.0, 0.0, 0.0, 1.0),	// mSpecularLevel
	vec4(0.0, 0.0, 0.0, 1.0),	// mMetallic
	vec4(1.0, 1.0, 1.0, 1.0),	// mRoughness
	vec4(1.0, 1.0, 1.0, 1.0),	// mAO
	vec4(0.0, 0.0, 0.0, 1.0),	// mEmissive
	vec4(1.0, 1.0, 1.0, 1.0),	// mOpacity
	vec4(1.0, 1.0, 1.0, 1.0),	// mGlossiness
	vec4(0.0, 0.0, 0.0, 1.0)	// mHeight
	);

bool isInUdimTile(vec2 uv)
{
	if (uv.x < uvTileCoords.x || uv.x >= (uvTileCoords.x+1) ||
		uv.y < uvTileCoords.y || uv.y >= (uvTileCoords.y+1))
	{
		return false;
	}
	return true;
}

bool hasToDisableFragment(vec2 uv)
{
	if (displayUVTileOnly)
	{
		if (!isInUdimTile(uv))
		{
			return true;
		}
	}	
	return false;
}

vec2 getUDIMTileUV(vec2 uv)
{
	if (displayUVTileOnly)
	{
		if (isInUdimTile(uv))
		{
			return uv - uvTileCoords;
		}
	}
	return uv;
}

vec4 get2DSample(sampler2D map, vec2 uv, bool disableFragment, vec4 defaultColor)
{
	if (disableFragment)
		return defaultColor;
	return texture(map,uv);
}
