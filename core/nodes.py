#!/usr/bin/env python
import os
import uuid
from copy import deepcopy
import simplejson as json

from .. import options
reload(options)


"""
Goals:
 - hold basic attributes
 - easily add new attributes
 - query connections easily
"""

class DagNode(dict):

    CLASS_KEY     = "dagnode"  
    NAME_KEY      = "name"
    UUID_KEY      = "UUID"
    COLOR_KEY     = "color"
    WIDTH_KEY     = "width"
    HEIGHT_KEY    = "height"
    EXPANDED_KEY  = "height"
    POS_KEY       = "pos"
    TYPE_KEY      = "node_type"
    OUTPUTS_KEY   = "outputs"
    INPUTS_KEY    = "inputs"

    def __init__(self, nodetype, **kwargs):        

        self.node_type          = nodetype
        self.name               = kwargs.pop('name', 'node1')
        self.color              = kwargs.pop('color', [180, 180, 180])
        self.expanded           = kwargs.pop('expanded', False)
        self.height_collapsed   = kwargs.pop('height_collapsed', 15)
        self.height_expanded    = kwargs.pop('height_expanded', 175)
        self.pos                = kwargs.pop('pos', (0,0))

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.UUID = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

        # connections
        self.inputs             = [Connection(self),]
        self.outputs            = [Connection(self, name='output', type='output'),]
        return

    def __str__(self):
        return json.dumps(self, indent=4)

    @property
    def node_class(self):
        return self.CLASS_KEY

    @property
    def name(self):
        return self[self.NAME_KEY]

    @name.setter
    def name(self, value):
        self[self.NAME_KEY] = value
        return

    @property
    def id(self):
        return self[self.UUID_KEY]

    @property
    def UUID(self):
        return self[self.UUID_KEY]

    @UUID.setter
    def UUID(self, value):
        self[self.UUID_KEY] = value

    @property
    def color(self):
        return self[self.COLOR_KEY]

    @color.setter
    def color(self, value):
        self[self.COLOR_KEY] = value
        return

    @property
    def width(self):
        return self[self.WIDTH_KEY]

    @width.setter
    def width(self, value):
        self[self.WIDTH_KEY] = value
        return

    @property
    def height(self):
        return self[self.HEIGHT_KEY]

    @height.setter
    def height(self, value):
        self[self.HEIGHT_KEY] = value
        return

    @property
    def expanded(self):
        return self[self.EXPANDED_KEY]

    @expanded.setter
    def expanded(self, value):
        self[self.EXPANDED_KEY] = value
        return

    @property
    def pos(self):
        return self[self.POS_KEY]

    @pos.setter
    def pos(self, value):
        self[self.POS_KEY] = value
        return

    @property
    def node_type(self):
        return self[self.TYPE_KEY]

    @node_type.setter
    def node_type(self, value):
        self[self.TYPE_KEY] = value
        return

    @property
    def inputs(self):
        return self[self.INPUTS_KEY]

    @inputs.setter
    def inputs(self, value):
        self[self.INPUTS_KEY] = value
        return

    @property
    def outputs(self):
        return self[self.OUTPUTS_KEY]

    @outputs.setter
    def outputs(self, value):
        self[self.OUTPUTS_KEY] = value
        return


class Connection(dict):
    """
    This needs to exlude the node reference (or stash the Node.UUID)
    """
    CLASS_KEY     = "connection"
    NAME_KEY      = "name"  
    NODE_KEY      = "node"
    TYPE_KEY      = "type"
    parent        = None  

    def __init__(self, node, **kwargs):     

        self.parent     = node
        self.node       = node.UUID
        self.name       = kwargs.pop('name', 'input')
        self.type       = kwargs.pop('type', 'input')

        self.update(**kwargs)
        return

    @property
    def node_class(self):
        return self.CLASS_KEY

    @property
    def name(self):
        return self[self.NAME_KEY]

    @name.setter
    def name(self, value):
        self[self.NAME_KEY] = value
        return

    @property
    def node(self):
        return self[self.NODE_KEY]

    @node.setter
    def node(self, value):
        self[self.NODE_KEY] = value
        return

    @property
    def type(self):
        return self[self.TYPE_KEY]

    @type.setter
    def type(self, value):
        self[self.TYPE_KEY] = value
        return

    @property
    def node_type(self):
        return self.CLASS_KEY



class DagEdge(dict):

    CLASS_KEY     = "edge"
    SRC_ID_KEY    = "src_id"
    DEST_ID_KEY   = "dest_id"
    SRC_ATTR_KEY  = "src_attr"
    DEST_ATTR_KEY = "dest_attr"
    UUID_KEY      = "UUID"
    TYPE_KEY      = "node_type"    

    def __init__(self, source, dest, **kwargs):        

        self.src_id    = source
        self.dest_id   = dest

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.UUID = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)
        return

    def __str__(self):
        return json.dumps(self, indent=4)

    @property
    def node_class(self):
        return self.CLASS_KEY

    @property
    def name(self):
        return '%s,%s' % (self.source, self.dest)

    @property
    def id(self):
        return self[self.UUID_KEY]

    @property
    def UUID(self):
        return str(self[self.UUID_KEY])

    @UUID.setter
    def UUID(self, value):
        self[self.UUID_KEY] = value

    @property
    def src_id(self):
        return self[self.SRC_ID_KEY]

    @src_id.setter
    def src_id(self, value):
        # get the default output
        if isinstance(value, DagNode):
            self[self.SRC_ID_KEY] = value.UUID
            self[self.SRC_ATTR_KEY] = value.outputs[0].name

        if isinstance(value, Connection):
            self[self.SRC_ID_KEY] = value.node
            self[self.SRC_ATTR_KEY] = value.name
        return

    @property
    def src_attr(self):
        return self[self.SRC_ATTR_KEY]

    @src_attr.setter
    def src_attr(self, value):
        self[self.SRC_ATTR_KEY] = value
        return

    @property
    def dest_id(self):
        return self[self.DEST_ID_KEY]

    @dest_id.setter
    def dest_id(self, value):
        # get the default input
        if isinstance(value, DagNode):
            self[self.DEST_ID_KEY] = value.UUID
            self[self.DEST_ATTR_KEY] = value.inputs[0].name
            return

        if isinstance(value, Connection):
            self[self.DEST_ID_KEY] = value.node
            self[self.DEST_ATTR_KEY] = value.name
        return

    @property
    def dest_attr(self):
        return self[self.DEST_ATTR_KEY]

    @dest_attr.setter
    def dest_attr(self, value):
        self[self.DEST_ATTR_KEY] = value
        return

    @property
    def node_type(self):
        return self.CLASS_KEY