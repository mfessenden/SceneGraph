#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'merge'


class Merge(DagNode):

    default_name = 'merge'

    def __init__(self, *args, **kwargs):

        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

        self._command           = 'touch %s'
        self.color              = [185, 172, 151, 255]

        self.remove_connection('input')
        # add two inputs
        for i in ['inputA', 'inputB']:
            self.add_input(name=i)

    def execute(self):
        """
        Evaluate the _command attribute.

        returns:
            (tuple) - merge results.
        """
        print '# %s merging...' % self.name
        return (self.inputA, self.inputB)