# Rendering in Arnold for Maya
Arnold for Maya has a MaterialX shader called aiMaterialXShader which
can be used to render materials authored in the Designer
MaterialX Plugin.

To use a Designer MaterialX export in Arnold do the following things
1. Export MaterialX, make sure you export with dependencies and 
   textures
2. Assign an aiMaterialXShader to an object in your scene
3. Point the MaterialX Shader attribute to the exported MaterialX
   document
4. Add the directory of your MaterialX document to the 
   Arnold Texture Search Path. This is located in the 
   __Arnold Render Settings->System->Search Paths__. Note that it's the
   document directory and not the texture directory that should be added. The 
   texture paths in the exported document are relative to the document
   itself.

## Limitations
At the moment you can't tweak MaterialX parameters directly on the 
MaterialX shader. In case you want to iterate, you'll need to tweak
parameters in Designer and reexport. Fortunately Arnold detects
updates to the files and will reload the updated shader when a new
rendering is triggered.

## Notes
This documentation was written for mtoa version 4.0.4.2 for Maya 2019
and it might vary between different versions.
