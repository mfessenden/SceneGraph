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
        self._font          = 'Monospace'
        self._font_size     = 8
        self._font_bold     = False
        self._font_italic   = False

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
        """
        return self.dagnode.color

    @color.setter
    def color(self, val):
        """
        Return the 'node color' (background color)
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
        #self.label.setTextEditable(not val)

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

            green_color = QtGui.QColor(0, 255, 0)
            painter.setPen(QtGui.QPen(green_color, 0.5, QtCore.Qt.SolidLine))
            painter.drawEllipse(self.output_pos, 4, 4)

            yellow_color = QtGui.QColor(255, 255, 0)
            painter.setPen(QtGui.QPen(yellow_color, 0.5, QtCore.Qt.SolidLine))   
            painter.drawEllipse(self.input_pos, 4, 4)

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
        QtGui.QGraphicsObject.__init__(self, *args, **kwargs)

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
        self._render_effects = True                   # enable fx

        self.weight          = weight
        self.arrow_size      = 8 
        self.show_conn       = False                  # show connection string
        self.multi_conn      = False                  # multiple connections (future)
        self.edge_type       = 'bezier'

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

        params:
            conn (Connection) - node connection widget.

        returns:
            (bool) - disconnection succeeded.
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
            return QtGui.QColor(*[200, 200, 200, 125])

        if self.is_selected:
            return QtGui.QColor(*self._h_color)

        if self.is_hover:
            return QtGui.QColor(*[109, 205, 255])

        return QtGui.QColor(*self._l_color)

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

    def getEndItem(self):
        return self.dest_item().parentItem()

    def getStartItem(self):
        return self.source_item().parentItem()

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

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)

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
                if draw_arrowhead:
                    painter.drawPolygon(arrowhead)    

                painter.setBrush(QtCore.Qt.NoBrush)

                if self.edge_type == 'bezier':
                    painter.drawPath(self.bezier_path)

                if self.edge_type == 'polygon':
                    painter.drawLine(line)
                
                # translate the center point
                #self.center_point.setPos(self.mapToScene(self.getCenterPoint()))


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
        qfont.setFamily("Menlo")
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
            qpen = QtGui.QPen(QtGui.QColor(*[220, 220, 220]))
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

