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
    
    Type  = QtGui.QGraphicsItem.UserType + 3

    def __init__(self, name='node1', node_type='default', font='Consolas', UUID=None,):
        
        self.name            = name
        self.node_type       = node_type
        self.uuid            = UUID if UUID else uuid.uuid4()
        
        self._private        = ['pos_x', 'pos_y']
        self._widget         = None   

        self._data           = dict()
        
        # buffers
        self.bufferX         = 3
        self.bufferY         = 3
        self.color           = [180, 180, 180]     

    def __str__(self):
        #return "name:%s  type:%s  uuid:%s" % (self.name, type(self).__name__, str(self.uuid))
        data = """%s %s {""" % (type(self).__name__, self.name)
        for k, v in self.data.iteritems():
            data += "\n   %s: %s," % (k, str(v))
        data += "\n}"
        return data

    def __lt__(self, other):
        return self.name < other.name

    def __hash__(self):
        return hash(self.uuid)

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
        for k, v in self._data.iteritems():
            if k not in self._private:
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

    @property
    def width(self):
        if self._widget:
            return self._widget.width
        return 0

    @property
    def height(self):
        if self._widget:
            return self._widget.height
        return 0

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
        for attr, val in kwargs.iteritems():
            if attr in ['width', 'height']:
                #if self._widget:
                setattr(self, attr, float(val))
                continue
            self._data[attr] = val

    def removeNodeAttributes(self, *args):
        """
        Remove arbitrary attributes to the node.
        """
        for arg in args:
            if arg in self._data:
                self._data.pop(arg)


#- CONNECTIONS -----


class ConnectionBase(object):
    def __init__(self, *args, **kwargs):

        self.name               = kwargs.pop('name', None)
        self._is_node           = False                         # this is a connection, not a scene graph node
        
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
    

#ConnectAttributeNode
class ConnectionNode(ConnectionBase, QtSvg.QGraphicsSvgItem):
    """
    Represents a node input connector
    """
    def __init__(self, *args, **kwargs):
        ConnectionBase.__init__(self, *args, **kwargs)
        
        self._parent            = args[0]
        self.nodeimage          = os.path.join(os.path.dirname(__file__), '../', 'icn', 'connection.svg')
        self.isInputConnection  = False
        self.isOutputConnection = False        
        
        args=list(args)
        args.insert(0, self.nodeimage)
        QtSvg.QGraphicsSvgItem.__init__(self, *args)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable )
        self.rectF = QtCore.QRectF(0,0,14,14)
        self.setAcceptsHoverEvents(True)
        
    def mousePressEvent(self, event):
        pass
        #print self.connectedLine

    def width(self):
        return self.sceneBoundingRect().width()

    def height(self):
        return self.sceneBoundingRect().height()
    
    def center(self):
        return self.sceneBoundingRect().center()


class NodeInput(ConnectionNode):
    def __init__(self, *args, **kwargs):
        super(NodeInput, self).__init__(*args, **kwargs)
        
        self.nodeimage = os.path.join(os.path.dirname(__file__), '../', 'icn', 'node_input.svg')
        self.isInputConnection = True
        
class NodeOutput(ConnectionNode):
    def __init__(self, *args, **kwargs):
        super(NodeOutput, self).__init__(*args, **kwargs)

        self.nodeimage = os.path.join(os.path.dirname(__file__), '../', 'icn', 'node_output.svg')
        self.isOutputConnection = True
        

# Line class for connecting the nodes together
class LineClass(QtGui.QGraphicsLineItem):

    def __init__(self, startItem, endItem, *args, **kwargs):
        super(LineClass, self).__init__(*args, **kwargs)

        # The arrow that's drawn in the center of the line
        self._is_node       = False
        self.arrowHead      = QtGui.QPolygonF()
        self.myColor        = QtCore.Qt.white
        self.myStartItem    = startItem
        self.myEndItem      = endItem
               
        self.sourcePoint    = QtCore.QPointF(self.myStartItem.center())
        self.destPoint      = QtCore.QPointF(self.myEndItem.center())
        self.centerPoint    = QtCore.QPointF()  # for bezier lines
        
        self.setZValue(-1.0)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setPen(QtGui.QPen(self.myColor, 2, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        
        self.name = "%s.%s" % (self.myStartItem, self.myEndItem)
        '''
        This if statement is making all of the connections consistent. The startItem will always be the
        beginning of the line. The arrow will always point to the end item, no matter which way the user
        connects the line.
        '''
        try:
            if self.myStartItem.isInputConnection:
                temp = self.myStartItem
                self.myStartItem = self.myEndItem
                self.myEndItem = temp
        except AttributeError, e:
            print "Error checking isInputConnection on node %s" %str(e)

    def __repr__(self):
        return '%s >> %s' % (self.myStartItem, self.myEndItem)
    
    def deleteNode(self):
        # For whatever the shit reason, I have to have this check. If I don't, I get an error in rare cases.
        if self:
            #self.getEndItem().getWidgetMenu().receiveFrom(self.getStartItem(), delete=True)
            #self.getStartItem().getWidgetMenu().sendData(self.getStartItem().getWidgetMenu().packageData())
            #self.getStartItem().removeReferences()
            self.scene().removeItem(self)
            self.myStartItem.connectedLine.remove(self)
            self.myEndItem.connectedLine.remove(self)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.deleteNode()
            self.update()
        else:
            super(LineClass, self).keyPressEvent(event)

    def getCenterPoint(self):
        line = self.getLine()
        centerX = (line.p1().x() + line.p2().x())/2
        centerY = (line.p1().y() + line.p2().y())/2
        return QtCore.QPointF(centerX, centerY)

    def getLine(self):
        p1 = self.myStartItem.sceneBoundingRect().center()
        p2 = self.myEndItem.sceneBoundingRect().center()
        return QtCore.QLineF(self.mapFromScene(p1), self.mapFromScene(p2))

    def getEndItem(self):
        return self.myEndItem.parentItem()

    def getStartItem(self):
        return self.myStartItem.parentItem()

    def updatePosition(self):
        self.setLine(self.getLine())
        self.myStartItem.connectedLine.append(self)
        self.myEndItem.connectedLine.append(self)

    def boundingRect(self):
        extra = (self.pen().width() + 100)  / 2.0
        line = self.getLine()
        p1 = line.p1()
        p2 = line.p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        path = super(LineClass, self).shape()
        path.addPolygon(self.arrowHead)
        return path

    def paint(self, painter, option, widget=None):
        arrowSize = 20.0
        line = self.getLine()
        painter.setBrush(self.myColor)
        myPen = self.pen()
        myPen.setColor(self.myColor)
        painter.setPen(myPen)

        if self.isSelected():
            painter.setBrush(QtCore.Qt.yellow)
            myPen.setColor(QtCore.Qt.yellow)
            myPen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(myPen)

        ####################################
        # This is Calculating the angle between the x-axis and the line of the arrow.
        # Then turning the arrow head to this angle so that it follows the direction of the arrow
        # If the angle is negative, turn the direction of the arrow
        ####################################

        if line.length() > 0.0:

            try:
                angle = math.acos(line.dx() / line.length())
            except ZeroDivisionError:
                angle = 0

            if line.dy() >= 0:
                angle = (math.pi * 2.0) - angle

            # Making sure that no matter which connectionCircle (output or input) is selected first, the arrow always points at the next input connection
            if self.myStartItem.isInputConnection:
                revArrow = 1
            else:
                revArrow = -1

            # Get the center point of the line
            centerPoint = self.getCenterPoint()

            # The head of the arrows tip is the centerPoint, so now calculate the other 2 arrow points
            arrowP1 = centerPoint + QtCore.QPointF(math.sin(angle + math.pi / 3.0) * arrowSize * revArrow,
                                        math.cos(angle + math.pi / 3) * arrowSize * revArrow)
            arrowP2 = centerPoint + QtCore.QPointF(math.sin(angle + math.pi - math.pi / 3.0) * arrowSize * revArrow,
                                        math.cos(angle + math.pi - math.pi / 3.0) * arrowSize * revArrow)

            # Clear anything in the arrowHead polygon
            self.arrowHead.clear()

            # Set the points of the arrowHead polygon
            for point in [centerPoint, arrowP1, arrowP2]:
                self.arrowHead.append(point)

            if line:
                painter.drawPolygon(self.arrowHead)
                painter.drawLine(line)
                #painter.drawCubicBezier(line)



#- Testing -----


class MyLine(QtGui.QGraphicsLineItem):
    def __init__(self, start_item, end_item, *args, **kwargs):
        super(MyLine, self).__init__(*args, **kwargs)
        
        self._start_item   = start_item
        self._end_item     = end_item


class MyPath(QtGui.QGraphicsPathItem):
    pass
