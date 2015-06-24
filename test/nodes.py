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
"""

class Node(QtGui.QGraphicsObject):

    Type = QtGui.QGraphicsObject.UserType + 1

    def __init__(self, dagnode, parent=None):
        super(Node, self).__init__(parent)

        self.dagnode         = dagnode
        
        # attributes
        self.width           = 100
        self.height          = 20
        self.bufferX         = 3
        self.bufferY         = 3

        self._l_color        = [5, 5, 5, 255]         # label color
        self._b_color        = [172, 172, 172, 255]   # bg color
        self._p_color        = [10, 10, 10, 255]      # pen color (outer rim)
        self._s_color        = [0, 0, 0, 60]          # shadow color

        # globals
        self._debug          = False
        self.orientation     = 'horizontal'           # connect on sides/top    
        self.is_expanded     = False                  # node is expanded 
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx

        self._label_coord    = [0,0]

        # layers
        self.background = NodeBackground(self)
        self.label = NodeLabel(self)        

        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

    def boundingRect(self):
        w = self.width
        h = self.height
        bx = self.bufferX
        by = self.bufferY
        return QtCore.QRectF(-w/2 -bx, -h/2 - by, w + bx*2, h + by*2)

    def shape(self):
        """
        Create the shape for collisions.
        """
        w = self.width
        h = self.height
        bx = self.bufferX
        by = self.bufferY
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-w/2, -h/2, w, h), 7, 7)
        return path

    @property
    def bg_color(self):
        if self.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.is_hover:
            base_color = QtGui.QColor(*self._b_color)
            return base_color.lighter(125)
        return QtGui.QColor(*self._b_color)

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


    def db(self):
        print 'debugging'


class NodeLabel(QtGui.QGraphicsObject):
    
    labelChanged = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)
        
        self.dagnode        = parent.dagnode

        self.font           = 'Monospace'
        self._font_size     = 8
        self._font_bold     = False
        self._font_italic   = False

        self.label = QtGui.QGraphicsTextItem(self.dagnode.name, self)
        self._document = self.label.document()

        # flags/signals
        '''
        self.label.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeNameChanged)
        
        self.rect_item = QtGui.QGraphicsRectItem(self.label.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        self.rect_item.stackBefore(self.label)
        '''

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

    def paint(self, painter, option, widget):
        """
        Draw the label.
        """
        label_color = self.node.label_color
        label_italic = self._font_italic

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self.font)
        qfont.setPointSize(self._font_size)
        qfont.setBold(self._font_bold)
        qfont.setItalic(label_italic)
        self.label.setFont(qfont)

        self.label.setDefaultTextColor(label_color)
        self.text = self.node.dagnode.name
    

class NodeBackground(QtGui.QGraphicsItem):
    def __init__(self, parent=None, scene=None):
        super(NodeBackground, self).__init__(parent, scene)

        self.dagnode=parent.dagnode

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
        bg_clr2 = bg_clr1.darker(125)

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

