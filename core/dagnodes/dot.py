#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class DotNode(DagNode):

    def __init__(self, **kwargs):
        nodetype = "dot"
        super(DotNode, self).__init__(nodetype, **kwargs)