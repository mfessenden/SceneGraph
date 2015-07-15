#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'default'


class DefaultNode(DagNode):

    default_name  = 'default'
    default_color = [172, 172, 172, 255]
    node_type     = 'default'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)