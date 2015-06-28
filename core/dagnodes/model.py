#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class ModelNode(DagNode):

    def __init__(self, **kwargs):
        nodetype = "model"
        super(ModelNode, self).__init__(nodetype, **kwargs)