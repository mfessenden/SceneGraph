#!/usr/bin/env python
from SceneGraph.core.nodes import DagNode


class MergeNode(DagNode):
    
    node_type     = 'merge'
    node_class    = 'evaluate'
    node_category = 'builtin'
    default_name  = 'merge'
    default_color = [255, 136, 136, 255]

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

    def execute(self):
        """
        Evaluate the _command attribute.

        :returns:  merge results.
        :rtype: tuple
        """
        return (self.inputA, self.inputB)