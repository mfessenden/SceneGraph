#!/usr/bin/env python
import os
import math
import uuid
from PySide import QtGui, QtCore, QtSvg
import simplejson as json

from .. import options
reload(options)


class NodeWidget(QtGui.QGraphicsItem):
    
    Type                = QtGui.QGraphicsItem.UserType + 3
    clickedSignal       = QtCore.Signal(QtCore.QObject)
    nodeCreatedInScene  = QtCore.Signal()
    nodeChanged         = QtCore.Signal(bool)

    def __init__(self, node, width=100, height=175, expanded=False, font='Monospace', UUID=None):
        QtGui.QGraphicsItem.__init__(self)
        
        self.dagnode         = node
        self.width           = width
        self.expanded        = expanded
        self.height          = height
        
        # buffers
        self.bufferX         = 3
        self.bufferY         = 3
        self.color           = [180, 180, 180]
        
        # label
        #self.label           = QtGui.QGraphicsSimpleTextItem(parent=self)
        self.label           = QtGui.QGraphicsTextItem(parent=self)
        self._font_family    = font
        self._font_size      = 10
        self._font_bold      = False
        self._font_italic    = False
        self.font            = QtGui.QFont(self._font_family)
        self._is_node        = True
        
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)        

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return NodeWidget.Type

    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        return QtCore.QRectF(-self.width/2  - self.bufferX,  -self.height/2 - self.bufferY,
                              self.width  + 3 + self.bufferX, self.height + 3 + self.bufferY)
    
    # Label formatting -----
    def setLabelItalic(self, val=False):
        self._font_italic = val

    def setLabelBold(self, val=False):
        self._font_bold = val

    def buildNodeLabel(self, shadow=True):
        """
        Build the node's label attribute.
        """
        self.label.setX(-(self.width/2 - self.bufferX))
        self.label.setY(-(self.height/2 + self.bufferY))  # minus bufferY if plaintext

        self.font = QtGui.QFont(self._font_family)
        self.font.setPointSize(self._font_size)
        self.font.setBold(self._font_bold)
        self.font.setItalic(self._font_italic)

        self.label.setFont(self.font)
        #self.label.setText(self.dagnode.name)
        self.label.setPlainText(self.dagnode.name)
        self.label.setDefaultTextColor(QtGui.QColor(0, 0, 0))

        # drop shadow
        if shadow:
            dropshd = QtGui.QGraphicsDropShadowEffect()
            dropshd.setBlurRadius(6)
            dropshd.setColor(QtGui.QColor(0,0,0, 180))
            dropshd.setOffset(2,3)

            self.label.setGraphicsEffect(dropshd)

    
    def getLabelLine(self):
        """
        Draw a line for the node label area
        """
        p1 = self.boundingRect().topLeft()
        p1.setY(p1.y() + self.bufferY*8)
        p2 = self.boundingRect().topRight()
        p2.setY(p2.y() + self.bufferY*8)
        return QtCore.QLineF(p1, p2)
    
    def labelRect(self):
        """
        Return the nodes' label rectangle
        """
        return QtCore.QRectF()

    def paint(self, painter, option, widget):
        """
        Draw the node.
        """
        # label & line
        self.buildNodeLabel()        
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

        painter.setBrush(QtGui.QBrush(gradient))
        #painter.setBrush(QtGui.QBrush(QtGui.QColor(*self.color)))
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        #fullRect = QtCore.QRectF(-self.width/2, - self.height/2, self.width, self.height)
        #painter.drawRect(self.boundingRect())
        fullRect = self.boundingRect()
        painter.drawRoundedRect(fullRect, 3, 3)
        painter.drawLine(label_line)
        #painter.drawText(self.boundingRect().x()+self.buffer, self.boundingRect().y()+self.buffer, self.dagnode.name)

        # drop shadow
        dropshd = QtGui.QGraphicsDropShadowEffect()
        dropshd.setBlurRadius(12)
        dropshd.setColor(QtGui.QColor(0,0,0, 90))
        dropshd.setOffset(8,8)
        self.setGraphicsEffect(dropshd)