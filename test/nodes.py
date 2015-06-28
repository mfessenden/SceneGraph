#!/usr/bin/env python
import sys
from PySide import QtCore, QtGui


"""
pyqtgraph:

    - Node = QObject
        Node.graphicsItem = QGraphicsObject

    def close(self):
        self.disconnectAll()
        self.clearTerminals()
        item = self.graphicsItem()
        if item.scene() is not None:
            item.scene().removeItem(item)
        self._graphicsItem = None
        w = self.ctrlWidget()
        if w is not None:
            w.setParent(None)
        #self.emit(QtCore.SIGNAL('closed'), self)
        self.sigClosed.emit(self)

My Node:
    Requirements:
        - needs to send signals from label
        - needs to have connections

Node.setHandlesChildEvents(False)

"""

class Node(QtGui.QGraphicsObject):

    Type = QtGui.QGraphicsObject.UserType + 1
    doubleClicked     = QtCore.Signal()
    nodeChanged       = QtCore.Signal(object)  

    def __init__(self, dagnode, parent=None):
        super(Node, self).__init__(parent)

        self.dagnode         = dagnode
        self.dagnode._widget = self
        
        # attributes
        self.bufferX         = 3
        self.bufferY         = 3
        self.orientation     = 'horizontal'           # connect on sides/top    

        self._l_color        = [5, 5, 5, 255]         # label color
        self._p_color        = [10, 10, 10, 255]      # pen color (outer rim)
        self._s_color        = [0, 0, 0, 60]          # shadow color

        # globals
        self._debug          = False
        self.is_enabled      = True                   # node is enabled (will eval)  
        self.is_expanded     = False                  # node is expanded 
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx

        self._label_coord    = [0,0]                  # default coordiates of label

        self.setHandlesChildEvents(False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

        # layers
        self.background = NodeBackground(self)
        self.label = NodeLabel(self)   

        # signals/slots
        self.label.doubleClicked.connect(self.labelDoubleClickedEvent)

        # set node position
        self.setPos(QtCore.QPointF(self.dagnode.pos[0], self.dagnode.pos[1]))

    #- Attributes ----
    @property
    def width(self):
        return self.dagnode.width
        
    @width.setter
    def width(self, val):
        self.dagnode.width = val

    @property
    def height(self):
        return self.dagnode.height

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

    #- TESTING ---
    def labelDoubleClickedEvent(self):
        """
        Signal when the label item is double-clicked.

         * currently not using
        """
        val = self.label.is_editable
        #self.label.setTextEditable(not val)

    #- Events ----
    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        #print 'change: ', change.__class__.__name__
        if change == self.ItemPositionHasChanged:
            self.nodeChanged.emit(self)
        return super(Node, self).itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """
        translate Y: height_expanded - height_collapsed/2
        """
        expanded = self.dagnode.expanded
        self.dagnode.expanded = not self.dagnode.expanded
        self.update()

        # translate the node in relation to it's expanded height
        diffy = (self.dagnode.height_expanded - self.dagnode.height_collapsed)/2
        if expanded:
            diffy = -diffy
        self.translate(0, diffy)
        QtGui.QGraphicsItem.mouseDoubleClickEvent(self, event)

    def boundingRect(self):
        w = self.width
        h = self.height
        bx = self.bufferX
        by = self.bufferY
        return QtCore.QRectF(-w/2 -bx, -h/2 - by, w + bx*2, h + by*2)

    @property
    def label_rect(self):
        return self.label.boundingRect()

    def shape(self):
        """
        Create the shape for collisions.
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
    def bg_color(self):
        if self.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.is_hover:
            base_color = QtGui.QColor(*self.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.color)

    @property
    def pen_color(self):
        if self.is_selected:
            return QtGui.QColor(*[251, 210, 91])
        return QtGui.QColor(*self._p_color)

    @property
    def label_color(self):
        if self.is_selected:
            return QtGui.QColor(*[88, 0, 0])
        return QtGui.QColor(*self._l_color)

    @property
    def shadow_color(self):
        if self.is_selected:
            return QtGui.QColor(*[104, 56, 0, 60])
        return QtGui.QColor(*self._s_color)

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

        # translate the label
        self.label.setPos(QtCore.QPointF(-self.width/2, -self.height/2))

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

    def setDebug(self, val):
        if val != self._debug:
            self._debug = val
            self.label._debug = val
            self.background._debug = val


class NodeLabel(QtGui.QGraphicsObject):
    
    doubleClicked     = QtCore.Signal()
    labelChanged      = QtCore.Signal()
    clicked           = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)
        
        self.dagnode        = parent.dagnode

        self._debug         = False
        self._font          = 'Monospace'
        self._font_size     = 8
        self._font_bold     = False
        self._font_italic   = False

        self.label = QtGui.QGraphicsTextItem(self.dagnode.name, self)
        self._document = self.label.document()

        # flags/signals
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

        self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeNameChanged)

        # bounding shape
        self.rect_item = QtGui.QGraphicsRectItem(self.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.rect_item.setPen(QtGui.QPen(QtGui.QColor(125,125,125)))        
        self.rect_item.pen().setStyle(QtCore.Qt.DashLine)
        self.rect_item.stackBefore(self.label)
        self.setHandlesChildEvents(False)

    def initDocument(self):
        cursor = self.label.textCursor()
        cursor.setPosition(0, QtGui.QTextCursor.KeepAnchor)
        cursor.select(QtGui.QTextCursor.Document)
        self.label.setTextCursor(cursor)

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

    def mouseDoubleClickEvent(self, event):
        if self.label.textInteractionFlags() == QtCore.Qt.NoTextInteraction:
            self.label.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
            self.initDocument()
        else:
            if self.label.textCursor():
                c = self.label.textCursor()
                c.clearSelection()
                self.label.setTextCursor(c)
            self.label.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        QtGui.QGraphicsItem.mouseDoubleClickEvent(self, event)

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
        return self.label.boundingRect()

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
        label_italic = self._font_italic

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self._font)
        qfont.setPointSize(self._font_size)
        qfont.setBold(self._font_bold)
        qfont.setItalic(label_italic)
        self.label.setFont(qfont)

        self.label.setDefaultTextColor(label_color)
        self.text = self.node.dagnode.name

        # debug
        if self._debug:
            qpen = QtGui.QPen(QtGui.QColor(125,125,125))
            qpen.setWidthF(0.5)
            qpen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(qpen)
            painter.drawPolygon(self.boundingRect())


class NodeBackground(QtGui.QGraphicsItem):
    def __init__(self, parent=None, scene=None):
        super(NodeBackground, self).__init__(parent, scene)

        self.dagnode = parent.dagnode
        self._debug  = False

    @property
    def node(self):
        return self.parentItem()

    def boundingRect(self):
        return self.node.boundingRect()

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
        qpen.setWidthF(1.5)

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(qpen)
        painter.drawRoundedRect(self.boundingRect(), 7, 7)

        # line pen #1
        lcolor = self.node.pen_color
        lcolor.setAlpha(80)
        lpen = QtGui.QPen(lcolor)
        lpen.setWidthF(0.5)

        if self.node.is_expanded:
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(lpen)

            label_line = self.labelLine()
            painter.drawLine(label_line)



class Edge(QtGui.QGraphicsObject):
    
    Type        = QtGui.QGraphicsObject.UserType + 2
    adjustment  = 5

    def __init__(self, dagnode, *args, **kwargs):
        QtGui.QGraphicsObject.__init__(self, *args, **kwargs)

        self.dagnode         = dagnode

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

        self.arrow_size      = 8 
        self.show_conn       = False                  # show connection string
        self.multi_conn      = False                  # multiple connections (future)
        self.edge_type       = 'bezier'

        # connections
        self.source_item     = None
        self.dest_item       = None

        # points
        self.source_point    = QtCore.QPointF(0,0)
        self.dest_point      = QtCore.QPointF(0,0)
        self.center_point    = QtCore.QPointF(0,0)      
        
        # geometry
        self.bezier_path     = QtGui.QPainterPath()
        self.poly_line       = QtGui.QPolygonF()

        # flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

    def setDebug(self, val):
        """
        Set the widget debug modeself.
        """
        if val != self._debug:
            self._debug = val

    def listConnections(self):
        """
        Returns a list of connected nodes.
        """
        return (self.source_item.node, self.dest_item.node)

    @property
    def source_node(self):
        """
        Returns the source node widget.
        """
        return self.source_item.node

    @property
    def dest_node(self):
        """
        Returns the destination node widget.
        """
        return self.dest_item.node

    @property
    def line_color(self):
        """
        Returns the current line color.
        """
        if self.is_selected:
            return QtGui.QColor(*self._h_color)
        if self.is_hover:
            base_color = QtGui.QColor(*self._l_color)
            return base_color.lighter(125)
        return QtGui.QColor(*self._l_color)
