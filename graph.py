#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui, QtSvg
import weakref
import re

from . import core
reload(core)

"""
Notes:

    - overloading mouseMoveEvent on QGraphicsScene not easily implemented

"""


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
        self.renderer = QtSvg.QSvgRenderer()
    
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
                #nodeManager.removeNode(item)
                item.deleteNode()
        event.accept()


class GraphicsScene(QtGui.QGraphicsScene):    
    """
    Notes:
    
    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes
    
    """
     
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)
        
        self.line        = None    
        self.sceneNodes  = weakref.WeakValueDictionary()
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
    
    """
    To connect the nodes, we need to implement mousePressEvent, mouseMoveEvent & mouseReleaseEvent    
    """
    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos())
        if event.button() == QtCore.Qt.LeftButton and (isinstance(item, core.nodes.NodeInput) or isinstance(item, core.nodes.NodeOutput)):
            self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
            self.addItem(self.line)
        super(GraphicsScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line:
            newLine = QtCore.QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(newLine)
        super(GraphicsScene, self).mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.line:
            startItems = self.items(self.line.line().p1())
            print '# start items: ', startItems
            if len(startItems) and startItems[0] == self.line:
                startItems.pop(0)
            endItems = self.items(self.line.line().p2())
            if len(endItems) and endItems[0] == self.line:
                endItems.pop(0)

            self.removeItem(self.line)

            # If this is true a successful line was created
            if self.connectionTest(startItems, endItems):
                # Creates a line that is basically of 0 length, just to put a line into the scene
                connectionLine = core.nodes.LineClass(startItems[0], endItems[0], QtCore.QLineF(startItems[0].scenePos(), endItems[0].scenePos()))
                self.addItem(connectionLine)
                # Now use that previous line created and update its position, giving it the proper length and etc...
                connectionLine.updatePosition()
                # Setting the emitter, particle, and particleShape on the node
                connectionLine.getStartItem().getWidgetMenu().emitter = connectionLine.getEndItem().getWidgetMenu().emitter
                connectionLine.getStartItem().getWidgetMenu().particle = connectionLine.getEndItem().getWidgetMenu().particle
                connectionLine.getStartItem().getWidgetMenu().particleShape = connectionLine.getEndItem().getWidgetMenu().particleShape
                # Sending the data downstream. The start item is the upstream node ALWAYS. The end item is the downstream node ALWAYS.
                connectionLine.getEndItem().getWidgetMenu().receiveFrom(connectionLine.getStartItem(), delete=False)
                connectionLine.getStartItem().getWidgetMenu().sendData(connectionLine.getStartItem().getWidgetMenu().packageData())
                # Emitting the "justConnected" signal (That is on all connection points)
                connectionLine.myEndItem.lineConnected.emit()
                connectionLine.myStartItem.lineConnected.emit()

        self.line = None
        super(GraphicsScene, self).mouseReleaseEvent(event)

    def connectionTest(self, startItems, endItems):
        """
        This is the big if statement that is checking
        to make sure that whatever nodes the user is trying to
        make a connection between is allowable.
        """
        if startItems[0].isInputConnection:
            temp = startItems[0]
            startItems[0] = endItems[0]
            endItems[0] = temp

        try:
            if len(startItems) is not 0 and len(endItems) is not 0:
                if startItems[0] is not endItems[0]:
                    if isinstance(startItems[0], core.nodes.NodeOutput) and isinstance(endItems[0], core.nodes.NodeInput):
                        if (startItems[0].isOutputConnection and endItems[0].isInputConnection):
                            return True
        except AttributeError:
            pass
        return False

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
        if node_name in self._parent.sceneNodes.keys():
            self._parent.sceneNodes.pop(node_name)
    
    def renameNode(self, old_name, new_name):
        """
        Rename a node in the graph
        
        Returns the renamed node
        """
        if new_name in self._getNames():
            print '# Error: "%s" is not unique' % new_name
            return

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
                
    
        