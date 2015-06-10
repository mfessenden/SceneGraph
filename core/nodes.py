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
    PRIVATE = ['name', 'node_type', 'UUID', 'color']

    def __init__(self, node_type='default', **kwargs):
        
        self.name            = kwargs.pop('name', 'node1')
        self.node_type       = kwargs.pop('node_type', 'default')
        UUID                 = kwargs.pop('id', None)
        self.UUID            = UUID if UUID else uuid.uuid4()
        
        # edges attribute
        self._edge_list      = dict()

        # node widget
        self._widget         = None   

        # data attribute for arbitrary attributes
        self._data           = dict()        
        self.color           = [180, 180, 180]

        # add any arbitrary attributes
        self.addNodeAttributes(**kwargs)

    def __str__(self):
        data = """%s %s {""" % (type(self).__name__, self.name)
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
        data = dict()
        data['pos_x'] = self.pos_x
        data['pos_y'] = self.pos_y
        data['width'] = self.width
        data['height'] = self.height
        data['color'] = self.color
        for k, v in self._data.iteritems():
            if k not in self.PRIVATE:
                data[k] = v
        return data
    
    @property
    def pos_x(self):
        if self._widget:
            return self._widget.pos().x()
        return 0

    @property
    def pos_y(self):
        if self._widget:
            return self._widget.pos().y()
        return 0

    @pos_x.setter
    def pos_x(self, val):
        if self._widget:
            self._widget.setX(val)

    @pos_y.setter
    def pos_y(self, val):
        if self._widget:
            self._widget.setY(val)

    @property
    def width(self):
        if self._widget:
            return self._widget.width
        return 125

    @property
    def height(self):
        if self._widget:
            return self._widget.height
        return 15

    @width.setter
    def width(self, val):
        if self._widget:
            self._widget.width = val
            return True
        return False

    @property
    def height(self):
        if self._widget:
            return self._widget.height
        return 0

    @height.setter
    def height(self, val):
        if self._widget:
            self._widget.height = val
            return True
        return False

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
            # haxx here
            if attr not in self.PRIVATE:
                if not self._widget or attr not in self._widget.PRIVATE:
                    self._data[attr] = val
                    continue
                else:
                    if self._widget:
                        if attr in self._widget.PRIVATE:
                            if util.is_number(val):
                                val = float(val)
                            setattr(self._widget, attr, val)
            else:
                setattr(self, attr, val)

    def removeNodeAttributes(self, *args):
        """
        Remove arbitrary attributes to the node.
        """
        for arg in args:
            if arg in self._data:
                self._data.pop(arg)


#- Edges -----
class EdgeBase(object):
    
    Type    = QtGui.QGraphicsItem.UserType + 2
    PRIVATE = []

    def __init__(self, **kwargs):        
        
        src     = kwargs.get('src', None)
        dest    = kwargs.get('dest', None)

        if src is not None:
            self.src_node, self.src_attr = self.getNodeConnection(src)

        if dest is not None:
            self.dest_node, self.dest_attr = self.getNodeConnection(dest)

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




