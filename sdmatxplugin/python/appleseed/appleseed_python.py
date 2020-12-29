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
import xml.etree.ElementTree as ET
from xml.dom import minidom

import MaterialX as mx


def to_appleseed_value(value):
    if isinstance(value, str):
        return 'string %s' % value
    elif isinstance(value, mx.Color3):
        return 'color %f %f %f' % (value[0], value[1], value[2])
    elif isinstance(value, float):
        return 'float %f' % (value)


# Borrowed from here:
# http://effbot.org/zone/element-lib.htm#prettyprint
def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def render(target_file,
           resolution,
           appleseed_path,
           template_file,
           shader_params={}):
    try:

        with open(template_file, 'rt') as f:

            project_file = ET.parse(f)
            root = project_file.getroot()
            # Update resolution
            parameters = root.findall('output/frame/parameter[@name=\'resolution\']')
            for p in parameters:
                p.set('value', '%d %d' % resolution)

            # bind shader parameters
            shaders = root.findall('.//shader[@type=\'shader\']')
            for shader in shaders:
                if shader_params:
                    for p, val in shader_params.items():
                        param = ET.SubElement(shader, 'parameter')
                        param.set('name', p)
                        param.set('value', to_appleseed_value(val))
                        param.tail = '\n'
            new_project_file = os.path.splitext(target_file)[0] + ".appleseed"

            indent(root)
            # pretty_printed = toPrettyString(project_file)
            # print(pretty_printed)
            with open(new_project_file, "w") as file:
                project_file.write(new_project_file, encoding='utf-8', xml_declaration=True)

        # Invoke appleseed to render the project file.
        appleseed_cli_path = os.path.join(appleseed_path, "bin",
                                          "appleseed.cli.exe" if os.name == "nt" else "appleseed.cli")

        cmd = [appleseed_cli_path, "--message-verbosity", "error", new_project_file, "--output", target_file]
        print(subprocess.list2cmdline(cmd))
        subprocess.check_call(cmd)
        subprocess.check_call(['cmd', '/c', 'start', target_file])
    except subprocess.CalledProcessError as e:
        print("Failed to generate {0} with appleseed: {1}".format(target_file, e))
        raise
