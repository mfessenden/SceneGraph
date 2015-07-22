#!/usr/bin/env python
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'model'


class ModelWidget(NodeWidget):
    node_class = 'container'
    def __init__(self, dagnode, parent=None):
        super(ModelWidget, self).__init__(dagnode, parent)
        