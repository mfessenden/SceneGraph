#!/usr/bin/env python
import sys
import math
import weakref
from PySide import QtCore, QtGui
from SceneGraph.core import log
from SceneGraph import options
from SceneGraph.ui import Connection, SceneNodesCommand



SCENEGRAPH_WIDGET_TYPE = 'dot'


class DotWidget(QtGui.QGraphicsObject): 

    Type           = QtGui.QGraphicsObject.UserType + 1
    doubleClicked  = QtCore.Signal()
    nodeChanged    = QtCore.Signal(object) 
    nodeDeleted    = QtCore.Signal(object)  

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


    def buildConnections(self):
        """
        Build the nodes' connection widgets.
        """

        for input_name in self.dagnode.inputs:            
            # connection dag node
            input_dag = self.dagnode._inputs.get(input_name)
            input_widget = Connection(self, input_dag, input_name, **input_dag)
            self.connections['input'][input_name] = input_widget

        for output_name in self.dagnode.outputs:
            # connection dag node
            output_dag = self.dagnode._outputs.get(output_name)
            output_widget = Connection(self, output_dag, output_name, **output_dag)
            self.connections['output'][output_name] = output_widget

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
