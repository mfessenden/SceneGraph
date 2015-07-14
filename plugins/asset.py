#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'asset'


class Asset(DagNode):

    default_name  = 'asset'
    default_color = [174, 188, 43, 255]
    
    def __init__(self, *args, **kwargs):        
        kwargs.update(node_type=SCENEGRAPH_NODE_TYPE)
        DagNode.__init__(self, *args, **kwargs)

        self.remove_connection('input')
        
        # add two inputs
        for i in ['model', 'lookdev', 'rig', 'texture']:
            self.add_input(name=i)