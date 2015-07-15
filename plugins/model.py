#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'model'


class ModelNode(DagNode):

    default_name  = 'model'
    default_color = [139, 210, 244, 255]
    node_type     = 'model'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

