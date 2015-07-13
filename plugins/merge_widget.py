#!/usr/bin/env python
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'merge'


class MergeWidget(NodeWidget): 
    def __init__(self, dagnode, parent=None):
        super(MergeWidget, self).__init__(dagnode, parent)

        print 'connections: ', self.connections