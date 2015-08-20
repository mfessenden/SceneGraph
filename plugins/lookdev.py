#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class LookdevNode(DagNode):

    node_type     = 'lookdev'
    node_class    = 'container'
    node_category = 'builtin'
    default_name  = 'lookdev'
    default_color = [170, 170, 255, 255]

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)
        
