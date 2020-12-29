#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from sdmatx import mtlx2mdl_library, mtlx2mdl_shared

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='materialX to mdl function definitions transpiler')
    parser.add_argument(
        '--module_name',
        type=str,
        help='Name of the module to generate with any hierarchical '
             'directories appended. '
             'Should not have any file extension')
    parser.add_argument(
        '--generate_shared',
        action='store_true',
        help='Generate the shared library')

    parser.add_argument(
        '--mdl_root',
        help='Root to where mdl files are written',
        type=str)

    parser.add_argument(
        '--mtlx_search_path',
        help='Path string to resolve materialX includes against',
        type=str)
    parser.add_argument(
        '--mdl_shared_name',
        help='Name of the mdl shared module',
        type=str)

    args = parser.parse_args()

    # Sanity check arguments
    if args.generate_shared:
        print(mtlx2mdl_shared().strip('\n'))
    else:
        print(mtlx2mdl_library(
            args.module_name,
            args.mdl_shared_name,
            args.mtlx_search_path).strip('\n')
        )
