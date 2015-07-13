#!/usr/bin/env python
from PySide import QtCore, QtGui
from SceneGraph.ui import NodeWidget


SCENEGRAPH_WIDGET_TYPE = 'dot'


class DotWidget(NodeWidget): 
    def __init__(self, dagnode, parent=None):
        super(DotWidget, self).__init__(dagnode, parent)

        self.label      = None
        self.background = NodeBackground(self)

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

        if self._render_effects:
            # background
            self.bgshd = QtGui.QGraphicsDropShadowEffect()
            self.bgshd.setBlurRadius(16)
            self.bgshd.setColor(self.shadow_color)
            self.bgshd.setOffset(8,8)
            self.background.setGraphicsEffect(self.bgshd)

        else:
            if self.background.graphicsEffect():
                self.background.graphicsEffect().deleteLater()
                self.bgshd = QtGui.QGraphicsDropShadowEffect()


class Connection(QtGui.QGraphicsObject):
    
    Type                = QtGui.QGraphicsObject.UserType + 4
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeChanged         = QtCore.Signal(object)
    PRIVATE             = []

    def __init__(self, parent, conn_node, name, **kwargs):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.dagnode        = parent.dagnode
        self.dagconn        = conn_node

        self.radius         = 5.0
        self.buffer         = 2.0
        self.is_selected    = False
        self.is_hover       = False

    def __repr__(self):
        return 'Connection("%s")' % self.connection_name

    @property 
    def connection_name(self):
        return "%s.%s" % (self.dagnode.name, self.name)

    @property
    def node(self):
        return self.parentItem()

    @property
    def is_input(self):
        return self.dagconn.is_input

    @is_input.setter
    def is_input(self, val):
        self.dagnode.is_input = val
        return self.dagconn.is_input

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
        return self.dagnode.expanded

    @property
    def max_connections(self):
        return self.dagconn.max_connections

    @property
    def is_connectable(self):
        """
        Returns true if the connection can take a connection.
         0 - unlimited connections
        """
        if self.max_connections == 0:
            return True
        return len(self.connections) < self.max_connections

    @property
    def id(self):
        if self.dagnode:
            return str(self.dagnode.id)
        return None

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return Connection.Type

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



class NodeBackground(QtGui.QGraphicsItem):
    def __init__(self, parent=None, scene=None):
        super(NodeBackground, self).__init__(parent, scene)

        self.dagnode = parent.dagnode
        self._debug  = False

    @property
    def node(self):
        return self.parentItem()

    @property 
    def pen_width(self):
        return self.node.pen_width

    def boundingRect(self):
        return self.node.boundingRect()

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

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(qpen)
        painter.drawEllipse(self.boundingRect())

        # line pen #1
        lcolor = self.node.pen_color
        lcolor.setAlpha(80)
        lpen = QtGui.QPen(lcolor)
        lpen.setWidthF(0.5)
