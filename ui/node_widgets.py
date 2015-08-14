#!/usr/bin/env python
import sys
import math
import weakref
from PySide import QtCore, QtGui
from SceneGraph.core import log
from SceneGraph import options
from . import commands


class NodeWidget(QtGui.QGraphicsObject):

    Type           = QtGui.QGraphicsObject.UserType + 1
    doubleClicked  = QtCore.Signal()
    nodeChanged    = QtCore.Signal(object) 
    nodeDeleted    = QtCore.Signal(object) 
    node_class     = 'dagnode'
      
    def __init__(self, dagnode, parent=None):
        super(NodeWidget, self).__init__(parent)

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

        # fonts
        self._font           = 'Monospace'
        self._font_size      = 8
        self._font_bold      = False
        self._font_italic    = False

        self._cfont          = 'Monospace'
        self._cfont_size     = 6
        self._cfont_bold     = False
        self._cfont_italic   = False

        # widget globals
        self._debug          = False
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx
        self._label_coord    = [0,0]                  # default coordiates of label

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

        # layers
        self.background = NodeBackground(self)
        self.label      = NodeLabel(self)   

        # signals/slots
        self.label.doubleClicked.connect(self.labelDoubleClickedEvent)

        # set node position
        self.setPos(QtCore.QPointF(self.dagnode.pos[0], self.dagnode.pos[1]))
        self.drawConnections()

    def close(self):
        """
        Cleanup and delete the node and children.
        """
        for item in [self.background, self.label]:
            if item is not None:
                if item.scene() is not None:
                    item.scene().removeItem(item)

        # clean up terminals
        for conn in self.connections.values():
            if conn is not None:
                if conn.scene() is not None:
                    conn.scene().removeItem(conn)

        if self is not None:
            if self.scene() is not None:
                self.scene().removeItem(self)

    def __str__(self):
        return '%s("%s")' % (self.__class__.__name__, self.dagnode.name)

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.dagnode.name)

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
        return float(self.dagnode.height)

    @height.setter
    def height(self, val):
        self.dagnode.height = val

    @property
    def color(self):
        """
        Return the 'node color' (background color)

        :returns: node rgba background color.
        :rtype: list
        """
        return self.dagnode.color

    @color.setter
    def color(self, val):
        """
        Set the 'node color' (background color) attributes.

        :param list color: rgba value.
        """
        self.dagnode.color = val

    @property
    def orientation(self):
        return self.dagnode.orientation

    @orientation.setter
    def orientation(self, val):
        self.dagnode.orientation = val
        return self.dagnode.orientation

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
        return len(self.inputs) > 1 or len(self.outputs) > 1 or self.dagnode.force_expand

    #- TESTING ---
    def labelDoubleClickedEvent(self):
        """
        Signal when the label item is double-clicked.

         * currently not using
        """
        val = self.label.is_editable

    #- Events ----
    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        if event.type == 'positionChanged':
            self.setPos(obs.pos[0], obs.pos[1])

    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        if change == self.ItemPositionHasChanged:
            self.nodeChanged.emit(self)
        return super(NodeWidget, self).itemChange(change, value)

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
            self.scene().undo_stack.push(commands.SceneNodesCommand(self._data_snapshot, snapshot, self.scene()))
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

    @property
    def label_rect(self):
        """
        Returns a bounding rectangle for the label item.

        returns:
            (QRectF) - label bounding rect.
        """
        return self.label.boundingRect()

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

    #- Global Properties ----
    @property
    def label_pos(self):
        return QtCore.QPointF(-self.width/2, -self.height/2 - self.bufferY)

    @property
    def input_pos(self):
        """
        Return the first input connection center point.

        returns:
            (QPointF) - input connection position.
        """
        rect = self.boundingRect()
        width = rect.width()
        height = rect.height()
        ypos = -rect.center().y()
        if self.is_expanded:         
            ypos = -(height / 2 ) +  self.dagnode.base_height * 2
        return QtCore.QPointF(-width/2, ypos)

    @property
    def output_pos(self):
        """
        Return the first output connection center point.

        returns:
            (QPointF) - output connection position.
        """
        rect = self.boundingRect()
        width = rect.width()
        height = rect.height()
        ypos = -rect.center().y()
        if self.is_expanded:         
            ypos = -(height / 2 ) +  self.dagnode.base_height * 2
        return QtCore.QPointF(width/2, ypos)

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        :returns: widget background color.
        :rtype: QtGui.QColor
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

        returns:  widget pen color.
        :rtype: QtGui.QColor
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

        returns:  widget label color.
        :rtype: QtGui.QColor
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

        returns:  widget shadow color.
        :rtype: QtGui.QColor
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
            (Connection) - connection widget.
        """
        if name not in self.inputs:
            return 
        return self.connections.get(name)

    def getOutputConnection(self, name):
        """
        Returns a named connection.

        returns:
            (Connection) - connection widget.
        """
        if name not in self.outputs:
            return 
        return self.connections.get(name)

    def getConnection(self, name):
        """
        Returns a named connection.

        returns:
            (Connection) - connection widget.
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

    def drawConnections(self, remove=False):
        """
        Update all of the connection widgets.

        params:
            remove (bool) - force connection removal & rebuild.
        """
        inp_start = self.input_pos
        out_start = self.output_pos

        inp_count = 0
        out_count = 0

        inp_y_offset = 0
        out_y_offset = 0

        for conn_name in self.dagnode.connections:
            conn_dag = self.dagnode.get_connection(conn_name)
            conn_widget = None

            if conn_name in self.connections:
                conn_widget = self.connections.get(conn_name)

                if remove:
                    # pop the current widget
                    self.connections.pop(conn_name)
                    self.scene().removeItem(conn_widget)


            if conn_widget is None:
                conn_widget = Connection(self, conn_dag, conn_name)
                self.connections[conn_name] = conn_widget

            if conn_widget.is_input:
                inp_y_offset = self.dagnode.base_height * inp_count
                conn_widget.setY(inp_start.y() + inp_y_offset)
                conn_widget.setX(inp_start.x())
                inp_count += 1

            if conn_widget.is_output:
                out_y_offset = self.dagnode.base_height * out_count
                conn_widget.setY(out_start.y() + out_y_offset)
                conn_widget.setX(out_start.x())
                out_count += 1

    def paint(self, painter, option, widget):
        """
        Paint the widget container and all of the child widgets.
        """
        if not self.label or not self.background:
            return

        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        # translate the label
        self.label.setPos(self.label_pos)        
        self.drawConnections()

        # set the tooltip to the current node's documentation string.
        self.setToolTip(self.dagnode.docstring)

        # render fx
        if self._render_effects:
            # background
            self.bgshd = QtGui.QGraphicsDropShadowEffect()
            self.bgshd.setBlurRadius(16)
            self.bgshd.setColor(self.shadow_color)
            self.bgshd.setOffset(8,8)
            self.background.setGraphicsEffect(self.bgshd)

            # label
            self.lblshd = QtGui.QGraphicsDropShadowEffect()
            self.lblshd.setBlurRadius(8)
            self.lblshd.setColor(self.shadow_color)
            self.lblshd.setOffset(4,4)
            self.label.setGraphicsEffect(self.lblshd)

        else:
            if self.background.graphicsEffect():
                self.background.graphicsEffect().deleteLater()
                self.bgshd = QtGui.QGraphicsDropShadowEffect()

            if self.label.graphicsEffect():
                self.label.graphicsEffect().deleteLater()
                self.lblshd = QtGui.QGraphicsDropShadowEffect()

        if self._debug:
            debug_color = QtGui.QColor(*[0, 0, 0])
            painter.setBrush(QtCore.Qt.NoBrush)

            # draw circles at the input/output positions
            green_color = QtGui.QColor(0, 255, 0)
            painter.setPen(QtGui.QPen(green_color, 0.5, QtCore.Qt.SolidLine))
            painter.drawEllipse(self.output_pos, 4, 4)

            yellow_color = QtGui.QColor(255, 255, 0)
            painter.setPen(QtGui.QPen(yellow_color, 0.5, QtCore.Qt.SolidLine))   
            painter.drawEllipse(self.input_pos, 4, 4)

            center_color = QtGui.QColor(*[164, 224, 255, 75])
            painter.setPen(QtGui.QPen(center_color, 0.5, QtCore.Qt.DashLine))

            # center point 
            h1 = QtCore.QPoint(-self.width/2, 0)
            h2 = QtCore.QPoint(self.width/2, 0)

            v1 = QtCore.QPoint(0, -self.height/2)
            v2 = QtCore.QPoint(0, self.height/2)

            hline = QtCore.QLine(h1, h2)
            vline = QtCore.QLine(v1, v2)

            painter.drawLine(hline)
            painter.drawLine(vline)


    def setDebug(self, value):
        """
        Set the debug value of all child nodes.
        """
        if value != self._debug:
            log.info('setting "%s" debug: %s' % (self.dagnode.name, value))
            self._debug = value
            for item in self.childItems():
                if hasattr(item, '_debug'):
                    item._debug = value

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


class EdgeWidget(QtGui.QGraphicsObject):
    
    Type          = QtGui.QGraphicsObject.UserType + 2
    adjustment    = 5
    nodeDeleted   = QtCore.Signal(object)
    node_class    = 'edge'
    """
    class EdgeWidget:

        Widget represention of an graph edge.

    params:
        edge (dict)              - nx edge: (id, id, {attributes})
        source_item (Connection) - source node connection
        dest_item (Connection)   - destination node connection
    """
    def __init__(self, edge, source_item, dest_item, weight=1.0, *args, **kwargs):
        QtGui.QGraphicsObject.__init__(self)

        #edge: (id, id, {attributes})
        # edge attributes
        self.src_id          = edge.get('src_id')
        self.dest_id         = edge.get('dest_id')
        self.edge_data       = edge                   # nx edge: (id, id, {attributes})  

        # globals
        self._l_color        = [224, 224, 224]        # line color
        self._p_color        = [10, 10, 10, 255]      # pen color (outer rim)
        self._h_color        = [90, 245, 60]          # highlight color
        self._s_color        = [0, 0, 0, 60]          # shadow color
        
        self.visible         = True
        self._debug          = False
        self.is_enabled      = True                   # node is enabled (will eval)  
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self.alt_modifier    = False                  # indicates that the alt key is pressed  
        self._render_effects = True                   # enable fx

        self.weight          = weight
        self.arrow_size      = 8.0
        self.cp_size         = 3.0                    # debug: control point size
        self.show_conn       = False                  # show connection string
        self.multi_conn      = False                  # multiple connections (future)
        self.edge_type       = edge.get('edge_type', 'bezier')

        # Connection widgets
        self.source_item     = weakref.ref(source_item, self.callback_source_deleted)
        self.dest_item       = weakref.ref(dest_item, self.callback_dest_deleted)

        # points
        self.source_point    = QtCore.QPointF(0,0)
        self.dest_point      = QtCore.QPointF(0,0)
        self.center_point    = QtCore.QPointF(0,0)  
        
        # geometry
        self.gline           = QtGui.QGraphicsLineItem(self)
        self.bezier_path     = QtGui.QPainterPath()
        self.poly_line       = QtGui.QPolygonF()

        # flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)
        self.setZValue(-1.0)


    def __str__(self):
        return 'Edge("%s")' % self.name

    def __repr__(self):
        return 'Edge("%s")' % self.name

    def __del__(self):
        self.breakConnections()

    def close(self):
        """
        Delete the edge and child items.
        """
        self.breakConnections()
        for item in [self.gline]:
            if item.scene() is not None:
                item.scene().removeItem(item)

        if self.scene() is not None:
            self.scene().removeItem(self)

    @property 
    def ids(self):
        """
        Return an easy-to-query attribute to check nx edges.

        returns:
            (tuple) - edge source id, edge destination id
        """
        return (self.src_id, self.dest_id)

    def connect_terminal(self, conn):
        """
        Connect the edge widget to the connection passed.

        params:
            conn (Connection) - node connection widget.

        returns:
            (bool) - connection succeeded.
        """
        # conn.connections (dict of edge id, edge widget)
        if not conn:
            log.warning('invalid connection.')
            return False

        if self.ids in conn.connections:
            log.warning('edge is already connected to: "%s"' % conn.connection_name)
            return False

        conn.connections[self.ids] = self
        return True

    def disconnect_terminal(self, conn):
        """
        Disconnect the edge widget from the connection.

        :param Connection conn: node connection widget.

        :returns: disconnection succeeded.
        :rtype: bool 
        """
        if not conn:
            log.warning('invalid connection.')
            return False

        if self.ids in conn.connections:
            conn.connections.pop(self.ids)
            return True
        return False

    def breakConnections(self):
        """
        Disconnect all connection objects.

        :returns: disconnection succeeded.
        :rtype: bool 
        """
        result = True
        if not self.disconnect_terminal(self.source_item()):
            result = False

        if not self.disconnect_terminal(self.dest_item()):
            result = False
        return result

    def callback_source_deleted(self):
        print 'Edge source deleted.'

    def callback_dest_deleted(self):
        print 'Edge destination deleted.'

    def setDebug(self, value):
        """
        Set the widget debug mode.
        """
        if value != self._debug:
            self._debug = value

    def listConnections(self):
        """
        Returns a list of connected nodes.

        returns:
            (tuple) - source Node widget, dest Node widget
        """
        return (self.source_item().node, self.dest_item().node)

    @property
    def source_node(self):
        """
        Returns the source node widget.

        returns:
            (NodeWidget) - source node.
        """
        return self.source_item().node

    @property
    def dest_node(self):
        """
        Returns the destination node widget.

        returns:
            (NodeWidget) - destination node.
        """
        return self.dest_item().node

    @property
    def source_connection(self):
        """
        returns:
            (str) - source connection name (ie: "node1.output").
        """
        if self.source_item():            
            if hasattr(self.source_item(),'dagnode'):
                return '%s.%s' % (self.source_item().dagnode.name, self.source_item().name)
        return '(source broken)'

    @property
    def dest_connection(self):
        """
        returns:
            (str) - destination connection name (ie: "node2.input").
        """
        if self.dest_item():            
            if hasattr(self.dest_item(), 'dagnode'):
                return '%s.%s' % (self.dest_item().dagnode.name, self.dest_item().name)
        return '(dest broken)'

    @property
    def name(self):
        """
        returns:
            (str) - connection string.
        """
        return "%s,%s" % (self.source_connection, self.dest_connection)

    @property
    def line_color(self):
        """
        Returns the current line color.
        """
        if self._debug:
            if self.is_selected:
                return QtGui.QColor(*[199, 255, 200, 125])

            if self.is_hover:
                return QtGui.QColor(*[199, 227, 255, 125])

            return QtGui.QColor(*[200, 200, 200, 125])

        if self.is_selected:
            return QtGui.QColor(*self._h_color)           

        if self.is_hover:
            if self.alt_modifier:
                return QtGui.QColor(*[164, 224, 255])
            return QtGui.QColor(*[109, 205, 255])

        return QtGui.QColor(*self._l_color)

    #- Events -----
    def hoverEnterEvent(self, event):
        QtGui.QGraphicsObject.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        self.alt_modifier = False
        QtGui.QGraphicsObject.hoverLeaveEvent(self, event)

    def hoverMoveEvent(self, event):
        QtGui.QGraphicsObject.hoverMoveEvent(self, event)

    def mouseMoveEvent(self, event):
        QtGui.QGraphicsObject.mouseMoveEvent(self, event)

    def boundingRect(self):
        """
        Create a bounding rect for the line.

         todo: see why self.bezier_path.controlPointRect()
         doesn't work.
        """
        extra = (self.gline.pen().width() + 100)  / 2.0
        line = self.getLine()
        p1 = line.p1()
        p2 = line.p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def getLine(self):
        """
        Return the line between two points.
        """
        p1 = self.source_item().sceneBoundingRect().center()
        p2 = self.dest_item().sceneBoundingRect().center()

        # offset the end point a few pixels
        p2 = QtCore.QPointF(p2.x(), p2.y())
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

        dx = math.fabs(dx)
        # bezier percentage
        t = .25

        # x coord
        cx1 = x1 + (dx * t)
        cx2 = x2 - (dx * t)

        # y coord
        cy1 = y1 - (dy * (t/4))
        cy2 = y2 + (dy * (t/4))

        # create the control points
        self.source_point = QtCore.QPointF(cx1, cy1)
        self.dest_point = QtCore.QPointF(cx2, cy2)

        # create a polyline
        self.poly_line = QtGui.QPolygonF([line.p1(), self.source_point, self.dest_point, line.p2()])
        path.cubicTo(self.source_point, self.dest_point, line.p2())
        #path.quadTo(line.p1(), line.p2())
        return path

    def getCenterPoint(self):
        """
        Returns the node center point.
        """ 
        line = self.getLine()
        centerX = (line.p1().x() + line.p2().x())/2
        centerY = (line.p1().y() + line.p2().y())/2
        return QtCore.QPointF(centerX, centerY)

    def getEndPoint(self):
        line = self.getLine()
        ep = line.p2()
        return QtCore.QPointF(ep.x(), ep.y())

    def getStartItem(self):
        """
        Returns the source item widget.

        returns:
            (object) - connection widget.
        """
        return self.source_item().parentItem()

    def getEndItem(self):
        """
        Returns the destination item widget.

        returns:
            (object) - connection widget.
        """
        return self.dest_item().parentItem()

    def shape(self):
        """
         * todo: add some adjustments to the line to make it more selectable.
        """
        path = QtGui.QPainterPath()
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(30)
        line = self.getLine()
        path.moveTo(line.p1())
        path.lineTo(line.p2())
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None):
        """
        Draw the line and arrow.
        """
        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True 

        if option.state & QtGui.QStyle.State_MouseOver:                 
            self.is_hover = True

        self.setToolTip(self.name)
        self.show_conn = False

        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.HighQualityAntialiasing)

        line = self.getLine()
        painter.setBrush(self.line_color)

        epen = self.gline.pen()
        epen.setColor(self.line_color)
        epen.setWidthF(float(self.weight))
        painter.setPen(epen)

        #self.cp.visible = False
        draw_arrowhead = True

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

            # build the arrowhead
            arrowhead = QtGui.QPolygonF()

            # set the polygon points
            for point in [center_point, arrow_p1, arrow_p2]:
                arrowhead.append(point)

            if line:
                if not self.alt_modifier:
                    if draw_arrowhead:
                        painter.drawPolygon(arrowhead)
                else:
                    arrow_rect = arrowhead.boundingRect()
                    painter.drawEllipse(arrow_rect.center(), 3,3)

                painter.setBrush(QtCore.Qt.NoBrush)

                if self.edge_type == 'bezier':
                    painter.drawPath(self.bezier_path)

                if self.edge_type == 'polygon':
                    painter.drawLine(line)
                
                # translate the center point
                #self.center_point.setPos(self.mapToScene(self.getCenterPoint()))
        if self._debug:
            if self.edge_type == 'bezier':
                painter.setPen(QtGui.QPen(QtGui.QColor(*[197, 255, 174, 80]), 0.5, QtCore.Qt.SolidLine))
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawPolyline(self.poly_line)
                # 145, 255, 161, 200
                painter.setPen(QtGui.QPen(QtGui.QColor(*[145, 255, 161, 200]), 1.5, QtCore.Qt.SolidLine))
                painter.setBrush(QtGui.QColor(*[145, 176, 255, 50]))
                painter.drawEllipse(self.source_point, self.cp_size, self.cp_size)
                painter.drawEllipse(self.dest_point, self.cp_size, self.cp_size)


class Connection(QtGui.QGraphicsObject):
    
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
        self.draw_radius    = 4.0
        self.pen_width      = 1.5
        self.radius         = self.draw_radius*4
        self.buffer         = 2.0
        self.node_shape     = 'circle'        
        self.draw_label     = False                  # draw a connection name label
        self.is_proxy       = False                  # connection is a proxy for several connections

        # widget colors
        self._i_color       = [255, 255, 41, 255]    # input color
        self._o_color       = [0, 204, 0, 255]       # output color   
        self._l_color       = [5, 5, 5, 200]         # label color
        self._s_color       = [0, 0, 0, 60]          # shadow color
        self._p_color       = [178, 187, 28, 255]    # proxy node color

        # connection state
        self._debug         = False
        self.is_selected    = False
        self.is_hover       = False

        # label
        self.label          = QtGui.QGraphicsSimpleTextItem(self)

        # dict: {(id, id) : edge widget} 
        self.connections    = dict()

        self.setAcceptHoverEvents(True)
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)

    def __repr__(self):
        return 'Connection("%s")' % self.connection_name

    def __del__(self):
        print '# Connection "%s" deleted.' % self.name

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
        return Connection.Type

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

    @property
    def label_color(self):
        """
        Returns the widget label color.

        returns:
            (QColor) - widget label color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[50, 50, 50, 128])
        if self.is_selected:
            return QtGui.QColor(*[88, 0, 0])
        return QtGui.QColor(*self._l_color)

    @property 
    def input_label_pos(self):
        """
        Returns a point for the label to lock to.
        """
        cw = self.draw_radius + (self.pen_width*2)
        x = cw
        h = float(self.label.boundingRect().height())
        y = -h/2
        return QtCore.QPointF(x, y)

    @property 
    def output_label_pos(self):
        """
        Returns a point for the label to lock to.
        """
        cw = self.draw_radius + (self.pen_width*2)
        lw = self.label.boundingRect().width()
        x = -(cw + lw)
        h = float(self.label.boundingRect().height())
        y = -h/2
        return QtCore.QPointF(x , y)

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

    def mouseClickEvent(self, event):
        """
         * debug
        """
        if event.button() == QtCore.Qt.RightButton:
            print '# connected edges: ', self.connections.values()
        event.accept()

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
        self.is_selected = False
        self.is_hover = False

        # set node selection/hover states
        if option.state & QtGui.QStyle.State_Selected:
            # if the entire node is selected, ignore
            if not self.node.isSelected():
                self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        self.setToolTip('%s.%s (%s)' % (self.dagnode.name, self.name, self.dagnode.get_attr(self.name).data_type))

        # background
        gradient = QtGui.QLinearGradient(0, -self.draw_radius, 0, self.draw_radius)
        gradient.setColorAt(0, self.bg_color)
        gradient.setColorAt(1, self.bg_color.darker(125))
        
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QBrush(self.pen_color), self.pen_width, QtCore.Qt.SolidLine))
        painter.setBrush(QtGui.QBrush(gradient))

        # draw a circle
        if self.node_shape == 'circle':
            painter.drawEllipse(QtCore.QPointF(0,0), self.draw_radius, self.draw_radius)
        elif self.node_shape == 'pie':
            # pie drawing
            start_angle = 16*90
            if self.isOutputConnection():
                start_angle = start_angle * -1
            painter.drawPie(self.drawRect(), start_angle, 16*180)
        
        # label
        label_color = self.label_color
        if self._debug:
            label_color = QtGui.QColor(*[170, 170, 170])
        
        # user attributes display in italics
        italic = False
        if self.dagnode.get_attr(self.name).user:
            italic = True

        label_font = QtGui.QFont(self.node._cfont, self.node._cfont_size, italic=italic)
        self.label.hide()
        if self.is_expanded:
            self.label.setBrush(label_color)
            self.label.setFont(label_font)
            self.label.show()
            self.label.setText(self.name)
            # set the positions
            if self.isInputConnection():
                self.label.setPos(self.input_label_pos)

            if self.isOutputConnection():
                self.label.setPos(self.output_label_pos)

            self.label.setToolTip(self.dagconn.desc)

        # visualize the bounding rect if _debug attribute is true
        if self._debug:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(self.bg_color, 0.5, QtCore.Qt.DashLine))
            painter.drawRect(self.boundingRect())

            if self.is_expanded:
                painter.setPen(QtGui.QPen(QtGui.QColor(*[140, 140, 140]), 0.5, QtCore.Qt.DashLine))
                self.label.setToolTip("(%.2f, %.2f)" % (self.label.pos().x(), self.label.pos().y()))
                rect = self.label.sceneBoundingRect()
                rect.moveTo(self.label.pos().x(), self.label.pos().y())
                painter.drawRect(rect)

    def setDebug(self, value):
        """
        Set the widget debug mode.
        """
        if value != self._debug:
            self._debug = value


#- Builtins ----


class DefaultWidget(NodeWidget):
    node_class     = 'default' 
    def __init__(self, dagnode, parent=None):
        super(DefaultWidget, self).__init__(dagnode, parent)



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
    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        if event.type == 'positionChanged':
            self.setPos(obs.pos[0], obs.pos[1])

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




class NoteWidget(QtGui.QGraphicsObject): 

    Type           = QtGui.QGraphicsObject.UserType + 1
    doubleClicked  = QtCore.Signal()
    nodeChanged    = QtCore.Signal(object) 
    nodeDeleted    = QtCore.Signal(object)
    node_class     = 'note' 

    def __init__(self, dagnode, parent=None):
        super(NoteWidget, self).__init__(parent)

        # connect the dag node
        self.dagnode         = dagnode
        self.dagnode.connect_widget(self)
        
        # attributes        
        self.corner_size     = 20
        self.bufferX         = 3
        self.bufferY         = 3
        self.pen_width       = 1.5                            # pen width for NoteBackground  
        self.handle_size     = 6                              # size of the resize handle
          
        # fonts
        self._font           = 'SansSerif'
        self._font_size      = self.dagnode.font_size
        self._font_bold      = False
        self._font_italic    = False

        # widget colors
        self._l_color        = [5, 5, 5, 255]                 # label color
        self._p_color        = [10, 10, 10, 255]              # pen color (outer rim)
        self._s_color        = [0, 0, 0, 60]                  # shadow color

        # widget globals
        self._debug          = False
        self.is_selected     = False                          # indicates that the node is selected
        self.is_hover        = False                          # indicates that the node is under the cursor
        self.handle_selected = False                          # indicates that the node handle is selected
        self._render_effects = True                           # enable fx

        # temp resizing attributes
        self.top_left        = ()
        self.btm_right       = ()
        self.min_width       = 75                             # widget minimum size  
        self.min_height      = 60                             # widget minimum size  

        # label
        self._evaluate_tag   = False                          # indicates the node is set to "evaluate" (a la Houdini)
        self.label           = NodeText(self)
        self.resize_handle   = QtGui.QGraphicsRectItem(self)
        self.center_label    = QtGui.QGraphicsTextItem(self)  # debug  

        # undo/redo snapshots
        self._current_pos    = QtCore.QPointF(0,0)
        self._data_snapshot  = None
        self._pos_snapshot   = None

        self.setHandlesChildEvents(True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

        # set node position
        self.setPos(QtCore.QPointF(self.dagnode.pos[0], self.dagnode.pos[1]))

    def close(self):
        """
        Cleanup and delete the node and children.
        """
        if self is not None:
            if self.scene() is not None:
                self.scene().removeItem(self)
   
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
    def hoverMoveEvent(self,event):
        QtGui.QGraphicsItem.hoverMoveEvent(self, event)
        scene_pos = event.scenePos()
        if self.handle_selected:
            if not self.handleRect().contains(self.mapFromScene(scene_pos)):
                self.handle_selected = False

    def hoverLeaveEvent(self,event):
        self.handle_selected = False
        QtGui.QGraphicsItem.hoverLeaveEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Scale the node as the resize handle is dragged.
        """
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

        if self.handle_selected:
            scene_pos = event.scenePos()

            # if there's no stashed value, set it
            if not self.top_left:
                # map scene coordinates to local
                top_left = self.mapToScene(self.boundingRect().topLeft())
                self.top_left = (top_left.x(), top_left.y())

            self.btm_right = (scene_pos.x(), scene_pos.y())
            # create a temporary rectangle with the current selection
            rect = QtCore.QRectF(QtCore.QPointF(*self.top_left), QtCore.QPointF(*self.btm_right))    
            self.dagnode.width = abs(rect.width())
            self.dagnode.height = abs(rect.height())

    def mousePressEvent(self, event):
        """
        Set the handle selection state if the handle widget is clicked.
        """
        self.handle_selected = False
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        scene_pos = event.scenePos()
        if self.handleRect().contains(self.mapFromScene(scene_pos)):
            self.handle_selected = True

    def mouseReleaseEvent(self, event):
        """
        Reset resize values when the mouse is released.
        """
        self.top_left = []
        self.btm_right = []
        #cpos = self.mapToScene(self.boundingRect().center())

        if self.handle_selected:
            self.handle_selected = False
            #self.setPos(cpos.x(), cpos.y())            
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

        # tidy up
        if self.dagnode.width < self.min_width:
            self.dagnode.width = self.min_width

        if self.dagnode.height < self.min_height:
            self.dagnode.height = self.min_height

    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        if event.type == 'positionChanged':
            self.setPos(obs.pos[0], obs.pos[1])

    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        if change == self.ItemPositionHasChanged:
            self.nodeChanged.emit(self)
            #self.updateConnections()
        return super(NoteWidget, self).itemChange(change, value)

    def boundingRect(self):
        """
        Returns a bounding rectangle for the node.

        returns:
            (QRectF) - node bounding rect.
        """
        if self.top_left and self.btm_right:
            top_left = self.mapFromScene(*self.top_left)
            btm_right = self.mapFromScene(*self.btm_right)
            return QtCore.QRectF(top_left, btm_right)

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

    def getNoteShape(self):
        """
        Returns a note-shaped polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - note-shaped polygon
        """
        rect = self.boundingRect()

        p1 = rect.topLeft()
        p2 = rect.topRight()
        p3 = rect.topRight()
        p4 = rect.bottomRight()
        p5 = rect.bottomLeft()

        p2.setX(p2.x() - self.corner_size)
        p3.setY(p2.y() + self.corner_size)
        return QtGui.QPolygonF([p1, p2, p3, p4, p5, p1])

    def getCornerShape(self):
        """
        Returns a corner polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - corner polygon
        """
        rect = self.boundingRect()

        p1 = rect.topRight() # need as p1
        p2 = rect.topRight() # need as p2

        p1.setX(p1.x() - self.corner_size)
        p2.setY(p1.y() + self.corner_size)

        p3 = QtCore.QPointF(p1.x(), p2.y())
        return QtGui.QPolygonF([p1, p2, p3, p1])

    def handleRect(self):
        """
        * testing
        """
        rect = self.boundingRect()
        hbuffer = self.handle_size/3.0
        p1 = rect.bottomRight()
        p2 = QtCore.QPointF(abs(p1.x()) - (self.handle_size + hbuffer), p1.y())
        topLeft = QtCore.QPointF(p2.x(), p2.y() - (self.handle_size + hbuffer))
        return QtCore.QRectF(topLeft, QtCore.QSize(self.handle_size, self.handle_size))

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

        # draw resize handle
        handle_color = self.bg_color
        handle_color.setAlpha(75)
        if self.handle_selected:
            handle_color = handle_color.lighter(250)
        hpen_color = handle_color.darker(200)
        hpen_color.setAlpha(125)
        self.resize_handle.setPen(QtGui.QPen(hpen_color))
        self.resize_handle.setBrush(QtGui.QBrush(handle_color))
        
        self.label.setPos(self.label_pos)
        self.label.label.setTextWidth(self.width * 0.8)

        # setup colors
        bg_color1 = self.bg_color
        bg_color2 = bg_color1.darker(150)
        bg_color3 = self.bg_color.lighter(50)
        bg_color3.setAlpha(125)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)
        gradient.setColorAt(0, bg_color1)
        gradient.setColorAt(1, bg_color2)

        # pen color
        pcolor = self.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.pen_width)

        cpen = QtGui.QPen(QtCore.Qt.NoPen)

        # background brush
        qbrush = QtGui.QBrush(gradient)
        # corner brush
        cbrush = QtGui.QBrush(bg_color2.darker(80))
        # handle brush
        hbrush = QtGui.QBrush(bg_color3)

        if self._debug:
            qpen = QtGui.QPen(QtGui.QColor(*[220, 220, 220]))
            qpen.setStyle(QtCore.Qt.DashLine)
            qpen.setWidthF(0.5)

            cpen = QtGui.QPen(QtGui.QColor(*[0, 0, 255]))
            cpen.setStyle(QtCore.Qt.DashLine)
            cpen.setWidthF(0.5)

            qbrush = QtGui.QBrush(QtCore.Qt.NoBrush)
            cbrush = QtGui.QBrush(QtCore.Qt.NoBrush)
            painter.drawRect(self.boundingRect())

            center_color = QtGui.QColor(*[164, 224, 255, 75])
            painter.setPen(QtGui.QPen(center_color, 0.5, QtCore.Qt.DashLine))

            # center point 
            h1 = QtCore.QPoint(-self.width/2, 0)
            h2 = QtCore.QPoint(self.width/2, 0)

            v1 = QtCore.QPoint(0, -self.height/2)
            v2 = QtCore.QPoint(0, self.height/2)

            hline = QtCore.QLine(h1, h2)
            vline = QtCore.QLine(v1, v2)

            painter.drawLine(hline)
            painter.drawLine(vline)

        # shapes
        note_shape = self.getNoteShape()
        corner_shape = self.getCornerShape()
        corner_shape.translate(-0.5, 0.5)
        painter.setPen(qpen)
        painter.setBrush(qbrush)

        # draw background
        if not self.handle_selected:
            painter.drawPolygon(note_shape)
        else:
            painter.drawRect(self.boundingRect())
        painter.setBrush(cbrush)
        painter.setPen(cpen)

        # draw corner
        if not self.handle_selected:
            painter.drawPolygon(corner_shape)

        self.center_label.hide()
        cpos = self.mapToScene(self.boundingRect().center())

        # if the handle is selected, update the position
        if self.handle_selected:
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(*[200, 200, 200, 255])))
            clabel = '%.2f, %.2f' % (cpos.x(), cpos.y())
            self.center_label.setPlainText(clabel)
            
            # show the center coordinates if we're in debug mode
            if self._debug:
                self.center_label.show()
                self.center_label.setPos(0,0)
            self.setPos(cpos.x(),cpos.y())
        self.resize_handle.setRect(self.handleRect())
            
    def setDebug(self, val):
        """
        Set the debug value of all child nodes.
        """
        if val != self._debug:
            self._debug = val
            #self.background.setDebug(val)
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


    #- NOTEWIDGET SPECIFIC ----
    @property
    def label_pos(self):
        return QtCore.QPointF(-self.width/2, -self.height/2 - self.bufferY)



#- Sub-Widgets ----

class NodeLabel(QtGui.QGraphicsObject):
    
    doubleClicked     = QtCore.Signal()
    labelChanged      = QtCore.Signal()
    clicked           = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.dagnode        = parent.dagnode
        self._debug         = False

        self.label = QtGui.QGraphicsTextItem(self.dagnode.name, self)
        self.label.node = parent
        self._document = self.label.document()

        self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeNameChanged)

        # set flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        self.label.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.label.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        # bounding shape
        self.rect_item = QtGui.QGraphicsRectItem(self.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.rect_item.setPen(QtGui.QPen(QtGui.QColor(125,125,125)))        
        self.rect_item.pen().setStyle(QtCore.Qt.DashLine)
        self.rect_item.stackBefore(self.label)
        self.setHandlesChildEvents(False)

    @QtCore.Slot()
    def nodeNameChanged(self):
        """
        Runs when the node name is changed.
        """      
        new_name = self.text
        if new_name != self.dagnode.name:
            self.dagnode.name = new_name
            
        # re-center the label
        bounds = self.boundingRect()
        self.label.setPos(bounds.width()/2. - self.label.boundingRect().width()/2, 0)

    @property
    def is_editable(self):
        return self.label.textInteractionFlags() == QtCore.Qt.TextEditorInteraction

    def keyPressEvent(self, event):
        print '# NodeLabel: keyPressEvent'
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.nodeNameChanged()
        else:
            QtGui.QGraphicsObject.keyPressEvent(self, event)

    @property
    def node(self):
        return self.parentItem()

    def boundingRect(self):
        try:
            return self.label.boundingRect()
        except:
            return QtCore.QRectF(0, 0, 0, 0)

    @property
    def text(self):
        return str(self._document.toPlainText())

    @text.setter
    def text(self, text):
        self._document.setPlainText(text)
        return self.text

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
        Draw the label.
        """
        label_color = self.node.label_color
        label_italic = self.node._font_italic

        # diabled fonts always render italicized
        if not self.node.is_enabled:
            label_italic = True

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self.node._font)
        qfont.setPointSize(self.node._font_size)
        qfont.setBold(self.node._font_bold)
        qfont.setItalic(label_italic)
        #qfont.setFamily("Menlo")
        self.label.setFont(qfont)

        # debug
        if self._debug:
            label_color = QtGui.QColor(*[200, 200, 200])
            qpen = QtGui.QPen(QtGui.QColor(125,125,125))
            qpen.setWidthF(0.5)
            qpen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(qpen)
            painter.drawPolygon(self.boundingRect())

        self.label.setDefaultTextColor(label_color)
        self.text = self.node.dagnode.name


class NodeBackground(QtGui.QGraphicsItem):
    def __init__(self, parent=None, scene=None):
        super(NodeBackground, self).__init__(parent, scene)

        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        self.dagnode = parent.dagnode
        self._debug  = False

    @property
    def node(self):
        return self.parentItem()

    @property 
    def pen_width(self):
        return self.node.pen_width

    def boundingRect(self):
        if self.node:
            return self.node.boundingRect()
        return QtCore.QRectF(0,0,0,0)

    def labelLine(self, offset=0):
        """
        Draw a line for the node label area
        """
        p1 = self.boundingRect().topLeft()
        p1.setX(p1.x() + self.node.bufferX)
        p1.setY(p1.y() + self.node.bufferY*7)

        p2 = self.boundingRect().topRight()
        p2.setX(p2.x() - self.node.bufferX)
        p2.setY(p2.y() + self.node.bufferY*7)

        if offset:
            p1.setY(p1.y() + offset)
            p2.setY(p2.y() + offset)

        return QtCore.QLineF(p1, p2)

    def paint(self, painter, option, widget):
        """
        Paint the node background.
        """
        # setup colors
        bg_clr1 = self.node.bg_color
        bg_clr2 = bg_clr1.darker(150)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.node.height/2, 0, self.node.height/2)
        gradient.setColorAt(0, bg_clr1)
        gradient.setColorAt(1, bg_clr2)

        # pen color
        pcolor = self.node.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.pen_width)
        qbrush = QtGui.QBrush(gradient)
        
        if self._debug:
            pcolor = QtGui.QColor(*[220, 220, 220])
            if self.node.is_selected:
                pcolor = QtGui.QColor(*[255, 180, 74])
            qpen = QtGui.QPen(pcolor)
            qbrush = QtGui.QBrush(QtCore.Qt.NoBrush)

        painter.setPen(qpen)
        painter.setBrush(qbrush)
        painter.drawRoundedRect(self.boundingRect(), 7, 7)

        # line pen #1
        lcolor = self.node.pen_color
        lcolor.setAlpha(80)
        lpen = QtGui.QPen(lcolor)
        lpen.setWidthF(0.5)

        if self._debug:
            lpen.setColor(QtGui.QColor(*[200, 200, 200, 150]))

        if self.dagnode.expanded:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(lpen)

            label_line = self.labelLine()
            painter.drawLine(label_line)


class NodeText(QtGui.QGraphicsObject):
    
    doubleClicked     = QtCore.Signal()
    labelChanged      = QtCore.Signal()
    clicked           = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.dagnode        = parent.dagnode
        self._debug         = False

        self.label = QtGui.QGraphicsTextItem(self.dagnode.doc_text, self)
        self.label.node = parent
        self._document = self.label.document()

        #self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeTextChanged)

        # set flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        self.label.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.label.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        # bounding shape
        self.rect_item = QtGui.QGraphicsRectItem(self.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.rect_item.setPen(QtGui.QPen(QtGui.QColor(125,125,125)))        
        self.rect_item.pen().setStyle(QtCore.Qt.DashLine)
        self.rect_item.stackBefore(self.label)
        self.setHandlesChildEvents(False)

    @QtCore.Slot()
    def nodeTextChanged(self):
        """
        Runs when the node name is changed.
        """      
        new_name = self.text
        if new_name != self.dagnode.doc_text:
            self.dagnode.doc_text = new_name
            
        # re-center the label
        bounds = self.boundingRect()
        self.label.setPos(bounds.width()/2. - self.label.boundingRect().width()/2, 0)

    @property
    def is_editable(self):
        return self.label.textInteractionFlags() == QtCore.Qt.TextEditorInteraction

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.nodeTextChanged()
        else:
            QtGui.QGraphicsObject.keyPressEvent(self, event)

    @property
    def node(self):
        return self.parentItem()

    def boundingRect(self):
        try:
            return self.label.boundingRect()
        except:
            return QtCore.QRectF(0, 0, 0, 0)

    @property
    def text(self):
        return str(self._document.toPlainText())

    @text.setter
    def text(self, text):
        self._document.setPlainText(text)
        return self.text

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
        Draw the label.
        """
        label_color = self.node.label_color
        label_italic = self.node._font_italic

        # diabled fonts always render italicized
        if not self.node.is_enabled:
            label_italic = True

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self.node._font)
        qfont.setPointSize(self.dagnode.font_size)
        qfont.setBold(self.node._font_bold)
        qfont.setItalic(label_italic)
        self.label.setFont(qfont)

        # debug
        if self._debug:
            label_color = QtGui.QColor(*[200, 200, 200])
            qpen = QtGui.QPen(QtGui.QColor(125,125,125))
            qpen.setWidthF(0.5)
            qpen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(qpen)
            painter.drawPolygon(self.boundingRect())

        self.label.setDefaultTextColor(label_color)
        self.text = self.node.dagnode.doc_text




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




class NoteBackground(QtGui.QGraphicsObject):

    def __init__(self, parent=None):
        super(NoteBackground, self).__init__(parent)

        self.dagnode = parent.dagnode
        self._debug  = False

        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

    @property
    def node(self):
        return self.parentItem()

    @property 
    def pen_width(self):
        return self.node.pen_width

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        :returns: widget background color.
        :rtype: QtGui.QColor
        """
        if not self.node.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.node.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.node.is_hover:
            base_color = QtGui.QColor(*self.dagnode.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.dagnode.color)

    @property
    def pen_color(self):
        """
        Returns the widget pen color.

        :returns: widget pen color.
        :rtype: QtGui.QColor
        """
        if not self.node.is_enabled:
            return QtGui.QColor(*[40, 40, 40])
        if self.node.is_selected:
            return QtGui.QColor(*[251, 210, 91])
        return QtGui.QColor(*self.node._p_color)

    def boundingRect(self):
        if self.node:
            return self.node.boundingRect()
        return QtCore.QRectF(0,0,0,0)

    def getNoteShape(self):
        """
        Returns a note-shaped polygon (based on the current boundingRect)

        :returns: note-shaped polygon
        :rtype: QtCore.QPolygonF
        """
        rect = self.boundingRect()
        corner_w = rect.width() - (rect.width() * 0.8)

        p1 = rect.topLeft()
        p2 = rect.topRight()
        p3 = rect.topRight()
        p4 = rect.bottomRight()
        p5 = rect.bottomLeft()

        p2.setX(p2.x() - corner_w)
        p3.setY(p2.y() + corner_w)
        return QtGui.QPolygonF([p1, p2, p3, p4, p5, p1])

    def getCornerShape(self):
        """
        Returns a corner polygon (based on the current boundingRect)

        :returns: corner polygon
        :rtype: QtCore.QPolygonF
        """
        rect = self.boundingRect()
        corner_w = rect.width() - (rect.width() * 0.8)
        corner_h = rect.height() - (rect.height() * 0.8)

        p1 = rect.topRight() # need as p1
        p2 = rect.topRight() # need as p2

        p1.setX(p1.x() - corner_w)
        p2.setY(p1.y() + corner_w)

        p3 = p2
        p3.setX(p2.x() - corner_w)
        return QtGui.QPolygonF([p1, p2, p3, p1])

    def paint(self, painter, option, widget):
        """
        Paint the node background.
        """
        # setup colors
        bg_color1 = self.node.bg_color
        bg_color2 = bg_color1.darker(150)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.node.height/2, 0, self.node.height/2)
        gradient.setColorAt(0, bg_color1)
        gradient.setColorAt(1, bg_color2)

        # pen color
        pcolor = self.node.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.node.pen_width)

        qbrush = QtGui.QBrush(gradient)
        cbrush = QtGui.QBrush(QtGui.QColor(*[225, 189, 10, 55]))

        painter.setPen(qpen)
        painter.setBrush(qbrush)

        painter.drawPolygon(self.getNoteShape())

    def setDebug(self, val):
        """
        Set the debug value of all child nodes.
        """
        if val != self._debug:
            self._debug = val


class ResizeHandle(QtGui.QGraphicsObject): 

    clicked  = QtCore.Signal()

    def __init__(self, parent=None):
        super(ResizeHandle, self).__init__(parent)

        self.dagnode         = parent.dagnode
        self.width           = 5.0

        self._debug          = False
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx
        
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        
        self.setAcceptedMouseButtons(True)
        self.setAcceptsHoverEvents(True)

    @property
    def node(self):
        return self.parentItem()

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
            return QtGui.QColor(*[255, 183, 44, 125])

        if self.is_hover:
            base_color = QtGui.QColor(*self.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.color)

    def boundingRect(self):
        try:
            return self.node.boundingRect()
        except:
            return QtCore.QRectF(0, 0, 0, 0) 

    def mousePressEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        self.clicked.emit()
        QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

    def getShape(self):
        """
        Returns a shape based on the parent's boundingRect

        returns:
            (QPolygonF) - qquare polygon
        """
        rect = self.boundingRect()

        p1 = rect.bottomRight()
        p2 = QtCore.QPointF(p1.x() - self.width, p1.y())
        p3 = QtCore.QPointF(p2.x(), p2.y() - self.width)
        p4 = QtCore.QPointF(p3.x() + self.width, p3.y())
        return QtGui.QPolygonF([p1, p2, p3, p4, p1])

    def paint(self, painter, option, widget):
        """
        Paint the node background.
        """
        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        # setup colors
        bg_color = self.bg_color.darker(100)
        qpen = QtGui.QPen(QtCore.Qt.NoPen)
        qbrush = QtGui.QBrush(bg_color)

        painter.setPen(qpen)
        painter.setBrush(qbrush)

        shape = self.getShape()
        shape.translate(-2, -2)
        painter.drawPolygon(shape)