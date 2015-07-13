#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'dot'


class Dot(DagNode):

    default_name = 'dot'

    def __init__(self, *args, **kwargs):
        
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

        self.width              = 10.0
        self.base_height        = 10.0
        self.height_expanded    = 10.0

        self.color              = [172, 172, 172, 255]
        self.orientation        = 'dot'

    @property
    def height(self):
        return 10.0

    @property
    def width(self):
        return 10.0