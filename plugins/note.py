#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'note'


class NoteNode(DagNode):

    default_name  = 'note'
    default_color = [255, 239, 62, 255]
    node_type     = 'note'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

        self.corner_loc     = 'top'   
        self.base_height    = 75
        self.corner_size    = 15
        self.doc_text       = kwargs.get('doc_text', "Sample note text.")