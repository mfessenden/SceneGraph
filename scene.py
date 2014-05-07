#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
import weakref

from . import core
reload(core)


class GraphicsItem (QtGui.QGraphicsItem):
    def __init__ (self):
        super(GraphicsItem, self).__init__()
        self.rectF = QtCore.QRectF(0,0,10,10)
    def boundingRect (self):
        return self.rectF
    def paint (self, painter=None, style=None, widget=None):
        painter.fillRect(self.rectF, QtCore.Qt.red)


class GraphicsView (QtGui.QGraphicsView):
    def __init__ (self, parent = None):
        super (GraphicsView, self).__init__ (parent)
        self.parent = parent
        
    def mousePressEvent(self, event):
        super (GraphicsView, self).mousePressEvent(event)
        item = GraphicsItem()
        position = QtCore.QPointF(event.pos()) - item.rectF.center()
        item.setPos(position.x() , position.y())
        #self.parent.scene.addItem(item)
        
    def wheelEvent (self, event):
        super (GraphicsView, self).wheelEvent(event)
        factor = 1.2
        if event.delta() < 0 :
            factor = 1.0 / factor
        self.scale(factor, factor)


class GraphicsScene(QtGui.QGraphicsScene):    
    tabKeyPressed        = QtCore.pyqtSignal(bool)    
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)      
        self.sceneNodes = weakref.WeakValueDictionary()        
        
    def createGenericNode(self):
        newPos = QtCore.QPointF(150, 150)
        return self.createNode('generic', newPos)
        
    def createNode(self, node_type, pos):
        # Now transfer the node_type (which is the base class Node) to a category or attribute node
        if node_type is "generic":
            sceneNode = core.GenericNode(node_type)

        #sceneNode.connectSignals()
        sceneNode.setPos(pos)
        self.sceneNodes["generic"] = sceneNode
        self.addItem(sceneNode)
        return sceneNode
    
    def dropEvent(self, event):
        newPos = event.scenePos()

    def mousePressEvent(self, event):
        super(GraphicsScene, self).mousePressEvent(event)
        item = GraphicsItem()
        position = QtCore.QPointF(event.scenePos()) - item.rectF.center()
        item.setPos(position.x() , position.y())
        self.addItem(item)
        print '( %s, %s )' % ( str(event.pos().x()), str(event.pos().y()))
