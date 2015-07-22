#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'lookdev'


class LookdevNode(DagNode):

    default_name  = 'lookdev'
    default_color = [170, 170, 255, 255]
    node_type     = 'lookdev'
    
    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)
        
