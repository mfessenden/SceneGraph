#!/usr/bin/env python
from SceneGraph.core.nodes import NodeBase


class MergeNode(NodeBase):

    def __init__(self, **kwargs):
        nodetype = "merge"
        super(MergeNode, self).__init__(nodetype, **kwargs)