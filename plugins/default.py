#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'default'


class Default(DagNode):
    def __init__(self, *args, **kwargs):
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        super(Default, self).__init__(*args, **kwargs)

        self.color     = [172, 172, 172, 255] 