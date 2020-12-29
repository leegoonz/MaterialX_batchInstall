# Standard Surface shader compatibility
The implementations the Standard Surface shader in Designer and Painter are not 
supporting all features.
This is a list of features supported and not supported in different renderers.
## Designer GL
Supported

* base
* base_color
* metalness
* specular
* specular_color
* specular_IOR
* transmission (limited)
* sheen
* sheen_color
* sheen_roughness
* coat
* coat_color
* coat_roughness
* coat_IOR
* emission
* emission_color
* opacity (limited)

Not supported

* diffuse_roughness 
* specular_anisotropy
* specular_rotation
* transmission_color
* transmission_depth
* transmission_scatter
* transmission_scatter_anisotropy
* transmission_dispersion
* transmission_extra_roughness
* subsurface
* subsurface_color
* subsurface_radius
* subsurface_scale
* subsurface_anisotropy
* coat_anisotropy
* coat_rotation
* coat_affect_color
* coat_affect_roughness
* thin_film_thickness
* thin_film_IOR
* thin walled

## Designer MDL
Supported

* base
* base_color
* diffuse_roughness
* metalness
* specular
* specular_color
* specular_IOR
* specular_anisotropy
* specular_rotation
* transmission (limited)
* transmission_color
* transmission_depth
* transmission_scatter
* transmission_extra_roughness
* sheen
* sheen_color
* sheen_roughness
* coat
* coat_color
* coat_roughness
* coat_anisotropy
* coat_IOR
* emission
* emission_color
* opacity (limited)

Not supported

* transmission_scatter_anisotropy
* transmission_dispersion
* subsurface
* subsurface_color
* subsurface_radius
* subsurface_scale
* subsurface_anisotropy
* coat_rotation
* coat_affect_color
* coat_affect_roughness
* thin_film_thickness
* thin_film_IOR
* thin walled


## Painter
Supported

* base
* base_color
* metalness
* specular
* specular_color
* specular_IOR
* emission
* emission_color

Not supported

* diffuse_roughness 
* specular_anisotropy
* specular_rotation
* transmission
* transmission_color
* transmission_depth
* transmission_scatter
* transmission_scatter_anisotropy
* transmission_dispersion
* transmission_extra_roughness
* sheen
* sheen_color
* sheen_roughness
* subsurface
* subsurface_color
* subsurface_radius
* subsurface_scale
* subsurface_anisotropy
* coat
* coat_color
* coat_roughness
* coat_IOR
* coat_anisotropy
* coat_rotation
* coat_affect_color
* coat_affect_roughness
* thin_film_thickness
* thin_film_IOR
* thin walled
* opacity