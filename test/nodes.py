#!/usr/bin/env python
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
"""

class Node()