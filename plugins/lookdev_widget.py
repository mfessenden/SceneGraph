#!/usr/bin/env python
from SceneGraph.ui.node_widgets import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'lookdev'


class LookdevWidget(NodeWidget):
    node_class = 'container'
    def __init__(self, dagnode, parent=None):
        super(LookdevWidget, self).__init__(dagnode, parent)