#!/usr/bin/env python
import os
import math
import uuid
from PySide import QtGui, QtCore, QtSvg
import simplejson as json

from .. import options
reload(options)


class NodeWidget(QtGui.QGraphicsObject):
    
    Type                = QtGui.QGraphicsObject.UserType + 3
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeCreatedInScene  = QtCore.Signal()
    nodeChanged         = QtCore.Signal(str, dict)
    PRIVATE             = ['width', 'height', 'expanded', 'pos_x', 'pos_y']
    
    """
    Simple node type widget.
    
    Represents a node without any connectable attributes.
    """
    def __init__(self, node, **kwargs):
        QtGui.QGraphicsObject.__init__(self)        

        # set the dag node widget attribute
        self.dagnode            = node
        self.dagnode._widget    = self       

        # flag for an expanded node
        self.is_expandable      = True
        self.expanded           = kwargs.get('expanded', False)
        self.expand_widget      = None

        # input/output terminals
        self.input_widget      = ConnectionWidget(self)
        self.input_widget.setParentItem(self)

        self.output_widget      = ConnectionWidget(self, is_input=False)
        self.output_widget.setParentItem(self)

        # width/height attributes
        self.width              = kwargs.get('width', 120)        
        self.height_collapsed   = 15
        self.height             = kwargs.get('height', 175) if self.expanded else self.height_collapsed

        # buffers
        self.bufferX            = 3
        self.bufferY            = 3
        self.color              = [180, 180, 180]
        
        # font/label attributes
        self.label              = QtGui.QGraphicsTextItem(parent=self)
        self.font               = kwargs.get('font', 'Monospace')
        self._font_size         = 8
        self._font_bold         = False
        self._font_italic       = False
        self.qfont              = QtGui.QFont(self.font)


        # widget flags
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsObject.ItemIsMovable | QtGui.QGraphicsObject.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(1)

        # set the postition
        pos_x = kwargs.get('pos_x', 0)
        pos_y = kwargs.get('pos_y', 0)
        self.setPos(pos_x, pos_y)

    @property
    def node_class(self):
        return 'dagnode'    

    @property
    def UUID(self):
        if self.dagnode:
            return self.dagnode.UUID
        return None

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return NodeWidget.Type
    
    def shape(self):
        """
        Aids in selection.
        """
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-self.width/2, -self.height/2, self.width, self.height), 7, 7)
        return path

    def anchorScenePos(self):
        """
        Return anchor position in scene coordinates.
        """
        return self.mapToScene(QPointF(0, 0))

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsObject.ItemScenePositionHasChanged:
            self.scenePositionChanged.emit(value)  
        return QtGui.QGraphicsObject.itemChange(self, change, value)

    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        return QtCore.QRectF(-self.width/2  - self.bufferX,  -self.height/2 - self.bufferY,
                              self.width  + 3 + self.bufferX, self.height + 3 + self.bufferY)
    
    #- Events -----
    def hoverEnterEvent(self, event):
        QtGui.QGraphicsObject.hoverEnterEvent(self, event)

    @QtCore.Slot()
    def nodeNameChanged(self):
        """
        Runs when the label text is edited.
        """
        node_name = self.label.document().toPlainText()
        cur_name = self.dagnode.name
        UUID = str(self.dagnode.UUID)
        if node_name != cur_name:
            print '# NodeWidget: Node name updated: ', node_name
            self.dagnode.name = node_name
            self.nodeChanged.emit(UUID, {'name':node_name})

    def getLabelLine(self):
        """
        Draw a line for the node label area
        """
        p1 = self.boundingRect().topLeft()
        p1.setY(p1.y() + self.bufferY*7)
        p2 = self.boundingRect().topRight()
        p2.setY(p2.y() + self.bufferY*7)
        return QtCore.QLineF(p1, p2)
    
    def getHiddenIcon(self):
        """
        Returns an icon for the hidden state of the node
        """
        # expanded icon
        tr = self.boundingRect().topRight()
        top_rx = tr.x()
        top_ry = tr.y()

        buf = 8
        triw = 8

        p1 = QtCore.QPointF(top_rx - buf, (top_ry + buf) + (triw / 2))
        p2 = QtCore.QPointF(top_rx - (buf + triw), (top_ry + buf) + (triw / 2))
        p3 = QtCore.QPointF((p1.x() + p2.x()) / 2, (top_ry + buf - (triw / 2)) + (triw / 2))

        tripoly = QtGui.QPolygonF([p1, p2, p3])
        triangle = QtGui.QGraphicsPolygonItem(tripoly, self, None)
        triangle.setPen(QtGui.QPen(QtGui.QColor(0,0,0, 50)))
        triangle.setBrush(QtGui.QBrush(QtGui.QColor(125,125,125)))
        return triangle

    def getExpandedIcon(self):
        """
        Returns an icon for the expanded state of the node
        """
        # expanded icon
        tr = self.boundingRect().topRight()
        top_rx = tr.x()
        top_ry = tr.y()

        buf = 8
        triw = 8

        p1 = QtCore.QPointF(top_rx - buf, (top_ry + buf))
        p2 = QtCore.QPointF(top_rx - (buf + triw), (top_ry + buf))
        p3 = QtCore.QPointF((p1.x() + p2.x()) / 2, (top_ry + buf + (triw / 2)))

        tripoly = QtGui.QPolygonF([p1, p2, p3])
        triangle = QtGui.QGraphicsPolygonItem(tripoly, self, None)
        triangle.setPen(QtGui.QPen(QtGui.QColor(0,0,0, 50)))
        triangle.setBrush(QtGui.QBrush(QtGui.QColor(125,125,125)))
        return triangle

    def setExpanded(self, val=True):
        """
        Toggle the node's expanded value.
        """
        self.expanded = val
        top_val = self.boundingRect().top()
        if val:
            self.height = 175
            self.moveBy(0, 175/2 - self.height_collapsed - 4 )

        else:
            self.height = self.height_collapsed
            self.moveBy(0, -175 + 4)
        self.update()
        
    def buildNodeLabel(self, shadow=True):
        """
        Build the node's label attribute.
        """
        self.label.setX(-(self.width/2 - self.bufferX + 3))
        self.label.setY(-(self.height/2 + self.bufferY))
        #self.label.setY(self.boundingRect().top() + (self.height_collapsed - self.bufferY*1.5))

        self.qfont = QtGui.QFont(self.font)
        self.qfont.setPointSize(self._font_size)
        self.qfont.setBold(self._font_bold)
        self.qfont.setItalic(self._font_italic)

        self.label.setFont(self.qfont)
        self.label.setPlainText(self.dagnode.name)
        self.label.setDefaultTextColor(QtGui.QColor(0, 0, 0))

        # make the label editable
        self.label.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        label_doc = self.label.document()
        label_doc.setMaximumBlockCount(1)
        label_doc.contentsChanged.connect(self.nodeNameChanged)

        # drop shadow
        if shadow:
            self.tdropshd = QtGui.QGraphicsDropShadowEffect()
            self.tdropshd.setBlurRadius(6)
            self.tdropshd.setColor(QtGui.QColor(0,0,0,120))
            self.tdropshd.setOffset(1,2)
            self.label.setGraphicsEffect(self.tdropshd)

    def paint(self, painter, option, widget):
        """
        Draw the node.
        """
        #self.scene().removeItem(self.label)
        self.buildNodeLabel()

        # label & line
        if self.expanded:    
            label_line = self.getLabelLine()

        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        # background
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)

        if option.state & QtGui.QStyle.State_Selected:
            gradient.setColorAt(0, QtGui.QColor(255, 172, 0))
            gradient.setColorAt(1, QtGui.QColor(200, 128, 0))

        elif option.state & QtGui.QStyle.State_MouseOver:
            gradient.setColorAt(0, QtGui.QColor(200, 200, 200))
            gradient.setColorAt(1, QtGui.QColor(150, 150, 150))

        else:
            topGrey = self.color[0]
            bottomGrey = self.color[0] / 1.5
            gradient.setColorAt(0, QtGui.QColor(topGrey, topGrey, topGrey))
            gradient.setColorAt(1, QtGui.QColor(bottomGrey, bottomGrey, bottomGrey))

        
        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))

        fullRect = self.boundingRect()
        painter.drawRoundedRect(fullRect, 7, 7)

        if self.expanded:
            painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0, 90)))
            painter.drawLine(label_line)

        if self.expand_widget:
            self.expand_widget.scene().removeItem(self.expand_widget)

        if self.expanded:
            self.expand_widget = self.getExpandedIcon()
        else:
            self.expand_widget = self.getHiddenIcon()
        self.label.setPlainText(self.dagnode.name)

        self.output_widget.update()
        self.input_widget.update()


class ConnectionWidget(QtGui.QGraphicsObject):
    
    Type                = QtGui.QGraphicsObject.UserType + 4
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeChanged         = QtCore.Signal(str, dict)
    PRIVATE             = []

    def __init__(self, parent=None, is_input=True, **kwargs):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.node       = parent

        self.color      = [255, 255, 0]
        self.dagnode    = parent.dagnode
        self.radius     = 8

        self.is_input   = is_input
        self.attribute  = kwargs.get('attribute', None)

        if self.attribute is None:
            if self.is_input:
                self.attribute ='input'
            else:
                self.attribute = 'output'

        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsItem.ItemNegativeZStacksBehindParent)

        self.setAcceptHoverEvents(True)
        self.setZValue(- 1)



    def __str__(self):
        return '%s.%s' % (self.dagnode.name, self.attribute)

    def __repr__(self):
        return str(self)

    @property
    def node_class(self):
        return 'connection'    

    @property
    def node_class(self):
        return 'connection'  

    @property
    def UUID(self):
        if self.dagnode:
            return self.dagnode.UUID
        return None

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return NodeWidget.Type
    
    def shape(self):
        """
        Aids in selection.
        """
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def boundingRect(self):
        """
        Defines the clickable hit box.

        top left, width, height
        """
        if self.is_input:
            return QtCore.QRectF(self.parentItem().boundingRect().left() - self.radius/2, 
                                            self.parentItem().boundingRect().center().y() - self.radius/2, 
                                            self.radius, 
                                            self.radius)
        else:
            return QtCore.QRectF(self.parentItem().boundingRect().right() - self.radius/2, 
                                self.parentItem().boundingRect().center().y() - self.radius/2, 
                                self.radius, 
                                self.radius)

    def paint(self, painter, option, widget):
        """
        Draw the connection widget.
        """
        # background
        gradient = QtGui.QLinearGradient(0, -self.radius/2, 0, self.radius/2)
        grad = .5
        color = self.color

        if option.state & QtGui.QStyle.State_Selected:
            color = [255, 0, 0]
        
        else:
            if option.state & QtGui.QStyle.State_MouseOver:
                color = [255, 157, 0]

        gradient.setColorAt(0, QtGui.QColor(*color))
        gradient.setColorAt(1, QtGui.QColor(color[0]*grad, color[1]*grad, color[2]*grad))
        
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        #painter.setPen(QtGui.QColor(*color))

        painter.setPen(QtGui.QPen(QtGui.QBrush(QtGui.QColor(color[0]*grad, color[1]*grad, color[2]*grad)), 0.5, QtCore.Qt.SolidLine))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawEllipse(self.boundingRect())
        

# Line class for connecting the nodes together
class EdgeWidget(QtGui.QGraphicsLineItem):

    def __init__(self, source_item, dest_item, *args, **kwargs):
        super(EdgeWidget, self).__init__(*args, **kwargs)

        # The arrow that's drawn in the center of the line
        self.arrowhead      = QtGui.QPolygonF()
        self.color          = QtCore.Qt.white

        self.source_item    = source_item
        self.dest_item      = dest_item
               
        self.source_point   = QtCore.QPointF(self.source_item.boundingRect().center())
        self.dest_pint      = QtCore.QPointF(self.dest_item.boundingRect().center())
        self.centerpoint    = QtCore.QPointF()  # for bezier lines
        
        self.setZValue(-1.0)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setPen(QtGui.QPen(self.color, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        
        self.name = "%s.%s" % (self.source_item, self.dest_item)


    @property
    def node_class(self):
        return 'edge' 

    def __repr__(self):
        return '%s >> %s' % (self.source_item, self.dest_item)
    
    def deleteNode(self):
        # For whatever the shit reason, I have to have this check. If I don't, I get an error in rare cases.
        if self:
            #self.getEndItem().getWidgetMenu().receiveFrom(self.getStartItem(), delete=True)
            #self.getStartItem().getWidgetMenu().sendData(self.getStartItem().getWidgetMenu().packageData())
            #self.getStartItem().removeReferences()
            self.scene().removeItem(self)
            self.source_item.connectedLine.remove(self)
            self.dest_item.connectedLine.remove(self)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.deleteNode()
            self.update()
        else:
            super(EdgeWidget, self).keyPressEvent(event)

    def getCenterPoint(self):
        line = self.getLine()
        centerX = (line.p1().x() + line.p2().x())/2
        centerY = (line.p1().y() + line.p2().y())/2
        return QtCore.QPointF(centerX, centerY)

    def getLine(self):
        p1 = self.source_item.sceneBoundingRect().center()
        p2 = self.dest_item.sceneBoundingRect().center()
        return QtCore.QLineF(self.mapFromScene(p1), self.mapFromScene(p2))

    def getEndItem(self):
        return self.dest_item.parentItem()

    def getStartItem(self):
        return self.source_item.parentItem()

    def updatePosition(self):
        self.setLine(self.getLine())
        self.source_item.connectedLine.append(self)
        self.dest_item.connectedLine.append(self)

    def boundingRect(self):
        extra = (self.pen().width() + 100)  / 2.0
        line = self.getLine()
        p1 = line.p1()
        p2 = line.p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        path = super(EdgeWidget, self).shape()
        path.addPolygon(self.arrowhead)
        return path

    def paint(self, painter, option, widget=None):
        arrowSize = 10.0
        line = self.getLine()
        painter.setBrush(self.color)
        myPen = self.pen()
        myPen.setColor(self.color)
        painter.setPen(myPen)

        if self.isSelected():
            painter.setBrush(QtCore.Qt.yellow)
            myPen.setColor(QtCore.Qt.yellow)
            myPen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(myPen)

        if line.length() > 0.0:

            try:
                angle = math.acos(line.dx() / line.length())
            except ZeroDivisionError:
                angle = 0

            if line.dy() >= 0:
                angle = (math.pi * 2.0) - angle

            if self.source_item.is_input:
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
            self.arrowhead.clear()

            # Set the points of the arrowHead polygon
            for point in [centerPoint, arrowP1, arrowP2]:
                self.arrowhead.append(point)

            if line:
                painter.drawPolygon(self.arrowhead)
                painter.drawLine(line)
                #painter.drawCubicBezier(line)

