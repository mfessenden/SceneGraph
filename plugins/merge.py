#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'merge'


class MergeNode(DagNode):

    default_name  = 'merge'
    default_color = [255, 85, 0, 255]
    node_type     = 'merge'
    
    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

    def execute(self):
        """
        Evaluate the _command attribute.

        returns:
            (tuple) - merge results.
        """
        print '# %s merging...' % self.name
        return (self.inputA, self.inputB)