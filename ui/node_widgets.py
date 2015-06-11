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
        self.enabled            = True

        # buffers
        self.bufferX            = 3
        self.bufferY            = 3

        # debugging
        self.debug_mode         = False

        # colors
        self._color             = [180, 180, 180]
        self.color_mult         = 0.5
        self.debug_color        = [0, 0, 0]

        # input/output terminals
        self.input_widget      = ConnectionWidget(self)
        self.input_widget.setParentItem(self)

        self.output_widget      = ConnectionWidget(self, is_input=False)
        self.output_widget.setParentItem(self)
        
        # font/label attributes
        self.label              = NodeLabel(self)

        self.font               = kwargs.get('font', 'Monospace')
        self._font_size         = 8
        self._font_bold         = False
        self._font_italic       = False
        self.qfont              = QtGui.QFont(self.font)

        # widget flags
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsObject.ItemIsMovable | QtGui.QGraphicsObject.ItemIsFocusable | QtGui.QGraphicsObject.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(1)

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

    def input_pos(self):
        """
        Returns the default input connection center.
        """
        ipos = -self.height - self.bufferX*2 + self.height_collapsed + self.bufferY*2
        return QtCore.QPointF(self.boundingRect().left(), ipos/2)

    def output_pos(self):
        """
        Returns the default output connection center.
        """
        ipos = -self.height - self.bufferX*2 + self.height_collapsed + self.bufferY*2
        return QtCore.QPointF(self.boundingRect().right(), ipos/2)

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
                              self.width  + self.bufferX*2, self.height + self.bufferY*2)
    
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
        
    def paint(self, painter, option, widget):
        """
        Draw the node.
        """
        # position the label
        self.label.setPos(-self.width/2 + self.bufferX*2, -self.height/2 - self.bufferY)

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

        # draw the node background
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


        if self.debug_mode:
            debug_color = QtGui.QColor(*self.debug_color)
            painter.setBrush(QtCore.Qt.NoBrush)

            green_color = QtGui.QColor(0, 255, 0)
            painter.setPen(QtGui.QPen(green_color, 0.5, QtCore.Qt.SolidLine))
            painter.drawEllipse(self.output_pos(), 4, 4)

            yellow_color = QtGui.QColor(255, 255, 0)
            painter.setPen(QtGui.QPen(yellow_color, 0.5, QtCore.Qt.SolidLine))   
            painter.drawEllipse(self.input_pos(), 4, 4)
            
        self.input_widget.setPos(self.input_pos())
        self.output_widget.setPos(self.output_pos())

        self.input_widget.update()
        self.output_widget.update()

        self.label.update()


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
        self.radius         = 24
        self.draw_radius    = self.radius/6
        self.max_conn       = 1 

        # create a bbox that is larger than what we'll be drawing
        self.bounds         = QtGui.QGraphicsRectItem(-self.radius/2, -self.radius/2, self.radius, self.radius, self)
        self.bounds.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        # parent item should be on top, so that mouseEvents focus on parent
        self.bounds.setFlags(QtGui.QGraphicsObject.ItemStacksBehindParent)
        self.bounds.setZValue(-1)

        # debugging
        self.debug_mode     = False

        self.is_input       = is_input
        self.attribute      = kwargs.get('attribute', 'output')

        if self.is_input:
            self.attribute ='input'

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

    def boundingRect(self):
        return self.bounds.mapRectToParent(self.bounds.boundingRect())

    def shape(self):
        """
        Aids in selection.
        """
        path = QtGui.QPainterPath()
        polyon = QtGui.QPolygonF(self.boundingRect())
        path.addPolygon(polyon)
        return path

    def paint(self, painter, option, widget):
        """
        Draw the connection widget.
        """
        # DEBUG
        if self.debug_mode:
            conn_color = QtGui.QColor(175, 229, 168)
            if self.isInputConnection():
                conn_color = QtGui.QColor(255, 255, 190)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(conn_color, 0.5, QtCore.Qt.DashLine))
            painter.drawRect(self.boundingRect())

        self.setToolTip('%s.%s' % (self.dagnode.name, self.attribute))
        # background
        gradient = QtGui.QLinearGradient(0, -self.draw_radius, 0, self.draw_radius)
        grad = .5

        if self.isInputConnection():
            color = self.color

        # green
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
        painter.drawEllipse(QtCore.QPointF(0,0), self.draw_radius, self.draw_radius)
        #painter.drawEllipse(self.boundingRect())

    def isInputConnection(self):
        if self.is_input == True:
            return True
        return False

    def isOutputConnection(self):
        if self.is_input == True:
            return False
        return True


# edge class for connecting nodes
class EdgeWidget(QtGui.QGraphicsLineItem):

    adjustment = 5

    def __init__(self, source_item, dest_item, *args, **kwargs):
        QtGui.QGraphicsLineItem.__init__(self, *args, **kwargs)

        # The arrow that's drawn in the center of the line
        self.arrowhead      = QtGui.QPolygonF()
        self.color          = [224, 224, 224]

        self.source_item    = source_item
        self.dest_item      = dest_item

        self.arrow_size     = 12
        self.show_conn      = False             # show connection string
        self.multi_conn     = False             # multiple connections (future)
        self.conn_label     = None      
        self.edge_type      = 'bezier'

        self.source_point   = QtCore.QPointF(self.source_item.boundingRect().center())
        self.dest_point     = QtCore.QPointF(self.dest_item.boundingRect().center())
        self.center_point   = QtCore.QPointF()  # for bezier lines       
        self.bezier_path    = QtGui.QPainterPath()
        self.poly_line      = QtGui.QPolygonF()

        # debugging
        self.debug_mode     = False

        # control points of bezier
        self.c1             = QtCore.QPointF(0,0)
        self.c2             = QtCore.QPointF(0,0)

        self.cp1            = ControlPoint(self.source_point, self) 
        self.cp2            = ControlPoint(self.dest_point, self)

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setPen(QtGui.QPen(QtGui.QColor(*self.color), 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        
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
        Crude, but works.
        """
        line = self.getLine()
        path = QtGui.QPainterPath()
        path.moveTo(line.p1().x(), line.p1().y())

        # some very crude bezier math here
        x1 = line.p1().x()
        x2 = line.p2().x()

        y1 = line.p1().y()
        y2 = line.p2().y()

        # distances
        dx = x2 - x1
        dy = y2 - y1

        # bezier percentage
        t = .25

        # x coord
        cx1 = x1 + (dx * t)
        cx2 = x2 - (dx * t)

        # y coord
        cy1 = y1 - (dy * (t/4))
        cy2 = y2 + (dy * (t/4))

        # create the control points
        self.c1 = QtCore.QPointF(cx1, cy1)
        self.c2 = QtCore.QPointF(cx2, cy2)

        # create a polyline
        self.poly_line = QtGui.QPolygonF([line.p1(), self.c1, self.c2, line.p2()])
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

        # TODO: see if this works
        #brect = self.bezier_path.controlPointRect()
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
        """
        Displays a label with connection information.

         ** unused
        """
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

        draw_color = QtGui.QColor(*self.color)

        line = self.getLine()
        painter.setBrush(draw_color)
        epen = self.pen()
        epen.setColor(draw_color)
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

        # get the bezier line center
        
        self.bezier_path = self.getBezierPath()
        # calculate the arrowhead geometry
        if line.length() > 0.0:
            angle = math.acos(line.dx() / line.length())
            if self.edge_type == 'bezier':
                bline = QtCore.QLineF(self.bezier_path.pointAtPercent(0.47), self.bezier_path.pointAtPercent(0.53))  
                angle = math.acos(bline.dx() / bline.length())

            if line.dy() >= 0:
                angle = (math.pi * 2.0) - angle

            revArrow = -1

            center_point = self.getCenterPoint()
            end_point = self.getEndPoint()

            arrow_p1 = center_point + QtCore.QPointF(math.sin(angle + math.pi / 3.0) * self.arrow_size * revArrow,
                                        math.cos(angle + math.pi / 3.0) * self.arrow_size * revArrow)
            arrow_p2 = center_point + QtCore.QPointF(math.sin(angle + math.pi - math.pi / 3.0) * self.arrow_size * revArrow,
                                        math.cos(angle + math.pi - math.pi / 3.0) * self.arrow_size * revArrow)
            # clear the arrow
            self.arrowhead.clear()


            # set the polygon points
            for point in [center_point, arrow_p1, arrow_p2]:
                self.arrowhead.append(point)

            if line:                

                painter.drawPolygon(self.arrowhead)                
                painter.setBrush(QtCore.Qt.NoBrush)

                if self.edge_type == 'bezier':
                    painter.drawPath(self.bezier_path)

                if self.edge_type == 'polygon':
                    painter.drawLine(line)
                

                if self.debug_mode:

                    self.cp1.hide()
                    self.cp2.hide()

                    if self.edge_type == 'bezier':

                        self.cp1.show()
                        self.cp2.show()

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

                        self.cp1.setPos(self.mapToScene(QtCore.QPointF(self.c1.x(), self.c1.y())))
                        self.cp2.setPos(self.mapToScene(QtCore.QPointF(self.c2.x(), self.c2.y())))

                        # angle output
                        angle_str = '( %.2f deg )' % angle
                        a_pen = QtGui.QPen(QtCore.Qt.SolidLine)
                        a_pen.setColor(draw_color)
                        painter.setPen(a_pen)
                        painter.setBrush(QtGui.QBrush(draw_color))
                        angle_pt = QtCore.QPointF(self.getCenterPoint().x() + 10, self.getCenterPoint().y())
                        painter.drawText(angle_pt, angle_str)

                    # draw the center point
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    painter.setBrush(QtGui.QBrush(draw_color))
                    painter.drawEllipse(self.getCenterPoint(), 1.5, 1.5)

                    # draw the arrow p1 (blue)
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    p1_color= QtGui.QColor(130,130,255)
                    painter.setBrush(QtGui.QBrush(p1_color))
                    painter.drawEllipse(arrow_p1, 1.5, 1.5)

                    # draw the arrow p2 (pink)
                    painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                    p2_color= QtGui.QColor(237,171,204)
                    painter.setBrush(QtGui.QBrush(p2_color))
                    painter.drawEllipse(arrow_p2, 1.5, 1.5)


    def hoverEnterEvent(self, event):
        QtGui.QGraphicsLineItem.hoverEnterEvent(self, event)



class ControlPoint(QtGui.QGraphicsObject):
    """
    Bezier control point widget.
    """
    def __init__(self, center, parent=None, **kwargs):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.center_point   = center
        self.edge           = parent

        self.color          = kwargs.get('color', [225, 35, 35])
        self.radius         = kwargs.get('radius', 3.0)

        # debugging
        self.debug_mode     = False

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
        if self.debug_mode:
            painter.setPen(cp_pen)
            painter.setBrush(QtGui.QBrush(red_color))
            painter.drawEllipse(self.center_point, self.radius, self.radius)

            cp = self.mapToScene(self.center_point)
            self.setToolTip("(%.2f, %.2f)" % (cp.x(), cp.y()))


class NodeLabel(QtGui.QGraphicsObject):

    labelChanged = QtCore.Signal(str)

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)
        
        self.node           = parent
        self.dagnode        = parent.dagnode
        self.UUID           = parent.dagnode.UUID

        self.font           = 'Monospace'
        self.color          = [0, 0, 0]
        self._font_size     = 8
        self._font_bold     = False
        self._font_italic   = False
        self.width          = 80

        self.label = QtGui.QGraphicsTextItem(self.dagnode.name, self)
        self._document = self.label.document()

        # flags/signals
        self.label.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeNameChanged)
        
        self.rect_item = QtGui.QGraphicsRectItem(self.label.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.rect_item.stackBefore(self.label)
        #self.setZValue(2)
  
    def boundingRect(self):
        return self.label.boundingRect()
  
    def paint(self, painter, option, widget):
        """
        Draw the label.
        """
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self.font)
        qfont.setPointSize(self._font_size)
        qfont.setBold(self._font_bold)
        qfont.setItalic(self._font_italic)
        self.label.setFont(qfont)

        self.label.setDefaultTextColor(QtGui.QColor(*self.color))
        self.text = self.dagnode.name
    
        # add a drop shadow for the label
        self.tdropshd = QtGui.QGraphicsDropShadowEffect()
        self.tdropshd.setBlurRadius(6)
        self.tdropshd.setColor(QtGui.QColor(0,0,0,120))
        self.tdropshd.setOffset(1,2)
        self.label.setGraphicsEffect(self.tdropshd)

    def focusOutEvent(self, event):
        QtGui.QGraphicsObject.focusOutEvent(self, event)
        self.labelChanged()
        
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            print 'ooh'
            self.labelChanged()
        else:
            QtGui.QGraphicsObject.keyPressEvent(self, event)
        
    @QtCore.Slot()
    def nodeNameChanged(self):       
        new_name = self.text
        if new_name != self.dagnode.name:
            self.dagnode.name = new_name
            
        # re-center the label
        bounds = self.boundingRect()
        self.label.setPos(bounds.width()/2. - self.label.boundingRect().width()/2, 0)

    def mouseDoubleClickEvent(self, event):        
        QtGui.QGraphicsObject.mouseDoubleClickEvent(self, event)

    @property
    def text(self):
        return str(self._document.toPlainText())

    @text.setter
    def text(self, text):
        self._document.setPlainText(text)
        return self.text
