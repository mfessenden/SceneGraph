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

    def __init__(self, node, width=100, height=175, expanded=False, font='Monospace', UUID=None, pos_x=0, pos_y=0):
        QtGui.QGraphicsObject.__init__(self)
        
        self.dagnode         = node
        self.dagnode._widget = self
        self.uuid            = UUID
        self.width           = width

        # flag for an expanded node
        self.expanded        = expanded
        self.expand_widget   = None   

        self.height          = height if expanded else 15
        
        # buffers
        self.bufferX         = 3
        self.bufferY         = 3
        self.color           = [180, 180, 180]
        
        # label
        self.label           = QtGui.QGraphicsTextItem(parent=self)
        self._font_family    = font
        self._font_size      = 8
        self._font_bold      = False
        self._font_italic    = False
        self.font            = QtGui.QFont(self._font_family)
        self._is_node        = True
        
        self.setFlags(QtGui.QGraphicsObject.ItemIsSelectable | QtGui.QGraphicsObject.ItemIsMovable | QtGui.QGraphicsObject.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)

        self.setPos(pos_x, pos_y)  

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return NodeWidget.Type
    
    @QtCore.Slot()
    def updateDagNode(self):
        """
        Update dag node attributes
        """
        attrs = dict()
        attrs.update(pos_x=self.pos().x())
        attrs.update(pos_y=self.pos().y())
        attrs.update(width=self.width)
        attrs.update(height=self.height)
        attrs.update(expanded=self.expanded)
        self.dagnode.addNodeAttributes(**attrs)
        self.nodeChanged.emit(self.uuid, attrs)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-self.width/2, -self.height/2, self.width, self.height), 5, 5)
        return path

    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        return QtCore.QRectF(-self.width/2  - self.bufferX,  -self.height/2 - self.bufferY,
                              self.width  + 3 + self.bufferX, self.height + 3 + self.bufferY)
    
    # Label formatting -----
    def setLabelItalic(self, val=False):
        """
        Set the label font italic
        """
        self._font_italic = val
        self.update()

    def setLabelBold(self, val=False):
        """
        Set the label font bold
        """
        self._font_bold = val
        self.update()

    def buildNodeLabel(self, shadow=True):
        """
        Build the node's label attribute.
        """
        self.label.setX(-(self.width/2 - self.bufferX + 3))
        self.label.setY(-(self.height/2 + self.bufferY))

        self.font = QtGui.QFont(self._font_family)
        self.font.setPointSize(self._font_size)
        self.font.setBold(self._font_bold)
        self.font.setItalic(self._font_italic)

        self.label.setFont(self.font)
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
    
    @QtCore.Slot()
    def nodeNameChanged(self):
        """
        Runs when the label text is edited.
        """
        node_name = self.label.document().toPlainText()
        cur_name = self.dagnode.name
        uuid = self.dagnode.uuid
        if node_name != cur_name:
            self.dagnode.name = node_name
            self.nodeChanged.emit(uuid, {'name':node_name})
            self.updateDagNode()

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

    def labelRect(self):
        """
        Return the nodes' label rectangle
        """
        return QtCore.QRectF()

    def setExpanded(self, val=True):
        self.expanded = val
        if val:
            self.height = 175
        else:
            self.height = 15
        self.update()

    def paint(self, painter, option, widget):
        """
        Draw the node.
        """
        # label & line
        self.buildNodeLabel(True)

        if self.expanded:    
            label_line = self.getLabelLine()
        
        # background
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)

        if option.state & QtGui.QStyle.State_Selected:
            gradient.setColorAt(0, QtGui.QColor(255, 172, 0))
            gradient.setColorAt(1, QtGui.QColor(200, 128, 0))
        else:
            topGrey = self.color[0]
            bottomGrey = self.color[0] / 1.5
            gradient.setColorAt(0, QtGui.QColor(topGrey, topGrey, topGrey))
            gradient.setColorAt(1, QtGui.QColor(bottomGrey, bottomGrey, bottomGrey))

        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
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
