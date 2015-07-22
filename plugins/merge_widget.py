#!/usr/bin/env python
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'merge'


class MergeWidget(NodeWidget):
    node_class = 'container'
    def __init__(self, dagnode, parent=None):
        super(MergeWidget, self).__init__(dagnode, parent)

