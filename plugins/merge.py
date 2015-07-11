#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'merge'


class Merge(DagNode):
    def __init__(self, *args, **kwargs):
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

        self.inputA    = kwargs.pop('inputA', "")
        self.inputB    = kwargs.pop('inputB', "")
        
        self.color     = [21, 140, 167, 255]