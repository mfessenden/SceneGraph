#!/usr/bin/env python
from SceneGraph.core.nodes import NodeBase


class DotNode(NodeBase):

    def __init__(self, **kwargs):
        nodetype = "dot"
        super(DotNode, self).__init__(nodetype, **kwargs)