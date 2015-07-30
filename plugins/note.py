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
        self.font_size      = 6
        self.show_name      = kwargs.get('show_name', False)
        self.doc_text       = kwargs.get('doc_text', "Sample note text.")        

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in self.REQUIRED:
            if hasattr(self, attr):
                data[attr] = getattr(self, attr)
        data.update(doc_text=self.doc_text, corner_loc=self.corner_loc, font_size=self.font_size, show_name=self.show_name)
        return data