#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'texture'


class TextureNode(DagNode):

    node_type     = 'texture'
    node_class    = 'container'
    node_category = 'builtin'
    default_name  = 'texture'
    default_color = [111, 178, 68, 255]
    
    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

