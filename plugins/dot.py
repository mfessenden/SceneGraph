#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'dot'


class DotNode(DagNode):

    default_name  = 'dot'
    default_color = [172, 172, 172, 255]
    node_type     = 'dot'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

        self.width              = 10.0
        self.base_height        = 10.0        
        self.orientation        = 'dot'

