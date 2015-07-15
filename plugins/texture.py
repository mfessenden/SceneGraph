#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'texture'


class TextureNode(DagNode):

    default_name  = 'texture'
    default_color = [111, 178, 68, 255]
    node_type     = 'texture'

    def __init__(self, name=None, **kwargs):
        super(TextureNode, self).__init__(name, **kwargs)

