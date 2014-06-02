#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
import weakref
import re

from . import core
reload(core)


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
            boundsRect.adjust(-100, -100, 100, 100)
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)
            
        elif event.key() == QtCore.Qt.Key_Tab:
            print '# Tab key pressed'
            self.tabPressed.emit(True)
            return True
            
        elif event.key() == QtCore.Qt.Key_Delete:
            graphicsScene = self.scene()
            nodeManager = graphicsScene.nodeManager
            for item in graphicsScene.selectedItems():
                nodeManager.removeNode(item)
                #graphicsScene.removeItem(item)
        event.accept()


class GraphicsScene(QtGui.QGraphicsScene):    
    """
    Notes:
    
    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes
    
    """
     
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)      
        self.sceneNodes = weakref.WeakValueDictionary()
        self.nodeManager = NodeManager(self)     
        
    def createGenericNode(self):
        newPos = QtCore.QPointF(150, 150)
        return self.createNode(newPos)
        
    def createNode(self, node_type, **kwargs):
        """
        Create a node in the current scene with the given attributes
        """
        node_name   = kwargs.get('name', 'My_Node')
        node_pos    = kwargs.get('pos', [0,0])
        # Now transfer the node_type (which is the base class Node) to a category or attribute node
        if node_type is "generic":
            sceneNode = core.GenericNode(name=node_name)
        #sceneNode.connectSignals()
        sceneNode.setPos(node_pos[0], node_pos[1])
        self.sceneNodes[sceneNode.node_name] = sceneNode
        self.addItem(sceneNode)
        return sceneNode
    
    def createTestNode(self, **kwargs):        
        node_pos = kwargs.get('pos', [0,0])
        sceneNode = core.NodeTest(**kwargs)
        sceneNode.setPos(node_pos[0], node_pos[1])
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
        item = self.nodeManager.createNode('generic')
        position = QtCore.QPointF(event.scenePos()) - item.rectF.center()
        item.setPos(position.x() , position.y())


class NodeManager(object):
    """
    Manages nodes in the parent graph
    """
    def __init__(self, parent):
        
        self._parent = parent
        
    def getNodes(self):
        """
        Returns a weakref to all of the scene nodes
        """
        return self._parent.sceneNodes

    def getNode(self, node_name):
        """
        Get a node by name
        """
        if node_name in self.getNodes():
            return self.getNodes().get(node_name)
        return
    
    def createNode(self, node_type, **kwargs):
        """
        Creates a node in the parent graph
        """
        node_name = self._nodeNamer(kwargs.pop('name', 'My_Node'))
        return self._parent.createNode(node_type, name=node_name, **kwargs)
    
    def removeNode(self, node_item):
        """
        Removes a node from the graph
        """
        node_name = node_item.node_name
        print '# Removing node: "%s"' % node_name
        self._parent.removeItem(node_item)       
    
    def renameNode(self, old_name, new_name):
        """
        Rename a node in the graph
        
        Returns the renamed node
        """
        item=self._parent.sceneNodes.pop(old_name)
        item.node_name = new_name
        self._parent.sceneNodes[item.node_name]=item
        return item
    
    def _getNames(self):
        """
        Returns the names of all the current nodes
        """
        return sorted(self.getNodes().keys())
    
    def _nodeNamer(self, node_name):
        """
        Returns a legal node name
        """
        node_name = re.sub(r'[^a-zA-Z0-9\[\]]','_', node_name)
        node_name = '%s1' % node_name
        all_names = self._getNames()
        if node_name in all_names:
            node_num = int(re.search('\d+$', node_name).group())
            node_base = node_name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):                
                if '%s%d' % (node_base, i) not in all_names:
                    node_name = '%s%d' % (node_base, i)
                    break
        return node_name
                
    
        