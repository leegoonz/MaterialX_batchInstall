#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
import subprocess
import sys

import logging
logger = logging.getLogger("SDMaterialX")


def invoke_mtlx2mdl(mtlx2mdl_script,
                    module_name,
                    python_executable,
                    mdl_root,
                    generate_shared=False,
                    mdl_shared_name=None,
                    materialx_search_path=None):
    if generate_shared:
        cmd = [python_executable,
               mtlx2mdl_script,
               '--module_name', module_name,
               '--generate_shared',
               '--mdl_root', mdl_root]
    else:
        if mdl_shared_name is None:
            raise BaseException('Shared module name must be provided when '
                                'converting a module')
        cmd = [python_executable,
               mtlx2mdl_script,
               '--module_name', module_name,
               '--mdl_shared_name', mdl_shared_name,
               '--mdl_root', mdl_root]
    if materialx_search_path:
        cmd += ['--mtlx_search_path', materialx_search_path]

    target_file = os.path.join(mdl_root, module_name + '.mdl')
    with open(target_file, 'w') as target:
        logger.info("Generating %s." % target_file)
        logger.info('Command: ' + ' '.join(cmd))
        p = subprocess.Popen(cmd, stdout=target, stderr=subprocess.PIPE)
        stdout_data, stderr_data = p.communicate()
        p.wait()

        if p.returncode != 0:
            logger.error('Failed')
            if stdout_data:
                logger.error('stdout:')
                logger.error(stdout_data.decode('utf-8'))
            if stderr_data:
                logger.error('stderr:')
                logger.error(stderr_data.decode('utf-8'))
            sys.stdout.flush()
            raise subprocess.CalledProcessError(
                cmd=subprocess.list2cmdline(cmd), returncode=p.returncode)


def createAlglib(alglib_defs_file, alglib_graph_file, alglib_script, data_path,
                 mtlx_search_path, python_executable):
    cmd = [python_executable,
           alglib_script,
           '--declaration-file', os.path.join(data_path,
                                              'mtlx',
                                              alglib_defs_file),
           '--definition-file', os.path.join(data_path,
                                             'mtlx',
                                             alglib_graph_file),
           '--materialx-search-path', mtlx_search_path]
    logger.info("Generating Alglib.")
    dest_dir = os.path.join(data_path, 'mtlx', 'alglib')
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = p.communicate()
    p.wait()
    if p.returncode != 0:
        logger.error('Failed')
        if stdout_data:
            logger.error('stdout:')
            logger.error(stdout_data.decode('utf-8'))
        if stderr_data:
            logger.error('stderr:')
            logger.error(stderr_data.decode('utf-8'))
        sys.stdout.flush()
        raise subprocess.CalledProcessError(
            cmd=subprocess.list2cmdline(cmd), returncode=p.returncode)
    logger.info('Done')


def main():
    # Figure out paths and names
    import sdmatx
    script_path = os.path.abspath(os.path.dirname(__file__))
    data_path = os.path.abspath(os.path.join(script_path, '..', '..', 'data'))
    if len(sys.argv) > 1:
        mdl_output_path = os.path.abspath(sys.argv[1])

    else:
        mdl_output_path = os.path.abspath(
            os.path.join(data_path, 'mdl', 'mtlx'))

    if not os.path.isdir(mdl_output_path):
        os.makedirs(mdl_output_path)

    # We can't use the standard search paths here since it's meant to be run
    # in-source
    script_path = os.path.dirname(__file__)
    # Note alglib before standard surface to make sure our version of standard
    # surface is being used
    # TODO: Redo paths so this is done explicitly rather than include order
    mtlx_search_path = sdmatx.makeMtlxPathString([
        os.path.abspath(os.path.join(script_path,
                                     '..',
                                     '..',
                                     'data',
                                     'mtlx')),
        os.path.abspath(os.path.join(script_path,
                                     '..',
                                     'thirdparty',
                                     'materialx',
                                     'libraries')),
        os.path.abspath(os.path.join(script_path,
                                     '..',
                                     'thirdparty',
                                     'MaterialX')),
    ])

    alglib_defs_file = os.path.join('alglib', 'alglib_defs.mtlx')
    alglib_graph_file = os.path.join('alglib', 'alglib_ng.mtlx')

    mdl_shared_name = 'shared'

    python_executable = sys.executable

    alglib_script = os.path.join(script_path, 'generatealglib.py')
    mtlx2mdl_script = os.path.join(script_path, 'run_mtlx2mdl.py')
    logger.info('Script Path:       %s' % script_path)
    logger.info('Data Path:         %s' % data_path)
    logger.info('MDL output path:   %s' % mdl_output_path)
    logger.info('Python Executable: %s' % python_executable)

    # Create the alglib
    createAlglib(alglib_defs_file, alglib_graph_file, alglib_script, data_path,
                 mtlx_search_path, python_executable)

    # Create shared mdl lib
    invoke_mtlx2mdl(mtlx2mdl_script,
                    mdl_shared_name,
                    python_executable,
                    generate_shared=True,
                    mdl_root=mdl_output_path)

    modules_to_build = [
        'stdlib',
        'alglib',
        'bxdf'
    ]

    # Create mdl modules from our materialx modules
    for module in modules_to_build:
        invoke_mtlx2mdl(mtlx2mdl_script,
                        module,
                        python_executable,
                        mdl_shared_name=mdl_shared_name,
                        mdl_root=mdl_output_path,
                        materialx_search_path=mtlx_search_path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s]%(message)s')
    main()
