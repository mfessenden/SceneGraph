#!/usr/bin/env python
from SceneGraph.core.nodes import NodeBase


class DefaultNode(NodeBase):

    def __init__(self, **kwargs):
        nodetype = "default"
        super(DefaultNode, self).__init__(nodetype, **kwargs)