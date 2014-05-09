#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
import weakref

from . import core
reload(core)


class GraphicsItem(QtGui.QGraphicsItem):
    """
    Simple test node
    icon=GraphicsItem()
    icon.setPos(200, 200)
    """   
    def __init__ (self):
        super(GraphicsItem, self).__init__()
        self.rectF = QtCore.QRectF(0,0,120,170)
        
    def boundingRect (self):
        return self.rectF
    
    def paint (self, painter=None, style=None, widget=None):
        painter.fillRect(self.rectF, QtCore.Qt.red)


class GraphicsView (QtGui.QGraphicsView):
    tabPressed        = QtCore.pyqtSignal(bool)
    def __init__ (self, parent = None, **kwargs):
        super(GraphicsView, self).__init__ (parent)
        self.gui = kwargs.get('gui')
        self.parent = parent
        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        #self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    
    def wheelEvent (self, event):
        super (GraphicsView, self).wheelEvent(event)
        factor = 1.2
        if event.delta() < 0 :
            factor = 1.0 / factor
        self.scale(factor, factor)
    
    def keyPressEvent(self, event):
        # fit all nodes in the view
        if event.key() == QtCore.Qt.Key_A:
            graphicsScene = self.scene()
            boundsRect = graphicsScene.itemsBoundingRect()
            
            # adjust bounds TODO: fix this
            boundsRect.adjust(200, 200, 200, 200)
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)
            
        elif event.key() == QtCore.Qt.Key_Tab:
            self.tabPressed.emit(True)        
        event.accept()

    """
    def mousePressEvent(self, event):
        # mouse event to drag select by default, pan with control-click 
        if event.button() == QtCore.Qt.LeftButton:
            if event.modifiers() == QtCore.Qt.ControlModifier:
                self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)            
            else:
                self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        
        event.accept()
    """

class GraphicsScene(QtGui.QGraphicsScene):    
    """
    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes
    
    """
     
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)      
        self.sceneNodes = weakref.WeakValueDictionary()        
        
    def createGenericNode(self):
        newPos = QtCore.QPointF(150, 150)
        return self.createNode(newPos)
        
    def createNode(self, node_type, pos=[0, 0]):
        # Now transfer the node_type (which is the base class Node) to a category or attribute node
        if node_type is "generic":
            sceneNode = core.GenericNode()

        #sceneNode.connectSignals()
        sceneNode.setPos(pos[0], pos[1])
        self.sceneNodes["generic"] = sceneNode
        self.addItem(sceneNode)
        return sceneNode
    
    def dropEvent(self, event):
        newPos = event.scenePos()

    def mouseDoubleClickEvent(self, event):
        """
        If mouse is double-clicked, add a node # BETA
        """
        super(GraphicsScene, self).mouseDoubleClickEvent(event)
        item = core.GenericNode()
        position = QtCore.QPointF(event.scenePos()) - item.rectF.center()
        item.setPos(position.x() , position.y())
        self.addItem(item)
