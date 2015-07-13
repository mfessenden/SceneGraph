#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'lookdev'


class Lookdev(DagNode):

    default_name = 'lookdev'

    def __init__(self, *args, **kwargs):
        
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

        self.color              = [241, 118, 110, 255]