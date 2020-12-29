#Copyright 2020 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import MaterialX as mx


class AutoMaterialXException(BaseException):
    pass


UNIQUE = 0


def getUniqueName():
    global UNIQUE
    UNIQUE = UNIQUE + 1
    return UNIQUE


def correct_kw(kwargs):
    res = {}
    rename = {'in_': 'in'}
    for a, b in kwargs.items():
        renamed = rename[a] if a in rename else a
        res[renamed] = b
    return res


def makeNodeFun(nodeDef):
    """

    :param nodeDef:
    :type nodeDef: MaterialX.NodeDef
    :return:
    """

    def _invoke(graph=None, _nodeName=None, **kwargs):
        """

        :param graph:
        :type graph: mx.NodeGraph
        :param kwargs:
        :return:
        """
        kwargs = correct_kw(kwargs)
        if graph is None:
            raise AutoMaterialXException('No graph found')
        nodeName = nodeDef.getAttribute('node')
        node = graph.addNode(nodeName, _nodeName if _nodeName else nodeDef.getName() + '_' + str(getUniqueName()),
                             nodeDef.getType())
        for i in nodeDef.getInputs():
            if i.getName() in kwargs:
                ii = kwargs[i.getName()]
                if isinstance(ii, Op):
                    ii = ii.node
                if isinstance(ii, mx.Node):
                    node.setConnectedNode(i.getName(), ii)
                elif isinstance(ii, mx.Input):
                    i = node.addInput(i.getName())
                    i.setInterfaceName(ii.getName())
                    i.setType(ii.getType())
                elif isinstance(ii, mx.Parameter):
                    i = node.addInput(i.getName())
                    i.setInterfaceName(ii.getName())
                    i.setType(ii.getType())
                elif ii.__class__ in TYPE_MAP:
                    node.setInputValue(i.getName(), ii)
                else:
                    raise AutoMaterialXException('Unknown type for node')
        for i in nodeDef.getParameters():
            if i.getName() in kwargs:
                p = kwargs[i.getName()]
                if isinstance(p, mx.ValueElement):
                    pp = node.addParameter(i.getName(), i.getType())
                    pp.setInterfaceName(p.getName())
                else:
                    node.setParameterValue(i.getName(), p)
        if '_attrs' in kwargs:
            for attr_name, attr_data in kwargs['_attrs'].items():
                node.setAttribute(attr_name, attr_data)
        return node

    return _invoke


TYPE_MAP = {
    mx.Vector2: 'vector2',
    mx.Vector3: 'vector3',
    mx.Vector4: 'vector4',
    mx.Color2: 'color2',
    mx.Color3: 'color3',
    mx.Color4: 'color4',
    float: 'float',
    int: 'float',  # questionable but the best solution for now
    str: 'string',
    bool: 'boolean'
}


def createConstantNetwork(shader_ref, node_graph, input_name, type_, constant):
    op = node_graph.addOutput(input_name, type_)
    bi = shader_ref.addBindInput(input_name)
    const_node = node_graph.addNode('constant', input_name + 'const', type_)
    const_node.setInputValue('value', constant)
    op.setConnectedNode(const_node)
    bi.setConnectedOutput(op)


class Library:
    def __init__(self, databaseDoc):
        allDefs = {}
        nodeDefs = databaseDoc.getNodeDefs()
        for nd in nodeDefs:
            # print(nd.getName())
            f = makeNodeFun(nd)
            setattr(self, nd.getName(), f)
            allDefs[nd] = f
        # Now identify all methods with the same type
        methodBuckets = {}
        # types = set(['float', 'color2', 'color3', 'color4',
        #              'vector2', 'vector3', 'vector4'])
        for n, f in allDefs.items():
            nodeName = n.getAttribute('node')
            bucket = methodBuckets.get(nodeName)
            if not bucket:
                # Unknown method bucket, create it
                bucket = []
                methodBuckets[nodeName] = bucket
            bucket.append((n, f))
        for n, funcs in methodBuckets.items():
            f = self.makePolyFun(funcs)
            setattr(self, n, f)

    def makePolyFun(self, polyFuns):
        """

        :param polyFuns:
        :type dict[string, f()
        :return:
        """

        def _invoke(graph=None, _outputType=None, **kwargs):
            def _matchType(input_, value):
                if isinstance(input_, mx.Input) and isinstance(value, mx.Node):
                    return input_.getType() == value.getType()
                elif isinstance(input_, mx.Input) and isinstance(value, mx.Input):
                    return input_.getType() == value.getType()
                elif isinstance(input_, mx.Input) and isinstance(value, Op):
                    return input_.getType() == value.node.getType()
                elif isinstance(input_, mx.Input) and isinstance(value, mx.Parameter):
                    return input_.getType() == value.getType()
                elif isinstance(input_, mx.Parameter) and isinstance(value, mx.Parameter):
                    return input_.getType() == value.getType()
                elif isinstance(input_, mx.Parameter) or \
                        isinstance(input_, mx.Input):
                    if value.__class__ in TYPE_MAP:
                        return input_.getType() == TYPE_MAP[value.__class__]
                return False

            def _typeMatching(node):
                for i in node.getInputs():
                    if i.getName() in kwargs:
                        nodeInput = kwargs[i.getName()]
                        if not _matchType(i, nodeInput):
                            return False
                for i in node.getParameters():
                    if i.getName() in kwargs:
                        nodeInput = kwargs[i.getName()]
                        if not _matchType(i, nodeInput):
                            return False
                if _outputType:
                    if _outputType != node.getType() or not node.getName().endswith(_outputType):
                        return False
                return True

            # Type check
            kwargs = correct_kw(kwargs)
            imp = None
            for node, f in polyFuns:
                if _typeMatching(node):
                    if imp is not None:
                        raise AutoMaterialXException('Multiple matching functions')
                    imp = f

            if not imp:
                raise AutoMaterialXException('No suitable implementation found for the inputs provided')
            return Op(self, graph, imp(graph, **kwargs))

        return _invoke


def _promoteInput(input, node_graph, lib):
    if isinstance(input, Op):
        return input
    else:
        return lib.constant(node_graph, value=input)


def param_promoter(func):
    def call_promoted(*args, **kwargs):
        node_graph = kwargs.get('node_graph')
        lib = kwargs.get('lib')
        if node_graph is None or lib is None:
            for a in args:
                if isinstance(a, Op):
                    node_graph = a.node_graph
                    lib = a.lib
        if lib is None or node_graph is None:
            raise AutoMaterialXException('No node graph or lib available for promoting constant')
        args = [_promoteInput(a, node_graph, lib) for a in args]
        return func(*args, **kwargs)

    return call_promoted


class Op:
    def __init__(self, lib, node_graph, node):
        self.lib = lib
        self.node_graph = node_graph
        self.node = node

    @param_promoter
    def __add__(self, b):
        return self.lib.add(self.node_graph, in1=self.node, in2=b.node)

    @param_promoter
    def __sub__(self, b):
        return self.lib.subtract(self.node_graph, in1=self.node, in2=b.node)

    @param_promoter
    def __mul__(self, b):
        return self.lib.multiply(self.node_graph, in1=self.node, in2=b.node)

    @param_promoter
    def __truediv__(self, b):
        return self.lib.divide(self.node_graph, in1=self.node, in2=b.node)

    # @param_promoter
    # def __rdiv__(self, b):
    #     return self.lib.divide(self.node_graph, in1=self.node, in2=b.node)

    @param_promoter
    def __lt__(self, other):
        diff = self - other
        true = self.lib.constant(self.node_graph, value=1.0)
        false = self.lib.constant(self.node_graph, value=0.0)
        return self.lib.compare(self.node_graph,
                                in1=true,
                                in2=false,
                                intest=diff,
                                cutoff=0.0)

    @param_promoter
    def __gt__(self, other):
        diff = self - other
        true = self.lib.constant(self.node_graph, value=1.0)
        false = self.lib.constant(self.node_graph, value=0.0)
        return self.lib.compare(self.node_graph,
                                in1=false,
                                in2=true,
                                intest=diff,
                                cutoff=0.0)


@param_promoter
def min_(a, b):
    return a.lib.min(a.node_graph, in1=a.node, in2=b.node)


@param_promoter
def max_(a, b):
    return a.lib.max(a.node_graph, in1=a.node, in2=b.node)


@param_promoter
def pow_(a, b):
    return a.lib.power(a.node_graph, in1=a.node, in2=b.node)


@param_promoter
def dot(a, b):
    return a.lib.dotproduct(a.node_graph, in1=a.node, in2=b.node)


@param_promoter
def swizzle(a, target_type, channels):
    return a.lib.swizzle(a.node_graph, in_=a, channels=channels, _outputType=target_type)


def bind_output(output_name, operation, graph, shader_ref):
    op = graph.addOutput(output_name, operation.node.getType())
    op.setConnectedNode(operation.node)
    bi = shader_ref.addBindInput(output_name, type=operation.node.getType())
    bi.setConnectedOutput(op)


def createOutput(name, op, node_graph, node_def):
    output_node = node_graph.addOutput(name, op.node.getType())
    nd_output = node_def.getOutput(name)
    nd_output.setType(op.node.getType())
    output_node.setConnectedNode(op.node)


def createInput(name, type, node_graph, node_def, lib, uiName=None, uiFolder=None, default=None, min=None, max=None):
    input = node_def.addInput(name, type)
    if default is not None:
        input.setValue(default)
    if min is not None:
        input.setAttribute('uimin', str(min))
    if max is not None:
        input.setAttribute('uimax', str(max))
    if uiName is not None:
        input.setAttribute('uiname', uiName)
    if uiFolder is not None:
        input.setAttribute('uifolder', uiFolder)
    return Op(lib, node_graph, input)


def createParameter(name, type, node_graph, node_def, lib, uiName=None, uiFolder=None, default=None, min=None,
                    max=None):
    param = node_def.addParameter(name, type)
    if default is not None:
        param.setValue(default)
    if min is not None:
        param.setAttribute('uimin', str(min))
    if max is not None:
        param.setAttribute('uimax', str(max))
    if uiName is not None:
        param.setAttribute('uiname', uiName)
    if uiFolder is not None:
        param.setAttribute('uifolder', uiFolder)
    return Op(lib, node_graph, param)


@param_promoter
def blend(a, b, weight):
    return a + (b - a) * weight


@param_promoter
def clamp(a, min, max):
    return min_(max_(a, min), max)


@param_promoter
def levels(a, black, white, gamma):
    aa = (a - black) / (white - black)
    return clamp(pow_(aa, gamma), 0.0, 1.0)
