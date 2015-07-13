#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'model'


class Model(DagNode):

    default_name  = 'model'
    default_color = [139, 210, 244, 255]
    
    def __init__(self, *args, **kwargs):        
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

