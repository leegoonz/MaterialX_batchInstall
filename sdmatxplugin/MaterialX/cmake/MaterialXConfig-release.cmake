#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "MaterialXCore" for configuration "Release"
set_property(TARGET MaterialXCore APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXCore PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXCore.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXCore )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXCore "${_IMPORT_PREFIX}/lib/MaterialXCore.lib" )

# Import target "MaterialXFormat" for configuration "Release"
set_property(TARGET MaterialXFormat APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXFormat PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXFormat.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXFormat )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXFormat "${_IMPORT_PREFIX}/lib/MaterialXFormat.lib" )

# Import target "MaterialXGenShader" for configuration "Release"
set_property(TARGET MaterialXGenShader APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXGenShader PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXGenShader.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXGenShader )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXGenShader "${_IMPORT_PREFIX}/lib/MaterialXGenShader.lib" )

# Import target "MaterialXGenGlsl" for configuration "Release"
set_property(TARGET MaterialXGenGlsl APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXGenGlsl PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXGenGlsl.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXGenGlsl )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXGenGlsl "${_IMPORT_PREFIX}/lib/MaterialXGenGlsl.lib" )

# Import target "MaterialXGenOsl" for configuration "Release"
set_property(TARGET MaterialXGenOsl APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXGenOsl PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXGenOsl.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXGenOsl )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXGenOsl "${_IMPORT_PREFIX}/lib/MaterialXGenOsl.lib" )

# Import target "MaterialXRender" for configuration "Release"
set_property(TARGET MaterialXRender APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXRender PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXRender.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXRender )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXRender "${_IMPORT_PREFIX}/lib/MaterialXRender.lib" )

# Import target "MaterialXRenderOsl" for configuration "Release"
set_property(TARGET MaterialXRenderOsl APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXRenderOsl PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXRenderOsl.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXRenderOsl )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXRenderOsl "${_IMPORT_PREFIX}/lib/MaterialXRenderOsl.lib" )

# Import target "MaterialXRenderHw" for configuration "Release"
set_property(TARGET MaterialXRenderHw APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXRenderHw PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXRenderHw.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXRenderHw )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXRenderHw "${_IMPORT_PREFIX}/lib/MaterialXRenderHw.lib" )

# Import target "MaterialXRenderGlsl" for configuration "Release"
set_property(TARGET MaterialXRenderGlsl APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXRenderGlsl PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/MaterialXRenderGlsl.lib"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXRenderGlsl )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXRenderGlsl "${_IMPORT_PREFIX}/lib/MaterialXRenderGlsl.lib" )

# Import target "MaterialXView" for configuration "Release"
set_property(TARGET MaterialXView APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(MaterialXView PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/MaterialXView.exe"
  )

list(APPEND _IMPORT_CHECK_TARGETS MaterialXView )
list(APPEND _IMPORT_CHECK_FILES_FOR_MaterialXView "${_IMPORT_PREFIX}/bin/MaterialXView.exe" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
