#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class MergeNode(DagNode):

    def __init__(self, **kwargs):
        nodetype = "merge"
        super(MergeNode, self).__init__(nodetype, **kwargs)