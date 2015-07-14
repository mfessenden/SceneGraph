#!/usr/bin/env python
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'asset'


class AssetWidget(NodeWidget): 
    def __init__(self, dagnode, parent=None):
        super(AssetWidget, self).__init__(dagnode, parent)