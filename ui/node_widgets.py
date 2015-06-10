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

        # width/height attributes
        self.width              = kwargs.get('width', 120)        
        self.height_collapsed   = 15
        self.height             = kwargs.get('height', 175) if self.expanded else self.height_collapsed

        # buffers
        self.bufferX            = 3
        self.bufferY            = 3

        # colors
        self._color             = [180, 180, 180]
        self.color_mult         = 0.5

        # input/output terminals
        self.input_widget      = ConnectionWidget(self)
        self.input_widget.setParentItem(self)

        self.output_widget      = ConnectionWidget(self, is_input=False)
        self.output_widget.setParentItem(self)
        
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

    def __repr__(self):
        return '< %s: %s >' % (self.node_class.title(), self.dagnode.name)

    @property
    def node_class(self):
        return 'dagnode'    

    @property
    def UUID(self):
        if self.dagnode:
            return self.dagnode.UUID
        return None

    @property
    def color(self):
        if self.dagnode:
            return self.dagnode.color
        return self._color

    @color.setter
    def color(self, val):
        if self.dagnode:
            self.dagnode.color = val
        self._color = val
        self.update()

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

    def defaultInputPos(self):
        """
        Returns the default input connection center.
        """
        return QtCore.QPointF(self.boundingRect().left() - self.height_collapsed/2, self.height_collapsed/2)

    def defaultOutputPos(self):
        """
        Returns the default output connection center.
        """
        return QtCore.QPointF(self.boundingRect().right() - self.height_collapsed/2, self.height_collapsed/2)

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
    def nodeChangedAction(self):
        self.nodeChanged.emit(UUID, self.dagnode)

    @QtCore.Slot()
    def nodeNameChanged(self):
        """
        Runs when the label text is edited.
        """
        node_name = self.label.document().toPlainText()
        cur_name = self.dagnode.name
        UUID = str(self.dagnode.UUID)
        if node_name != cur_name:
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

        p2a = QtCore.QPointF((p1.x() + p2.x()) / 2, (top_ry + buf) + (triw / 2))
        """
        # expanded icon
        tr = self.boundingRect().topRight()
        tl = self.boundingRect().topLeft()
        top_rx = tr.x()
        top_ry = tr.y()

        buf = 8
        triw = 8

        p1 = QtCore.QPointF(top_rx - buf, (top_ry + buf) + (triw / 2))
        p2 = QtCore.QPointF(top_rx - (buf + triw), (top_ry + buf) + (triw / 2))
        p3 = QtCore.QPointF((p1.x() + p2.x()) / 2, (top_ry + buf - (triw / 2)) + (triw / 2))

        tripoly = QtGui.QPolygonF([p1, p2, p3])
        triangle = QtGui.QGraphicsPolygonItem(tripoly, self, None)

        i1 = 0.4
        i2 = 0.5
        color1 = [self.color[0] * i1, self.color[1] * i1, self.color[2] * i1, 125]
        color2 = [self.color[0] * i2, self.color[1] * i2, self.color[2] * i2, 125]

        gradient = QtGui.QLinearGradient(p1,p2)
        gradient.setColorAt(0, QtGui.QColor(*color1))
        gradient.setColorAt(0.49, QtGui.QColor(*color1))
        gradient.setColorAt(.51, QtGui.QColor(*color2))
        gradient.setColorAt(1, QtGui.QColor(*color2))
        triangle.setPen(QtGui.QPen(QtGui.QColor(0,0,0, 15)))
        triangle.setBrush(gradient)
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

        i1 = 0.4
        i2 = 0.5
        color1 = [self.color[0] * i1, self.color[1] * i1, self.color[2] * i1, 125]
        color2 = [self.color[0] * i2, self.color[1] * i2, self.color[2] * i2, 125]

        gradient = QtGui.QLinearGradient(p1,p2)
        gradient.setColorAt(0, QtGui.QColor(*color1))
        gradient.setColorAt(0.49, QtGui.QColor(*color1))
        gradient.setColorAt(.51, QtGui.QColor(*color2))
        gradient.setColorAt(1, QtGui.QColor(*color2))

        triangle.setPen(QtGui.QPen(QtGui.QColor(0,0,0, 15)))
        triangle.setBrush(gradient)
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
        
        # define the graident background
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)

        top_color = self.color
        if option.state & QtGui.QStyle.State_Selected:
            top_color =[255, 172, 0]

        btm_color = [float(top_color[0]) * self.color_mult, float(top_color[1]) * self.color_mult, float(top_color[2]) * self.color_mult]
        gradient.setColorAt(0, QtGui.QColor(*top_color))
        gradient.setColorAt(1, QtGui.QColor(*btm_color))
       
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

        self.node           = parent

        self.color          = [255, 255, 0]
        self.dagnode        = parent.dagnode
        self.radius         = 8.0
        self.max_conn       = 1 

        self.is_input       = is_input
        self.attribute      = kwargs.get('attribute', None)
        self.centerpoint    = QtCore.QPointF(0, 0)

        if self.attribute is None:
            if self.is_input:
                self.attribute ='input'
                self.centerpoint = parent.defaultInputPos()
            else:
                self.attribute = 'output'
                self.centerpoint = parent.defaultOutputPos()

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable | QtGui.QGraphicsItem.ItemNegativeZStacksBehindParent)
        self.setZValue(-2)

    def __str__(self):
        return '< Connection: %s.%s >' % (self.dagnode.name, self.attribute)

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return '%s.%s' % (self.dagnode.name, self.attribute)  

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
    
    def getHitbox(self, adjustment=15):
        """
        DEBUGGING:  

            - get adjusted hitbox for easier selection.
        """
        rect = self.boundingRect()
        return QtCore.QRectF(rect.topLeft().x() - adjustment/2,  rect.topLeft().y() - adjustment/2, rect.width() + adjustment, rect.height() + adjustment)

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

    def shape(self):
        """
        Aids in selection.
        """
        path = QtGui.QPainterPath()
        polyon = QtGui.QPolygonF(self.getHitbox())
        path.addPolygon(polyon)
        return path

    def paint(self, painter, option, widget):
        """
        Draw the connection widget.
        """
        # DEBUG
        blackColor = QtGui.QColor(0, 0, 0)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(blackColor, 0.25, QtCore.Qt.DashDotLine))
        painter.drawRect(self.getHitbox())


        self.setToolTip('%s.%s' % (self.dagnode.name, self.attribute))
        # background
        gradient = QtGui.QLinearGradient(0, -self.radius/2, 0, self.radius/2)
        grad = .5

        if self.isInputConnection():
            color = self.color

        if self.isOutputConnection():
            color = [0, 255, 0]

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


    def isInputConnection(self):
        if self.is_input:
            return True
        return False

    def isOutputConnection(self):
        if self.is_input:
            return False
        return True


# edge class for connecting nodes
class EdgeWidget(QtGui.QGraphicsLineItem):

    adjustment = 5

    def __init__(self, source_item, dest_item, *args, **kwargs):
        QtGui.QGraphicsLineItem.__init__(self, *args, **kwargs)

        # The arrow that's drawn in the center of the line
        self.arrowhead      = QtGui.QPolygonF()
        self.color          = QtCore.Qt.white

        self.source_item    = source_item
        self.dest_item      = dest_item

        self.arrow_size     = 12
        self.show_conn      = False             # show connection string
        self.multi_conn     = False             # multiple connections (future)
        self.conn_label     = None      

        self.source_point   = QtCore.QPointF(self.source_item.boundingRect().center())
        self.dest_point     = QtCore.QPointF(self.dest_item.boundingRect().center())
        self.centerpoint    = QtCore.QPointF()  # for bezier lines       
        self.bezier_path    = None

        self.c1             = QtCore.QPointF(0,0)
        self.c2             = QtCore.QPointF(0,0)

        self.cp1            = ControlPoint(self.source_point, self) 
        self.cp2            = ControlPoint(self.dest_point, self)

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setPen(QtGui.QPen(self.color, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        
        self.name = "%s.%s" % (self.source_item, self.dest_item)
        self.setZValue(-1.0)

    @property
    def node_class(self):
        return 'edge' 

    def __repr__(self):
        return '< Edge: %s >' % self.connection
    
    @property
    def connection(self):
        if self.source_item and self.dest_item:
            return '%s>%s' % (self.source_item, self.dest_item)
        else:
            if not self.source_item:
                return '>%s' % self.dest_item
            if not self.dest_item:
                return '%s>' % self.source_item

    def deleteNode(self):
        if self:
            self.scene().removeItem(self)
            self.source_item.connectedLine.remove(self)
            self.dest_item.connectedLine.remove(self)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.deleteNode()
            self.update()
        else:
            QtGui.QGraphicsLineItem.keyPressEvent(self, event)

    def getLine(self):
        """
        Return the line between two points.
        """
        p1 = self.source_item.sceneBoundingRect().center()
        p2 = self.dest_item.sceneBoundingRect().center()

        # offset the end point a few pixels
        p2 = QtCore.QPointF(p2.x()-4, p2.y())
        return QtCore.QLineF(self.mapFromScene(p1), self.mapFromScene(p2))

    def getBezierPath(self, poly=False):
        """
        Returns a bezier path based on the current line.
        Hacky, but works.
        """
        line = self.getLine()
        path = QtGui.QPainterPath()
        path.moveTo(line.p1().x(), line.p1().y())

        x1 = line.p1().x()
        x2 = line.p2().x()

        y1 = line.p1().y()
        y2 = line.p2().y()

        lx = x2 - x1
        hy = y2 - y1

        r = 0
        if lx and hy:
            r  = lx/hy

        sx = lx/4

        #print 'ratio: %.2f' % r
        #print 'len x: ', lx
        #print 'len y: ', hy

        x11 = x1 + sx*1
        x12 = x11 + sx*2

        self.c1 = QtCore.QPointF(x11, y1 - lx/6)
        self.c2 = QtCore.QPointF(x12, y2 + lx/6)
        curvePoly = QtGui.QPolygonF([line.p1(), self.c1, self.c2, line.p2()])
        #
        path.cubicTo(self.c1, self.c2, line.p2())
        #path.quadTo(line.p1(), line.p2())
        return path

    def getCenterPoint(self):
        line = self.getLine()
        centerX = (line.p1().x() + line.p2().x())/2
        centerY = (line.p1().y() + line.p2().y())/2
        return QtCore.QPointF(centerX, centerY)

    def getEndPoint(self):
        line = self.getLine()
        ep = line.p2()
        return QtCore.QPointF(ep.x(), ep.y())

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
        """
        Need to add some adjustments to the line to make is more selectable.
        """
        path = QtGui.QPainterPath()
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(30)
        line = self.getLine()
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        return stroker.createStroke(path)

    def buildConnectionLabel(self):
        line = self.getLine()
        p1 = line.p1()
        p2 = line.p2()

        # draw a label showing the connection
        dx = p2.x() - p1.x()
        dy = p2.y() -  p1.y()
        rads = math.atan2(-dy,dx)
        rads %= 2*math.pi
        degs = math.degrees(rads)

        text = QtGui.QGraphicsSimpleTextItem(str(self))

        text.setParentItem(self)
        #text.setRenderHints(QtGui.QPainter.TextAntialiasing)
        text.setBrush(QtGui.QBrush(QtGui.QColor(255,255,255)))
      
        tw = text.boundingRect().width()
        th = text.boundingRect().height()
        center = self.boundingRect().center()
        
        text.rotate(-degs)
        text.setPos(center.x()-tw/2, center.y()-th/2)
        return text

    def paint(self, painter, option, widget=None):
        """
        Draw the line and arrow.
        """
        self.setToolTip(str(self))
        self.show_conn = False
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)

        line = self.getLine()
        painter.setBrush(self.color)
        epen = self.pen()
        epen.setColor(self.color)
        painter.setPen(epen)

        if option.state & QtGui.QStyle.State_Selected:
            painter.setBrush(QtCore.Qt.yellow)
            epen.setColor(QtCore.Qt.yellow)
            painter.setPen(epen)

        if option.state & QtGui.QStyle.State_MouseOver:
            painter.setBrush(QtCore.Qt.green)
            epen.setColor(QtCore.Qt.green)
            painter.setPen(epen)
            self.show_conn = True

        # calculate the arrowhead geometry
        if line.length() > 0.0:
            angle = math.acos(line.dx() / line.length())
            if line.dy() >= 0:
                angle = (math.pi * 2.0) - angle

            if self.source_item.is_input:
                revArrow = 1
            else:
                revArrow = -1


            center_point = self.getCenterPoint()
            end_point = self.getEndPoint()
            
            if self.bezier_path:
                end_point = self.bezier_path.pointAtPercent(0.95)
                #bangle = math.atan2f(point3.y - point2.y, point3.x - point2.x)
                #end_point = QtCore.QPointF(bp.x, bp.y)

            arrow_p1 = end_point + QtCore.QPointF(math.sin(angle + math.pi / 3.0) * self.arrow_size * revArrow,
                                        math.cos(angle + math.pi / 3.0) * self.arrow_size * revArrow)
            arrow_p2 = end_point + QtCore.QPointF(math.sin(angle + math.pi - math.pi / 3.0) * self.arrow_size * revArrow,
                                        math.cos(angle + math.pi - math.pi / 3.0) * self.arrow_size * revArrow)
            # clear the arrow
            self.arrowhead.clear()

            # set the polygon points
            for point in [end_point, arrow_p1, arrow_p2]:
                self.arrowhead.append(point)

            #self.scene().removeItem(self.conn_label)
            #self.conn_label = self.buildConnectionLabel()
            if line:
                painter.drawPolygon(self.arrowhead)
                self.bezier_path = self.getBezierPath()
                #painter.drawLine(line)
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawPath(self.bezier_path)

                # DEBUG: draw control points
                red_color = QtGui.QColor(226,36,36)
                blue_color = QtGui.QColor(155, 195, 226)

                cp_pen = QtGui.QPen(QtCore.Qt.SolidLine)
                cp_pen.setColor(red_color)

                l_pen = QtGui.QPen(QtCore.Qt.SolidLine)
                l_pen.setColor(blue_color)

                # control lines
                painter.setPen(l_pen)
                l1 = QtCore.QLineF(line.p1(), self.c1)
                l2 = QtCore.QLineF(self.c1, self.c2)
                l3 = QtCore.QLineF(self.c2, line.p2())
                painter.drawLines([l1, l2, l3])

                # control points
                painter.setPen(cp_pen)
                painter.setBrush(QtGui.QBrush(red_color))
                #painter.drawEllipse(self.c1, 4, 4)
                #painter.drawEllipse(self.c2, 4, 4)

                #self.cp1.scene().removeItem(self.cp1)
                #self.cp2.scene().removeItem(self.cp2)

                #self.cp1 = ControlPoint(self.c1, self)
                #self.cp2 = ControlPoint(self.c2, self)
                self.cp1.setPos(self.mapToScene(QtCore.QPointF(self.c1.x(), self.c1.y())))
                self.cp2.setPos(self.mapToScene(QtCore.QPointF(self.c2.x(), self.c2.y())))

                #self.cp1.update()
                #self.cp2.update()


    def hoverEnterEvent(self, event):
        QtGui.QGraphicsLineItem.hoverEnterEvent(self, event)



class ControlPoint(QtGui.QGraphicsObject):
    
    def __init__(self, center, parent=None, **kwargs):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.center_point   = center
        self.edge           = parent

        self.color          = kwargs.get('color', [225, 35, 35])
        self.radius         = kwargs.get('radius', 4.0)

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable | QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)

    def boundingRect(self):
        return QtCore.QRectF(-self.radius/2  - self.radius,  -self.radius/2 - self.radius,
                              self.radius  + self.radius, self.radius + self.radius)

    def setPos(self, pos):
        pos = self.mapFromScene(pos)
        self.translate(pos.x(), pos.y())
        self.center_point = pos

    def paint(self, painter, option, widget=None):
        """
        Draw the line and arrow.
        """
        red_color = QtGui.QColor(226,36,36)

        cp_pen = QtGui.QPen(QtCore.Qt.SolidLine)
        cp_pen.setColor(red_color)

        # control points
        painter.setPen(cp_pen)
        painter.setBrush(QtGui.QBrush(red_color))
        painter.drawEllipse(self.center_point, 4, 4)

        self.setToolTip("(%.2f, %.2f)" % (self.center_point.x(), self.center_point.y()))
