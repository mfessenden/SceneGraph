#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class DefaultNode(DagNode):

    def __init__(self, **kwargs):
        nodetype = "default"
        super(DefaultNode, self).__init__(nodetype, **kwargs)