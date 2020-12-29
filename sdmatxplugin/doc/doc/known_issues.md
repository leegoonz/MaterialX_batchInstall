# Known Issues

This is beta software and there are many unsupported cases. This a non-exhaustive list of issues

## Setting ranges for exposed parameters
Unfortunately there is an issue in Substance Designer 10.1.1 making setting ranges for exposed
parameters not working. There is no great workaround for this at the moment but setting your defaults
to somewhere in the higher range of where you expect them to be used.
This issue is fixed in Substance Designer 10.2 and should go away if 
upgrading

## Primvar support

* Only a single UV set is support at this point in Designer and Painter. You can author with more
but it won't be visualized in the viewport.
* Anything beyond UV, positon, tangent, binormal are not supported. As an example vertex colors
are not supported.
* Painter has a limited understanding of object space. At the moment Object space will fall back
to world space.

## Texturing using SBS/SBSAR nodes in the MaterialX Graph
The recommended way to bind textures is through the usage parameter on the texture2d nodes.

If importing an SBS/SBSAR node in the MaterialX editor it will work in iRay with the limitation
that the normal map is converted to world space automatically which is unlikely to be how you
want to treat the normal map. 

When using the OpenGL viewport it won't work properly and it won't export to MaterialX properly.

## BRDF Authoring not supported
Currently the BRDF nodes from MaterialX are not supported. The only proeperly supported BRDF is standard_surface

## Substance Designer Auto-generates unsupported nodes
Substance Designer filters what nodes are possible to create in the MaterialX editor but in some circumstances
certain convenience operations create nodes that have no support in MaterialX meaning the export will break.

The currently known example of this is connecting a texture2d node directly to a color/float or similar
triggering the creation of unsupported nodes. 

This issue should be solved in Substance Designer 10.1.2

## MDL export of MaterialX graphs is not supported
At this point there are issues that can be triggered if exporting a MaterialX graph as an mdl file or mdle.

We hope to be able to support this in the future but it's not working properly at this point. 

## Previewing subgraphs
Subgraphs are currently not previewing properly and reporting an error even if they are valid

## Nodes missing in the Substance Designer library
There are MaterialX nodes missing in the Substance Designer library if browsing them 
through the MaterialX Graph. They are present in mdl/mtlx and in the space/tab menu 
so you can find them there for now.

## Normal maps in Painter shaders
The normal map support in Substance Painter is somewhat limited. Hare are some
known issues:

* Only normal maps are supported, this means height won't impact the normal map. 
* There has to be data in the normal channel, empty normal map channels will 
cause issues.

## File/Shader names can't start with numbers
When generating code there are symbols in GLSL that are taken directly from
Designer. This means if things are named in ways that are not compatible with
GLSL symbols it can trigger errors. In general it's a bad idea to start any 
symbol name with a number or other non alphabetic character at this point
since it can cause trouble