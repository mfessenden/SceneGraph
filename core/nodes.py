#!/usr/bin/env python
import os
import math
import uuid
from PySide import QtGui, QtCore, QtSvg
import simplejson as json
from collections import OrderedDict as dict

from .. import options
reload(options)


class NodeBase(object):
    
    Type    = QtGui.QGraphicsItem.UserType + 3
    PRIVATE = ['UUID', 'node_type', 'height_collapsed', 'height_expanded', 'expanded']

    def __init__(self, node_type, **kwargs):
        # data attribute for arbitrary attributes
        self._data              = dict() 

        self.name               = kwargs.pop('name', 'node1')
        self.node_type          = node_type
        self.color              = kwargs.pop('color', [180, 180, 180])
        self.expanded           = kwargs.pop('expanded', False)
        self.height_collapsed   = kwargs.pop('height_collapsed', 15)
        self.height_expanded    = kwargs.pop('height_expanded', 175)
        UUID                    = kwargs.pop('id', None)

        self.UUID               = UUID if UUID else uuid.uuid4()
        
        # edges attribute
        self._edge_list         = dict()

        # node widget
        self._widget            = None   
        self.enabled            = kwargs.pop('enabled', True)   

        # add any arbitrary attributes
        self.addNodeAttributes(**kwargs)

    def __str__(self):
        data = '''%s "%s" {''' % (type(self).__name__, self.name)
        for k, v in self.data.iteritems():
            data += "\n   %s: %s," % (k, str(v))
        data += "\n}"
        return data

    def __lt__(self, other):
        return self.name < other.name

    def __hash__(self):
        return hash(self.UUID)

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return NodeBase.Type

    @property
    def data(self):
        data = self._data
        data.update(name=self.name,
                    node_type=self.node_type,
                    width=self.width, 
                    height=self.height,
                    expanded=self.expanded,
                    enabled=self.enabled,
                    )
        return data

    @property
    def name(self):
        return self._data.get('name', 'node1')

    @name.setter
    def name(self, val):
        self._data.update(name=val)
        return self.name

    @property
    def node_type(self):
        return self._data.get('node_type', 'default')

    @node_type.setter
    def node_type(self, val):
        self._data.update(node_type=val)
        return self.node_type

    @property
    def expanded(self):
        return self._data.get('expanded', False)

    @expanded.setter
    def expanded(self, val):
        self._data.update(expanded=val)
        return self.expanded

    @property
    def pos_x(self):
        return self._data.get('pos_x', 0)

    @pos_x.setter
    def pos_x(self, val):
        self._data.update(pos_x=val)
        return self.pos_x

    @property
    def pos_y(self):
        return self._data.get('pos_y', 0)

    @pos_y.setter
    def pos_y(self, val):
        self._data.update(pos_y=val)
        return self.pos_y

    @property
    def width(self):
        return self._data.get('width', 120)

    @width.setter
    def width(self, val):
        self._data.update(width=val)
        return self.width

    @property
    def height(self):
        if not self.expanded:
            return self.height_collapsed
        return self.height_expanded

    @height.setter
    def height(self, val):
        if not self.expanded:
            self._data.update(height_collapsed=val)
        else:
            self._data.update(height_expanded=val)
        return self.height

    @property
    def height_collapsed(self):
        return self._data.get('height_collapsed', 15)

    @height_collapsed.setter
    def height_collapsed(self, val):
        return self._data.update(height_collapsed=val)

    @property
    def height_expanded(self):
        return self._data.get('height_expanded', 175)

    @height_expanded.setter
    def height_expanded(self, val):
        return self._data.update(height_expanded=val)

    @height.setter
    def height(self, val):
        if not self.expanded:
            self._data.update(height_collapsed=val)
        else:
            self._data.update(height_expanded=val)
        return self.height

    @property
    def color(self):
        return self._data.get('color', [180, 180, 180])

    @color.setter
    def color(self, val):
        self._data.update(color=val)
        return self.color

    @height.setter
    def height(self, val):
        self._data.update(height=val)
        return self.width

    def path(self):
        return '/%s' % self.name

    def getNodeAttributes(self, **kwargs):
        """
        Add arbitrary attributes to the node.
        """
        return self.data

    def addNodeAttributes(self, **kwargs):
        """
        Add arbitrary attributes to the node.
        """
        from SceneGraph import util
        reload(util)
        for attr, val in kwargs.iteritems():
            #print '# "%s.%s": %s' % (self.name, attr, str(val))
            self._data[attr] = val
            if attr in ['pos_x', 'pos_y']:
                if self._widget is not None:

                    if attr == 'pos_x':
                        self._widget.setX(float(val))
                    if attr == 'pos_y':
                        self._widget.setY(float(val))

    def removeNodeAttributes(self, *args):
        """
        Remove arbitrary attributes to the node.
        """
        for arg in args:
            if arg in self._data:
                self._data.pop(arg)


#- Edges -----
class EdgeBase(object):
    """
    Represents an edge in a graph.

    To use it, instantiate the class with two strings:

        src  = "node1.output"
        dest = "node2.input"
    """
    Type    = QtGui.QGraphicsItem.UserType + 2
    PRIVATE = []

    def __init__(self, src, dest, **kwargs):

        UUID            = kwargs.pop('id', None)
        self.UUID       = UUID if UUID else uuid.uuid4()
        self.ids        = ()

        if src is not None:
            self.src_name, self.src_attr = self.getNodeConnection(src)

        if dest is not None:
            self.dest_name, self.dest_attr = self.getNodeConnection(dest)

    @property
    def source_node(self):
        return '%s.%s'  % (self.src_name, self.src_attr)

    @property
    def dest_node(self):
        return '%s.%s'  % (self.dest_name, self.dest_attr)

    @property
    def name(self):
        return '%s,%s' % (self.source_node, self.dest_node)

    def getNodeConnection(self, node, src=True):
        """
        Given a connection string (ie: "MyNode.graph"), 
        return a tuple of (node name, connection attribute)
        """
        attrs = node.partition('.')
        node_name = attrs[0]
        node_attr = 'input'
        if src:
            node_attr='output'
        if attrs[-1]:
            node_attr = attrs[-1]
        return (node_name, node_attr)


#- Connections -----

class ConnectionBase(object):
    def __init__(self, *args, **kwargs):

        self.name               = kwargs.pop('name', None)
        self.node_type          = 'connection'
        
        self._parent            = None
        self.nodeimage          = None
        self.isInputConnection  = False
        self.isOutputConnection = False
        self.connectedLine      = []
        
        # json output functions
    
    def __repr__(self):
        return '%s.%s' % (self._parent.name, self.name)

    def path(self):
        return '%s.%s' % (self._parent.path(), self.name)




