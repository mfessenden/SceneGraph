#!/usr/bin/env python
from SceneGraph import options
from SceneGraph.core.nodes import DagNode


SCENEGRAPH_NODE_TYPE = 'dot'


class DotNode(DagNode):

    default_name  = 'dot'
    default_color = [172, 172, 172, 255]
    node_type     = 'dot'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

        self.radius             = 10.0
        self.orientation        = 'dot'
        self.force_expand       = False

        self.add_attr('input', connectable=True, connection_type='input')

    @property
    def base_height(self):
        return self.radius
    
    @base_height.setter
    def base_height(self, value):
        """
        Set the base width value.

        params:
            value (float) - radius.
        """
        self.radius=value

    @property
    def width(self):
        return self.radius
    
    @width.setter
    def width(self, value):
        """
        Set the base width value.

        params:
            value (float) - radius.
        """
        self.radius=value

    @property
    def height(self):
        return self.radius
    
    @height.setter
    def height(self, value):
        """
        Set the radius value.

        params:
            value (float) - radius.
        """
        self.radius=value