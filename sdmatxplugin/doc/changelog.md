# Changelog
v 0.1.5
* Updated floor sample to avoid issues with Designer 10.2.0
* Updated Shader bindings to be more compatible with third
  party consumers of MaterialX documents
* Updated paths to always use forward slashes
* Added documentation on how to use shaders in Arnold for Maya 
* Corrected bug in tiled image in MDL
* Added support for the normal map node

v 0.1.4

* Added Painter Template and Sample
* Corrected painter shader so specular color affects non-metallic materials instead of metallic ones
* Corrected Painter Normal map tangent base to adapt automatically for the baked normals
* Added html documentation
* Added support for upcoming changes to MaterialX master preserving 1.37.1 compatibility

v 0.1.3

* Split out glsl codegen to a separate python module
* Added a configuration file for configuring paths and the viewer
* Removed issue related to finding the Substance Designer Document directory when HOME environment variable specified on windows
* Added documentation for what features are supported and not in standard surface in different implementations
* Updated floor sample for smaller export
* Added missing image for floor sample documentation
* Changed mat ball mesh in the package to make object space align with the object
space for the default version of that model in Substance Designer
* Added documentation notes on how to make coordinate systems align between 
applications
* Corrected iRay/MDL implementation of modulo to be consistent with GLSL

v 0.1.2

* Fixed issue with the path for user mdl documents breaking subgraph export
* Added missing sample Floor.sbs
* Added toolbar icon for the MaterialX toolbar
* Added translation for atan2
* Added compatibility checks on startup to make it easier to understand what goes wrong during initialization
* Added check for changes to mtlx modules on startup to decide on whether to rebuild mdl files
* Corrected behavior for tweaking parameters with min/max defined in GL viewport
* More feedback when exporting subgraphs

v 0.1.1

* Corrected documentation: sduserplugins is corretly spelled now
* Renamed checkbox when exporting MaterialX files so it properly says it's about exporting the Standard Library
* Fixed issue with more recent MaterialX builds breaking conversion of MaterialX standard library to MDL
* Added specific error message related to unsupported nodes that are added by Designer when connecting a texture 
directly to a color, float etc.

v 0.1.0

Initial Release