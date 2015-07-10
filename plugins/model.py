#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'model'


class Model(DagNode):
    def __init__(self, *args, **kwargs):
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        super(Model, self).__init__(*args, **kwargs)

        self.color     = [176, 186, 39, 255]