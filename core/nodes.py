#!/usr/bin/env python
from PySide import QtGui, QtCore, QtSvg
import simplejson as json
import os
import math

from .. import options
reload(options)


class NodeBase(object):
    """
    Base node type
    """
    def __init__(self, *args, **kwargs):
        
        self.nodetype      = None                           # designates the node type
        self._is_node      = True
        self._is_root      = False                          # designates a root node 
        self._node_name    = None
        self.nodeimage     = None
        self.description   = None
        self.nodetype      = None
        self.nodecolor     = None
        self._connections  = dict(input = {}, output={})

    def __repr__(self):
        return '%s' % self.node_name

    def path(self):
        """
        Returns a path relative to the base (parenting not yet implemented)
        """
        return '/%s' % str(self._node_name)
       

class RootNode(NodeBase, QtSvg.QGraphicsSvgItem):

    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeCreatedInScene  = QtCore.Signal()
    nodeChanged         = QtCore.Signal(bool)
    
    def __init__(self, *args, **kwargs):
        NodeBase.__init__(self)
        
        self._attr_ui      = None                       # link to UI?
        self.nodetype      = 'generic'
        self._is_root      = True
        self._node_name    = 'root'
        self.nodeimage     = os.path.join(options.SCENEGRAPH_ICON_PATH, 'node_root_100x180.svg')
        self.description   = 'node with no specific attributes'
        self.nodecolor     = None
        self.inputs        = []
        self.outputs       = ['graph']
        
        self._attributes   = dict()                 # arbitrary attributes
        self._private      = ['width', 'height']
        
        # text attributes
        self._name_text    = None                   # QGraphicsTextItem 
        
        args=list(args)
        args.insert(0, self.nodeimage)
        QtSvg.QGraphicsSvgItem.__init__(self, *args, **kwargs)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setCachingEnabled(True)
        self.setAcceptHoverEvents(True)
        
        self.rectF = QtCore.QRectF(0,0,250,180)        
        
        # setup UI
        self.addInputAttributes(*self.inputs)
        self.addOutputAttributes(*self.outputs)
        self.set_name()

    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setElementId("hover")
        else:
            self.setElementId("regular")
        super(RootNode, self).paint(painter, option, widget)

    def mousePressEvent(self, event):
        """
        Runs when node is selected
        """
        #print '# "%s" x: %s, y: %s' % (self._node_name, str(self.sceneBoundingRect().left()), str(self.sceneBoundingRect().top()))
        event.accept()
      
    def update(self):
        self.set_name()
        self.set_tooltip()
        super(RootNode, self).update()

    #- ATTRIBUTES -----
    def set_name(self):
        """
        Set the node title
        
        todo: should be in NodeBase
        """
        if not self._name_text:
            font = QtGui.QFont("SansSerif", 14)
            #font.setStyleHint(QtGui.QFont.Helvetica)
            font.setStretch(100)
            self._name_text = QtGui.QGraphicsTextItem(self._node_name, self)
            self._name_text.setFont(font)
            self._name_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
            self._name_text.setPos(self.sceneBoundingRect().left(), self.sceneBoundingRect().top())
            #self._name_text.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        else:
            self._name_text.setPlainText(self._node_name)
    
    def set_tooltip(self):
        """
        Set the tooltip text in the graph
        """
        self.setToolTip(self.path())
    
    @QtCore.Slot()
    def addNodeAttributes(self, **kwargs):
        """
        Add random attributes to the node
        
        todo: should be in NodeBase
        """
        self._attributes.update(**kwargs)
        self.nodeChanged.emit(True)
    
    @QtCore.Slot()
    def addAttr(self, val):
        self._attributes[val]=''
        self.nodeChanged.emit(True)

    def getAttr(self, attribute):
        """
        Query a specific node's attribute
        """
        return self.getNodeAttributes().get(attribute, None)

    def getNodeAttributes(self):
        """
        Returns a dictionary of node attributes
        """
        return self._attributes

    def setNodeAttributes(self, **kwargs):
        """
        Set arbitrary attributes
        """
        self._attributes.update(**kwargs)    

    def addInputAttributes(self, *attrs):
        """
        Add input attributes to the node
        
        todo: should be in NodeBase
        """
        start_y = self.sceneBoundingRect().top() + 36
        font = QtGui.QFont("SansSerif", 10)
        font.setStretch(100)
        for attr in attrs:
            if attr not in self.getInputAttributes():   
                #print '# adding attr "%s" at y: %d' % (attr, start_y)
                attr_text = QtGui.QGraphicsTextItem(attr, self)
                attr_text.setFont(font)
                attr_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
                attr_text.setPos(self.sceneBoundingRect().left()+5, start_y)
                connection = NodeInput(self, name=attr)
                #input_node.setPos(-input_node.width()/2, input_node.height()/2 + 9)
                connection.setPos(self.sceneBoundingRect().left()-7, start_y+5)
                self._connections.get('input').update(**{attr:connection})
                start_y+=30       

    def addOutputAttributes(self, *attrs):
        """
        Add input attributes to the node
        
        todo: should be in NodeBase
        """
        start_y = self.sceneBoundingRect().top() + 36
        font = QtGui.QFont("SansSerif", 10)
        font.setStretch(100)
        for attr in attrs:
            if attr not in self.getInputAttributes():   
                #print '# adding attr "%s" at y: %d' % (attr, start_y)
                attr_text = QtGui.QGraphicsTextItem(attr, self)
                
                attr_text.setFont(font)
                attr_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
                attr_text.setPos(self.sceneBoundingRect().center().x()+15, start_y)
                connection = NodeOutput(self, name=attr)
                #input_node.setPos(-input_node.width()/2, input_node.height()/2 + 9)
                connection.setPos(self.sceneBoundingRect().right()-7, start_y+5)
                self._connections.get('output').update(**{attr:connection})
                start_y+=30       

    def getInputAttributes(self):
        return self._connections.get('input', {}).keys()     

    def getOutputAttributes(self):
        return self._connections.get('output', {}).keys()
    
    def getInputConnection(self, conn_name):
        """
        Returns the input connection NODE for the given name
        """
        return self._connections.get('input').get(conn_name, None)

    def getOutputConnection(self, conn_name):
        """
        Returns the output connection NODE for the given name
        """
        return self._connections.get('output').get(conn_name, None)
    
    def getConnectedLines(self):
        result = []
        for typ, values in self._connections.iteritems():
            if values:
                for node_name, node in values.iteritems():                
                    if node.connectedLine:
                        for line in node.connectedLine:
                            if line not in result:
                                result.append(line)
        return result
    
    @property
    def node_name(self):
        return self._node_name
    
    @node_name.setter
    def node_name(self, val):
        self._node_name = val
        self.set_name()
    
    @property
    def width(self):
        return self.sceneBoundingRect().width()

    @property
    def height(self):
        return self.sceneBoundingRect().height()

    def deleteNode(self):
        # added only for compatibility, cannot delete this node
        pass
    
    @property
    def data(self):
        data = dict()
        data.update(x=self.sceneBoundingRect().x())
        data.update(y=self.sceneBoundingRect().y())
        data.update(width=self.width)
        data.update(height=self.height)
        data.update(**self.dumpArbitraryAttributes())
        return data
    
    def dumpArbitraryAttributes(self):
        result = dict()
        for attr in sorted(self._attributes.keys()):
            value = self._attributes.get(attr)
            result['__%s' % attr] = value
        return result
    
    def dump(self):
        output_data = {self.node_name:self.data}
        print json.dumps(output_data, indent=5)


class GenericNode(NodeBase, QtSvg.QGraphicsSvgItem):

    clickedSignal = QtCore.Signal(QtCore.QObject)
    nodeCreatedInScene = QtCore.Signal()
    nodeChanged = QtCore.Signal(bool)
    
    def __init__(self, *args, **kwargs):
        NodeBase.__init__(self)
        
        self._attr_ui      = None                       # link to UI?
        self.nodetype      = 'generic'
        self._node_name    = kwargs.pop('name', 'node')
        self.nodeimage     = os.path.join(options.SCENEGRAPH_ICON_PATH, 'node_base_250x180.svg')
        self.description   = 'node with no specific attributes'
        self.nodecolor     = None
        
        # inputs/outputs
        self.inputs        = ['input1', 'input2', 'input3']
        self.outputs       = ['output1', 'output2', 'output3'] 
        
        self._attributes   = dict()                 # arbitrary attributes
        self._private      = ['width', 'height']
        
        # text attributes
        self._name_text    = None                   # QGraphicsTextItem 
        
        args=list(args)
        args.insert(0, self.nodeimage)
        QtSvg.QGraphicsSvgItem.__init__(self, *args, **kwargs)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setCachingEnabled(True)
        self.setAcceptHoverEvents(True)
        
        self.rectF = QtCore.QRectF(0,0,100,180)        
        
        # setup UI        
        self.addInputAttributes(*self.inputs)
        self.addOutputAttributes(*self.outputs)
        self.update()     
    
    def paint(self, painter, option, widget):
        if self.isSelected():
            self.setElementId("hover")
        else:
            self.setElementId("regular")
        super(GenericNode, self).paint(painter, option, widget)
    
    def mousePressEvent(self, event):
        """
        Runs when node is selected
        """
        #print '# "%s" x: %s, y: %s' % (self._node_name, str(self.sceneBoundingRect().left()), str(self.sceneBoundingRect().top()))
        event.accept()
   
    '''
    def mouseMoveEvent(self, event):
        """
        Runs when node is selected
        """
        print '# "%s" x: %s, y: %s' % (self._node_name, str(self.sceneBoundingRect().left()), str(self.sceneBoundingRect().top()))
        event.accept()
    '''
    
    def update(self):
        self.set_name()
        self.set_tooltip()
        super(GenericNode, self).update()

    #- ATTRIBUTES -----
    def set_name(self):
        """
        Set the node title
        
        todo: should be in NodeBase
        """
        if not self._name_text:
            font = QtGui.QFont("SansSerif", 14)
            #font.setStyleHint(QtGui.QFont.Helvetica)
            font.setStretch(100)
            self._name_text = QtGui.QGraphicsTextItem(self._node_name, self)
            self._name_text.setFont(font)
            self._name_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
            self._name_text.setPos(self.sceneBoundingRect().left(), self.sceneBoundingRect().top())
            #self._name_text.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        else:
            self._name_text.setPlainText(self._node_name)
    
    def set_tooltip(self):
        """
        Set the tooltip text in the graph
        """
        self.setToolTip(self.path())
    
    @QtCore.Slot()
    def addNodeAttributes(self, **kwargs):
        """
        Add random attributes to the node
        
        todo: should be in NodeBase
        """
        self._attributes.update(**kwargs)
        self.nodeChanged.emit(True)
    
    @QtCore.Slot()
    def addAttr(self, val):
        self._attributes[val]=''
        self.nodeChanged.emit(True)
    
    def getNodeAttributes(self):
        return self._attributes
    
    def getAttr(self, attribute):
        """
        Query a specific node's attribute
        """
        return self.getNodeAttributes().get(attribute, None)
    
    def addInputAttributes(self, *attrs):
        """
        Add input attributes to the node
        
        todo: should be in NodeBase
        """
        start_y = self.sceneBoundingRect().top() + 36
        font = QtGui.QFont("SansSerif", 10)
        font.setStretch(100)
        for attr in attrs:
            if attr not in self.getInputAttributes():   
                #print '# adding attr "%s" at y: %d' % (attr, start_y)
                attr_text = QtGui.QGraphicsTextItem(attr, self)
                attr_text.setFont(font)
                attr_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
                attr_text.setPos(self.sceneBoundingRect().left()+5, start_y)
                connection = NodeInput(self, name=attr)
                #input_node.setPos(-input_node.width()/2, input_node.height()/2 + 9)
                connection.setPos(self.sceneBoundingRect().left()-7, start_y+5)
                self._connections.get('input').update(**{attr:connection})
                start_y+=30       

    def addOutputAttributes(self, *attrs):
        """
        Add input attributes to the node
        
        todo: should be in NodeBase
        """
        start_y = self.sceneBoundingRect().top() + 36
        font = QtGui.QFont("SansSerif", 10)
        font.setStretch(100)
        for attr in attrs:
            if attr not in self.getInputAttributes():   
                #print '# adding attr "%s" at y: %d' % (attr, start_y)
                attr_text = QtGui.QGraphicsTextItem(attr, self)
                
                attr_text.setFont(font)
                attr_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
                attr_text.setPos(self.sceneBoundingRect().center().x()+15, start_y)
                connection = NodeOutput(self, name=attr)
                #input_node.setPos(-input_node.width()/2, input_node.height()/2 + 9)
                connection.setPos(self.sceneBoundingRect().right()-7, start_y+5)
                self._connections.get('output').update(**{attr:connection})
                start_y+=30       

    def getInputAttributes(self):
        return self._connections.get('input', {}).keys()     

    def getOutputAttributes(self):
        return self._connections.get('output', {}).keys()
    
    def getInputConnection(self, conn_name):
        """
        Returns the input connection NODE for the given name
        """
        return self._connections.get('input').get(conn_name, None)

    def getOutputConnection(self, conn_name):
        """
        Returns the output connection NODE for the given name
        """
        return self._connections.get('output').get(conn_name, None)
    
    def getConnectedLines(self):
        result = []
        for typ, values in self._connections.iteritems():
            if values:
                for node_name, node in values.iteritems():                
                    if node.connectedLine:
                        for line in node.connectedLine:
                            if line not in result:
                                result.append(line)
        return result
    
    @property
    def node_name(self):
        return self._node_name
    
    @node_name.setter
    def node_name(self, val):
        self._node_name = val
        self.set_name()
    
    @property
    def width(self):
        return self.sceneBoundingRect().width()

    @property
    def height(self):
        return self.sceneBoundingRect().height()

    def deleteNode(self):
        # disconnection logic here
        if self.getConnectedLines():
            for node in self.getConnectedLines():
                self.scene().graph.removeNode(node)
        self.scene().graph.removeNode(self)
    
    @property
    def data(self):
        data = dict()
        data.update(x=self.sceneBoundingRect().x())
        data.update(y=self.sceneBoundingRect().y())
        data.update(width=self.width)
        data.update(height=self.height)
        data.update(**self.dumpArbitraryAttributes())
        return data
    
    def dumpArbitraryAttributes(self):
        result = dict()
        for attr in sorted(self._attributes.keys()):
            value = self._attributes.get(attr)
            result['__%s' % attr] = value
        return result
    
    def dump(self):
        output_data = {self.node_name:self.data}
        print json.dumps(output_data, indent=5)

#- CONNECTIONS -----


class ConnectionBase(object):
    def __init__(self, *args, **kwargs):
        
        self._is_node           = False                         # this is a connection, not a scene graph node
        self._node_name         = kwargs.pop('name', None)
        self._parent            = None
        self.nodeimage          = None
        self.isInputConnection  = False
        self.isOutputConnection = False
        self.connectedLine      = []
        
        # json output functions
    
    def __repr__(self):
        return '%s.%s' % (self._parent.node_name, self.node_name)
    
    @property
    def node_name(self):
        return str(self._node_name)
    
    def path(self):
        return '%s.%s' % (self._parent.path(), self.node_name)
    

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
        
        self.node_name = "%s.%s" % (self.myStartItem, self.myEndItem)
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
class SimpleNode(QtGui.QGraphicsItem):
    
    Type                = QtGui.QGraphicsItem.UserType + 3
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeCreatedInScene  = QtCore.Signal()
    nodeChanged         = QtCore.Signal(bool)

    def __init__(self, name='Node1', width=100, height=175, font='Consolas'):
        QtGui.QGraphicsItem.__init__(self)
        
        self.name            = name
        self.width           = width
        self.height          = height
        
        # buffers
        self.bufferX         = 3
        self.bufferY         = 3
        self.color           = [180, 180, 180]
        
        self.label           = QtGui.QGraphicsSimpleTextItem(parent=self)
        self._font_family    = font
        self._font_size      = 10
        self._font_bold      = False
        self._font_italic    = False
        self.font            = QtGui.QFont(self._font_family)
        self._is_node        = True
        
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)        

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return SimpleNode.Type

    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        return QtCore.QRectF(-self.width/2  - self.bufferX,  -self.height/2 - self.bufferY,
                              self.width  + 3 + self.bufferX, self.height + 3 + self.bufferY)
    
    # Label formatting -----
    def setLabelItalic(self, val=False):
        self._font_italic = val

    def setLabelBold(self, val=False):
        self._font_bold = val

    def buildNodeLabel(self):
        self.label.setX(-(self.width/2 - self.bufferX))
        self.label.setY(-(self.height/2 - self.bufferY))
        self.font = QtGui.QFont(self._font_family)
        self.font.setPointSize(self._font_size)
        self.font.setBold(self._font_bold)
        self.font.setItalic(self._font_italic)
        self.label.setFont(self.font)
        self.label.setText(self.name)
    
    def getLabelLine(self):
        p1 = self.boundingRect().topLeft()
        p1.setY(p1.y() + self.bufferY*8)
        p2 = self.boundingRect().topRight()
        p2.setY(p2.y() + self.bufferY*8)
        return QtCore.QLineF(p1, p2)
    
    def paint(self, painter, option, widget):
        """
        Draw the node.
        """
        # label & line
        self.buildNodeLabel()        
        label_line = self.getLabelLine()
       
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*self.color)))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        painter.drawRect(self.boundingRect())
        painter.drawLine(label_line)
        #painter.drawText(self.boundingRect().x()+self.buffer, self.boundingRect().y()+self.buffer, self.name)


class MyLine(QtGui.QGraphicsLineItem):
    def __init__(self, start_item, end_item, *args, **kwargs):
        super(MyLine, self).__init__(*args, **kwargs)
        
        self._start_item   = start_item
        self._end_item     = end_item


class MyPath(QtGui.QGraphicsPathItem):
    pass
