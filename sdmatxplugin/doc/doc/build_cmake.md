# Building MaterialX for the Substance Designer Plugin

These instructions will help you to build a MaterialX package for the MaterialX Substance 
Designer plugin. They are generally made for linux and mac since there are no prebuilt 
packages but should be easy to apply to windows too
## Prerequisites
* Python 3.7 (ideally 3.7.6)
* A moderately modern gcc/clang toolchain. We have seen issues with gcc 4 so make sure you have something fairly modern
* CMake

Building or installing these are beyond the scope of this tutorial and varies depending
on the system so it's left out.

## Getting the MaterialX source code
Clone MaterialX 1.37.2 or master (at the point of writing) from github. The main page is here the [MaterialX Github](https://github.com/materialx/MaterialX).
A typical command line looks something like this.

```git clone https://github.com/materialx/MaterialX.git```

This will put the MaterialX source code in a directory called MaterialX. Now enter this directory

```cd MaterialX```

Note that this will checkout the master branch. To be safe you might want to use the 1.37.2 branch
```git checkout v1.37.2```

Finally sync the submodules recursively

```git submodule update --init --recursive```

## Configuring the build
Create a build directory and enter it

```
mkdir build
cd build
```

For the plugin, what we need is a separated installation directory rather than installing
MaterialX system wide. We also want to make sure we build python bindings and the MaterialX
viewer

```
cmake .. \
	-DMATERIALX_BUILD_PYTHON=1 \
	-DMATERIALX_INSTALL_PYTHON=1 \
	-DMATERIALX_PYTHON_EXECUTABLE=/usr/bin/python3 \
        -DMATERIALX_BUILD_VIEWER=TRUE \
	-DMATERIALX_BUILD_DOCS=0 \
	-DMATERIALX_BUILD_VIEW=0 \
	-DMATERIALX_TEST_VIEW=0 \
	-DCMAKE_INSTALL_PREFIX=./installed/MaterialX
```
* ```MATERIALX_PYTHON_EXECUTABLE``` should be the full path to the python3.7 executable you
intend to build against
* ```CMAKE_INSTALL_PREFIX``` is set to install everything in a subdirectory to the build
directory called ```installed/MaterialX``` which we can copy into our installation directory.

In this process there might be errors related to libraries missing on your system and
you might need to install some of them to get everything running. How to do this depends
on your system and is outside the scope of these instructions.

## Building MaterialX
To build run

```make -j4 install```

This will compile the components we want and install all files in a structured form.
```-j4``` decides how many parallel build operations can be run at the same time and 
should ideally be in the same ballpark as the number of cores your computer has for
best build performance.

## Installing
When the operation is done, assuming everything worked, copy the ```MaterialX``` directory from 
the ```installed``` directory to the ```sdmatxplugin``` directory.
