#!/usr/bin/env python
import sys
import math
import weakref
from PySide import QtCore, QtGui
from SceneGraph.core import log
from SceneGraph import options
from SceneGraph.ui import SceneNodesCommand


SCENEGRAPH_WIDGET_TYPE = 'dot'


class DotWidget(QtGui.QGraphicsObject): 

    Type           = QtGui.QGraphicsObject.UserType + 1
    doubleClicked  = QtCore.Signal()
    nodeChanged    = QtCore.Signal(object) 
    nodeDeleted    = QtCore.Signal(object)
    node_class     = 'dot' 

    def __init__(self, dagnode, parent=None):
        super(DotWidget, self).__init__(parent)

        # connect the dag node
        self.dagnode         = dagnode
        self.dagnode.connect_widget(self)
        
        # attributes
        self.bufferX         = 3
        self.bufferY         = 3
        self.pen_width       = 1.5                    # pen width for NodeBackground  

        # widget colors
        self._l_color        = [5, 5, 5, 255]         # label color
        self._p_color        = [10, 10, 10, 255]      # pen color (outer rim)
        self._s_color        = [0, 0, 0, 60]          # shadow color

        # widget globals
        self._debug          = False
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx

        # tags
        self._evaluate_tag   = False                  # indicates the node is set to "evaluate" (a la Houdini)
        
        # connections widget
        self.connections     = dict()

        # undo/redo snapshots
        self._current_pos    = QtCore.QPointF(0,0)
        self._data_snapshot  = None
        self._pos_snapshot   = None

        self.setHandlesChildEvents(False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

        # set node position
        self.setPos(QtCore.QPointF(self.dagnode.pos[0], self.dagnode.pos[1]))
        self.drawConnections()

    def close(self):
        """
        Cleanup and delete the node and children.
        """
        for conn_name in self.connections:
            conn_widget = self.connections.get(conn_name)
            if conn_widget:
                if conn_widget.scene():
                    conn_widget.scene().removeItem(conn_widget)

        if self is not None:
            if self.scene() is not None:
                self.scene().removeItem(self)

    def drawConnections(self, remove=False):
        """
        Update all of the connection widgets.

        params:
            remove (bool) - force connection removal & rebuild.
        """
        for conn_name in self.dagnode.connections:
            conn_dag = self.dagnode.get_connection(conn_name)
            conn_widget = DotConnection(self, conn_dag, conn_name)

            radius = float(conn_widget.radius/2)
            yoffset = radius
            yoffset += radius*0.75

            #print 'radius:  ', radius
            #print 'yoffset: ', yoffset

            #conn_center = conn_widget.mapToParent(self.center)
            
            if conn_widget.is_input:
                #conn_widget.transform().translate(0, -yoffset)
                conn_widget.setY(-yoffset)

            if conn_widget.is_output:
                #conn_widget.transform().translate(0, yoffset)
                conn_widget.setY(yoffset)

            # set the transformation origin to the Dot's center.
            conn_widget.setRotation(0)
            conn_widget.setTransformOriginPoint(conn_widget.mapFromParent(QtCore.QPointF(0,0)))
            self.connections[conn_name] = conn_widget
            conn_widget.setZValue(-1)
    
    def updateConnections(self, painter):
        """
        Update the connection widget's rotation values
        if they're connected to existing edges.
        """
        for conn_name in self.connections:
            conn_dag = self.dagnode.get_connection(conn_name)
            conn_widget = self.connections.get(conn_name)

            
            ### RECENTER AND TRANSLATE BASED ON RADIUS ###
            conn_widget.setRotation(0)
            conn_widget.setTransformOriginPoint(conn_widget.mapFromParent(QtCore.QPointF(0,0)))

            # update radius
            radius = float(self.dagnode.radius/2)
            yoffset = radius
            yoffset += radius*0.5

            #conn_center = conn_widget.mapToParent(self.center)            
            if conn_widget.is_input:
                conn_widget.setY(-yoffset)

            if conn_widget.is_output:
                conn_widget.setY(yoffset)

           
            # point the connection at the connected edge
            angle = '0.0'
            if conn_widget.connected_edges():
                edge = conn_widget.connected_edges()[0]
                eline = edge.getLine()

                label_xoffset = 20
                if conn_widget.isInputConnection():
                    p1 = self.mapFromScene(eline.p1())
                    p2 = conn_widget.boundingRect().center()
                    label_xoffset = -label_xoffset

                if conn_widget.isOutputConnection():
                    #p1 = self.center
                    p1 = conn_widget.boundingRect().center()
                    p2 = self.mapFromScene(eline.p2())              

                line = QtCore.QLineF(p1, p2)
                x1 = p1.x()
                x2 = p2.x()
                y1 = p1.y()
                y2 = p2.y()

                #angle=math.atan2(-(pos1[1]-pos2[1]), pos1[0]-pos2[0])
                t = math.atan2(-(y1-y2), x1-x2)
                x = math.degrees(t)
                angle = '%.2f' % x

                # remove the current label
                if conn_widget.debug_label:
                    if conn_widget.debug_label.scene():
                        conn_widget.debug_label.scene().removeItem(conn_widget.debug_label)

                # draw a label to show the angle
                if conn_widget._debug:
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.setPen(QtGui.QPen(conn_widget.bg_color, 0.5, QtCore.Qt.DashLine))
                    painter.drawLine(line)
                    qfont = QtGui.QFont("Monospace")
                    qfont.setPointSize(10)
                    conn_widget.debug_label = QtGui.QGraphicsTextItem(conn_widget)
                    conn_widget.debug_label.setFlag(QtGui.QGraphicsItem.ItemIgnoresTransformations)
                    conn_widget.debug_label.setFont(qfont)
                    conn_widget.debug_label.setDefaultTextColor(QtGui.QColor(conn_widget.bg_color))                
                    #conn_widget.debug_label.setPlainText('%.4f, %.4f' % (angle[0], angle[1]))
                    conn_widget.debug_label.setPlainText(angle)
                    conn_widget.debug_label.setX(label_xoffset)

                # rotate the connector
                conn_widget.setRotation(90+(float(angle)*-1) )

    #- Attributes ----
    @property
    def id(self):
        return self.dagnode.id
    
    @property
    def name(self):
        return self.dagnode.name

    @property
    def width(self):
        return float(self.dagnode.width)
        
    @width.setter
    def width(self, val):
        self.dagnode.width = val

    @property
    def height(self):
        return float(self.dagnode.base_height)

    @height.setter
    def height(self, val):
        self.dagnode.base_height = float(val)

    @property
    def color(self):
        """
        Return the 'node color' (background color)
        """
        return self.dagnode.color

    @color.setter
    def color(self, val):
        """
        Return the 'node color' (background color)
        """
        self.dagnode.color = val

    @property
    def is_enabled(self):
        return self.dagnode.enabled

    @is_enabled.setter
    def is_enabled(self, val):
        self.dagnode.enabled = val
        self.nodeChanged.emit(self)
        return self.dagnode.enabled

    @property
    def is_expanded(self):
        return False

    #- Events ----
    def dagnodeUpdated(self, *args, **kwargs):
        """
        Callback from the dag node.
        """
        pass

    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        if change == self.ItemPositionHasChanged:
            self.nodeChanged.emit(self)
            #self.updateConnections()
        return super(DotWidget, self).itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """
        translate Y: height_expanded - base_height/2
        """
        expanded = self.dagnode.expanded        
        QtGui.QGraphicsItem.mouseDoubleClickEvent(self, event)
        self.update()

    def mousePressEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        # store the node's current position
        self._current_pos  = self.pos()
        # store the node's current data
        self.scene().handler.evaluate()
        self._data_snapshot = self.scene().graph.snapshot()        

    def mouseReleaseEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        # Don't register undos for selections without moves
        if self.pos() != self._current_pos:
            snapshot = self.scene().graph.snapshot()
            self.scene().undo_stack.push(SceneNodesCommand(self._data_snapshot, snapshot, self.scene()))
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

    def boundingRect(self):
        """
        Returns a bounding rectangle for the node.

        returns:
            (QRectF) - node bounding rect.
        """
        w = self.width
        h = self.height
        bx = self.bufferX
        by = self.bufferY
        return QtCore.QRectF(-w/2 -bx, -h/2 - by, w + bx*2, h + by*2)

    def shape(self):
        """
        Create the shape for collisions.

        returns:
            (QPainterPath) - painter path object.
        """
        w = self.width + 4
        h = self.height + 4
        bx = self.bufferX
        by = self.bufferY
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-w/2, -h/2, w, h), 7, 7)
        return path

    #- SUBCLASS -----
    #- Global Properties ----
    @property
    def center(self):
        return self.boundingRect().center()

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        returns:
            (QColor) - widget background color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.is_hover:
            base_color = QtGui.QColor(*self.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.color)

    @property
    def pen_color(self):
        """
        Returns the widget pen color.

        returns:
            (QColor) - widget pen color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[40, 40, 40])
        if self.is_selected:
            return QtGui.QColor(*[251, 210, 91])
        return QtGui.QColor(*self._p_color)

    @property
    def label_color(self):
        """
        Returns the widget label color.

        returns:
            (QColor) - widget label color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[50, 50, 50])
        if self.is_selected:
            return QtGui.QColor(*[88, 0, 0])
        return QtGui.QColor(*self._l_color)

    @property
    def shadow_color(self):
        """
        Returns the node shadow color, as dictated
        by the dagnode.

        returns:
            (QColor) - shadow color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[35, 35, 35, 60])
        if self.is_selected:
            return QtGui.QColor(*[104, 56, 0, 60])
        return QtGui.QColor(*self._s_color)

    #- Connections -----
    @property
    def inputs(self):
        """
        Returns a list of dagnode input connections.

        returns:
            (list) - list of input connections.
        """
        return self.dagnode.inputs

    @property
    def outputs(self):
        """
        Returns a list of dagnode output connections.

        returns:
            (list) - list of output connections.
        """
        return self.dagnode.outputs

    def inputConnections(self):
        """
        Returns a list of input connection widgets.

        returns:
            (list) - list of input connection widgets.
        """
        return self.connections.get('input').values()

    def outputConnections(self):
        """
        Returns a list of output connection widgets.

        returns:
            (list) - list of output connection widgets.
        """
        return self.connections.get('output').values()

    def getInputConnection(self, name):
        """
        Returns a named connection.

        returns:
            (DotConnection) - connection widget.
        """
        if name not in self.inputs:
            return 
        return self.connections.get(name)

    def getOutputConnection(self, name):
        """
        Returns a named connection.

        returns:
            (DotConnection) - connection widget.
        """
        if name not in self.outputs:
            return 
        return self.connections.get(name)

    def getConnection(self, name):
        """
        Returns a named connection.

        returns:
            (DotConnection) - connection widget.
        """
        if name not in self.inputs and name not in self.outputs:
            return 

        if name in self.inputs:
            return self.connections.get(name)

        if name in self.outputs:
            return self.connections.get(name)

    def removeConnectionWidgets(self):
        """
        Remove all of the connection widgets.
        """
        for conn_name in self.connections:            
            conn_widget = self.connections.get(conn_name)
            if conn_widget:
                self.scene().removeItem(conn_widget)

    def paint(self, painter, option, widget):
        """
        Paint the widget container and all of the child widgets.
        """
        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        # setup colors
        bg_clr1 = self.bg_color
        bg_clr2 = bg_clr1.darker(150)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)
        gradient.setColorAt(0, bg_clr1)
        gradient.setColorAt(1, bg_clr2)

        # pen color
        pcolor = self.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.pen_width)
        qbrush = QtGui.QBrush(gradient)
        
        if self._debug:
            qpen = QtGui.QPen(QtGui.QColor(*[220, 220, 220]))
            qbrush = QtGui.QBrush(QtCore.Qt.NoBrush)

        painter.setPen(qpen)
        painter.setBrush(qbrush)
        painter.drawEllipse(self.boundingRect())

        self.updateConnections(painter)

    def setDebug(self, val):
        """
        Set the debug value of all child nodes.
        """
        vs = 'true'
        if not val:
            vs = 'false'
        if val != self._debug:
            log.info('setting "%s" debug: %s' % (self.dagnode.name, vs))
            self._debug = val
            for item in self.childItems():
                if hasattr(item, '_debug'):
                    item._debug = val

    @classmethod
    def ParentClasses(cls, p=None):
        """
        Return all subclasses.
        """
        base_classes = []
        cl = p if p is not None else cls.__class__
        for b in cl.__bases__:
            if b.__name__ != "object":
                base_classes.append(b.__name__)
                base_classes.extend(cls.ParentClasses(b))
        return base_classes



class DotConnection(QtGui.QGraphicsObject):
    
    Type                = QtGui.QGraphicsObject.UserType + 4
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeChanged         = QtCore.Signal(object)
    PRIVATE             = []
    node_class          = 'connection'

    def __init__(self, parent, conn_node, name, **kwargs):
        QtGui.QGraphicsObject.__init__(self, parent)

        # attribute params (kwargs):'default_value', 'is_user', 'is_locked', 
        # 'connection_type', 'value', 'is_required', 'is_connectable', 'is_private', 'max_connections'

        self.dagnode        = parent.dagnode
        self.dagconn        = conn_node

        # globals
        self.draw_radius    = self.dagnode.radius * 0.4
        self.pen_width      = self.draw_radius * 0.25
        self.radius         = self.draw_radius*4
        self.buffer         = 2.0
        self.node_shape     = 'circle'        
        self.is_proxy       = False                  # connection is a proxy for several connections

        # widget colors
        self._i_color       = [255, 255, 41, 255]    # input color
        self._o_color       = [0, 204, 0, 255]       # output color   
        self._s_color       = [0, 0, 0, 60]          # shadow color
        self._p_color       = [178, 187, 28, 255]    # proxy node color

        # connection state
        self._debug         = False
        self.is_selected    = False
        self.is_hover       = False
        self.debug_label    = QtGui.QGraphicsTextItem(self)
        self._angle         = '0'
        self._rotated       = False

        # dict: {(id, id) : edge widget} 
        self.connections    = dict()

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable | QtGui.QGraphicsItem.ItemStacksBehindParent)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)

    def __repr__(self):
        return 'DotConnection("%s")' % self.connection_name

    def __del__(self):
        print '# DotConnection "%s" deleted.' % self.name

    @property 
    def connection_name(self):
        return "%s.%s" % (self.dagnode.name, self.name)

    @property
    def name(self):
        return self.dagconn.name

    @property
    def node(self):
        return self.parentItem()

    @property
    def is_input(self):
        return self.dagconn.is_input

    @property
    def is_output(self):
        return self.dagconn.is_output

    @property
    def is_connected(self):
        return len(self.connections)  

    @property
    def orientation(self):
        return self.dagnode.orientation

    @property
    def is_enabled(self):
        return self.dagnode.enabled

    @property
    def is_expanded(self):
        return self.node.is_expanded

    @property
    def max_connections(self):
        return self.dagconn.max_connections

    def connected_edges(self):
        """
        Returns a list of connected edges.

        returns:
            (list) - list of connected edge widgets.
        """
        return self.connections.values()

    @property
    def is_connectable(self):
        """
        Returns true if the connection can take a connection.
         0 - unlimited connections
        """
        if self.max_connections == 0:
            return True
        return len(self.connections) < self.max_connections

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DotConnection.Type

    @property
    def bg_color(self):
        """
        Returns the connection background color.

        returns:
            (QColor) - widget background color.
        """
        color = self._i_color
        if self.is_output:
            color = self._o_color

        if not self.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.is_hover:
            if self.is_connectable:
                return QtGui.QColor(*[137, 204, 226])
            else:
                return QtGui.QColor(*[238, 46, 36])
        return QtGui.QColor(*color)

    @property
    def pen_color(self):
        """
        Returns the connection pen color.

        returns:
            (QColor) - widget pen color.
        """
        return self.bg_color.darker(250)

    def isInputConnection(self):
        """
        Returns true if the node is an input
        connection in the graph.

        returns:
            (bool) - widget is an input connection.
        """
        return self.dagconn.is_input

    def isOutputConnection(self):
        """
        Returns true if the node is an output
        connection in the graph.

        returns:
            (bool) - widget is an output connection.
        """
        return not self.dagconn.is_input

    #- Events ----
    def hoverLeaveEvent(self, event):
        """
        QGraphicsSceneHoverEvent.pos
        """
        if self.isSelected():
            #self.setSelected(False)
            pass
        QtGui.QGraphicsObject.hoverLeaveEvent(self, event)

    def mousePressEvent(self, event):
        """
         * debug
        """
        super(DotConnection, self).mousePressEvent(event)

    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        #print 'change: ', change
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged or change == QtGui.QGraphicsItem.ItemTransformChange or change == QtGui.QGraphicsItem.ItemTransformChange:
            self._rotated = False
        return super(DotConnection, self).itemChange(change, value)

    @property
    def parent_center(self):
        return self.mapFromParent(self.node.center)
    
    def boundingRect(self):
        """
        Return the bounding rect for the connection (plus selection buffer).
        """
        r = self.radius
        b = self.buffer
        return QtCore.QRectF(-r/2 - b, -r/2 - b, r + b*2, r + b*2)

    def drawRect(self):
        """
        Return the bounding rect for the connection.
        """
        r = self.draw_radius
        b = self.buffer
        return QtCore.QRectF(-r/2 - b, -r/2 - b, r + b*2, r + b*2)

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
        self.draw_radius  = self.dagnode.radius * 0.3
        self.radius       = self.draw_radius*4

        self.is_selected = False
        self.is_hover = False

        # set node selection/hover states
        if option.state & QtGui.QStyle.State_Selected:
            # if the entire node is selected, ignore
            if not self.node.isSelected():
                self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        self.setToolTip('%s.%s' % (self.dagnode.name, self.name))

        # background
        gradient = QtGui.QLinearGradient(0, -self.draw_radius, 0, self.draw_radius)
        gradient.setColorAt(0, self.bg_color)
        gradient.setColorAt(1, self.bg_color.darker(125))
        
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QBrush(self.pen_color), self.pen_width, QtCore.Qt.SolidLine))
        painter.setBrush(QtGui.QBrush(gradient))

        # draw the connector shape
        if self.node_shape == 'circle':
            painter.drawEllipse(QtCore.QPointF(0,0), self.draw_radius, self.draw_radius)
        
        elif self.node_shape == 'pie':
            # pie drawing
            start_angle = 16*90
            if self.isOutputConnection():
                start_angle = start_angle * -1
            painter.drawPie(self.drawRect(), start_angle, 16*180)


        # visualize the bounding rect if _debug attribute is true
        if self._debug:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(self.bg_color, 0.5, QtCore.Qt.DashLine))
            painter.drawRect(self.boundingRect())

            # center/transformation origin 
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            bg_color = self.bg_color
            bg_color.setAlpha(125)
            
            painter.setBrush(QtGui.QBrush(bg_color))

            # connection center point (blue)
            painter.drawEllipse(self.transformOriginPoint(), 2, 2)
           
            # dot node center (red)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(*[255, 0, 0, 150])))
            painter.drawEllipse(self.parent_center, 2, 2)

            self.setToolTip('rotation: %.2f' % self.rotation())

    def setDebug(self, value):
        """
        Set the widget debug mode.
        """
        if value != self._debug:
            self._debug = value


