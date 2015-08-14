#!/usr/bin/env python
from SceneGraph.ui.node_widgets import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'asset'


class AssetWidget(NodeWidget):
    node_class     = 'container'
    def __init__(self, dagnode, parent=None):
        super(AssetWidget, self).__init__(dagnode, parent)