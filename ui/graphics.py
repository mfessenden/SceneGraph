#!/usr/bin/env python
from PySide import QtCore, QtGui, QtSvg
import weakref

from SceneGraph import core
reload(core)


class GraphicsView (QtGui.QGraphicsView):

    tabPressed          = QtCore.Signal()
    rootSelected        = QtCore.Signal(bool)

    def __init__(self, parent = None, **kwargs):
        super(GraphicsView, self).__init__(parent)

        self.gui    = kwargs.get('gui')
        self.parent = parent

        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.renderer = QtSvg.QSvgRenderer()
        self.setRenderHint(QtGui.QPainter.Antialiasing)

    def wheelEvent(self, event):
        """
        Scale the viewport with the middle-mouse wheel
        """
        super(GraphicsView, self).wheelEvent(event)
        factor = 1.2
        if event.delta() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        super(GraphicsView, self).mousePressEvent(event)

    def event(self, event):
        """
        Capture the tab key press event.
        """
        if (event.type()==QtCore.QEvent.KeyPress) and (event.key()==QtCore.Qt.Key_Tab):
            self.tabPressed.emit()
        return super(GraphicsView, self).event(event)

    def keyPressEvent(self, event):
        """
        Fit the viewport if the 'A' key is pressed
        """
        graphicsScene = self.scene()
        graph = graphicsScene.graph

        if event.key() == QtCore.Qt.Key_A:
            # get the bounding rect of the graphics scene
            boundsRect = graphicsScene.itemsBoundingRect()
            # set it to the GraphicsView scene rect...
            self.setSceneRect(boundsRect)
            # resize
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)

        elif event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = graph.selectedNodes()
            graph.copyNodes(nodes)
            print '# copying nodes: ', nodes

        elif event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = graph.pasteNodes()
            print '# pasting nodes: ', nodes

        elif event.key() == QtCore.Qt.Key_Delete:
            for item in graphicsScene.selectedItems():
                if isinstance(item, core.LineClass) or isinstance(item, core.NodeBase):
                    item.deleteNode()

        elif event.key() == QtCore.Qt.Key_S:
            self.rootSelected.emit(True)

        return super(GraphicsView, self).keyPressEvent(event)

    def get_scroll_state(self):
        """
        Returns a tuple of scene extents percentages
        """
        centerPoint = self.mapToScene(self.viewport().width()/2,
                                      self.viewport().height()/2)
        sceneRect = self.sceneRect()
        centerWidth = centerPoint.x() - sceneRect.left()
        centerHeight = centerPoint.y() - sceneRect.top()
        sceneWidth =  sceneRect.width()
        sceneHeight = sceneRect.height()

        sceneWidthPercent = centerWidth / sceneWidth if sceneWidth != 0 else 0
        sceneHeightPercent = centerHeight / sceneHeight if sceneHeight != 0 else 0
        return sceneWidthPercent, sceneHeightPercent


class GraphicsScene(QtGui.QGraphicsScene):
    """
    Notes:

    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes

    """

    def __init__(self, parent=None):
        super(GraphicsScene, self).__init__(parent)

        self.line        = None
        self.sceneNodes  = weakref.WeakValueDictionary()
        self.graph       = None

    def setNodeManager(self, val):
        self.graph = val

    def addNode(self, node_type, **kwargs):
        """
        Create a node in the current scene with the given attributes

        params:
            node_type   - (str) node type to create

        returns:
            (object)    - scene node
        """
        node_name   = kwargs.get('name', 'node')
        node_pos    = kwargs.get('pos', [0,0])
        
        sceneNode = core.GenericNode(name=node_name)
        
        # Now transfer the node_type (which is the base class Node) to a category or attribute node
        if node_type is "root":
            sceneNode = core.RootNode()
        #sceneNode.connectSignals()
        sceneNode.setPos(node_pos[0], node_pos[1])
        self.sceneNodes[sceneNode.node_name] = sceneNode
        self.addItem(sceneNode)
        return sceneNode

    def dropEvent(self, event):
        newPos = event.scenePos()

    def mouseDoubleClickEvent(self, event):
        super(GraphicsScene, self).mouseDoubleClickEvent(event)

    """
    # CONNECTING NODES:

         - we need to implement mousePressEvent, mouseMoveEvent & mouseReleaseEvent methods
    """
    def mousePressEvent(self, event):
        """
        If an input/output connector is selected, draw a line
        """
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

                ###  NEED TO IMPLEMENT THIS< OR DELETE ###
                # Sending the data downstream. The start item is the upstream node ALWAYS. The end item is the downstream node ALWAYS.
                #connectionLine.getEndItem().getWidgetMenu().receiveFrom(connectionLine.getStartItem(), delete=False)
                #connectionLine.getStartItem().getWidgetMenu().sendData(connectionLine.getStartItem().getWidgetMenu().packageData())
                # Emitting the "justConnected" signal (That is on all connection points)
                #connectionLine.myEndItem.lineConnected.emit()
                #connectionLine.myStartItem.lineConnected.emit()
                ### ###
        self.line = None
        super(GraphicsScene, self).mouseReleaseEvent(event)

    def connectionTest(self, startItems, endItems):
        """
        This is the big if statement that is checking
        to make sure that whatever nodes the user is trying to
        make a connection between is allowable.
        """
        if startItems[0]:
            if startItems[0].isInputConnection:
                temp = startItems[0]
                if endItems[0]:
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
