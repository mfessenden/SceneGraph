#!/usr/bin/env python
from SceneGraph.ui.node_widgets import NodeWidget


class AssetWidget(NodeWidget):
    widget_type  = 'asset'
    node_class   = 'container'
    def __init__(self, dagnode, parent=None):
        NodeWidget.__init__(self, dagnode, parent)