#!/usr/bin/env python
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'dot'


class DotWidget(NodeWidget): 
    def __init__(self, dagnode, parent=None):
        super(DotWidget, self).__init__(dagnode, parent)
        