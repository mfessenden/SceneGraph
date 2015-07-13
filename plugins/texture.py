#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'texture'


class Texture(DagNode):

    default_name  = 'texture'
    default_color = [111, 178, 68, 255]

    def __init__(self, *args, **kwargs):        
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

