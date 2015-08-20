#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class TextureNode(DagNode):

    node_type     = 'texture'
    node_class    = 'container'
    node_category = 'builtin'
    default_name  = 'texture'
    default_color = [111, 178, 68, 255]
    
    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

