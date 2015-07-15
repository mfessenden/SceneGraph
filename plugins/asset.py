#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'asset'


class AssetNode(DagNode):

    default_name  = 'asset'
    default_color = [174, 188, 43, 255]
    node_type     = 'asset'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)
