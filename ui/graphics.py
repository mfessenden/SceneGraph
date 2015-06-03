#!/usr/bin/env python
from PySide import QtCore, QtGui, QtSvg
from functools import partial
import weakref

from SceneGraph import core
from . import node_widgets
reload(core)
reload(node_widgets)


class GraphicsView(QtGui.QGraphicsView):

    tabPressed          = QtCore.Signal()

    def __init__(self, parent = None, **kwargs):
        QtGui.QGraphicsView.__init__(self, parent)

        self.parent              = parent
        scene                    = GraphicsScene(self)
        self.setScene(scene)
        scene.setSceneRect(-5000, -5000, 10000, 10000)
        
        self._scale              = 1
        self.current_cursor_pos  = QtCore.QPointF(0, 0)

        # Mouse Interaction
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)

        self.setMouseTracking(True)
        self.boxing = False
        self.modifierBoxOrigin = None
        self.modifierBox = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
        self.scale(1.0, 1.0)

    def updateNetwork(self):
        """
        Update networkx graph attributes.
        """
        self.scene().network.graph['scale']=self.getScaleFactor()
        self.scene().network.graph['xform']=self.getTranslation()
        self.scene().network.graph['gview_rect']=self.sceneRect().getCoords()
        self.scene().network.graph['gscene_rect']=self.scene().sceneRect().getCoords()

    def getTranslation(self):
        #return [self.transform().m31(), self.transform().m32()]
        return [self.horizontalScrollBar().value(), self.verticalScrollBar().value()]

    def getScaleFactor(self):
        return [self.transform().m11(), self.transform().m22()]

    def wheelEvent(self, event):
        """
        Scale the viewport with the middle-mouse wheel
        """
        QtGui.QGraphicsView.wheelEvent(self, event)
        factor = 1.2
        if event.delta() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        self._scale = factor
        self.updateNetwork()

    def mouseMoveEvent(self, event):
        """
        Panning the viewport around and CTRL+mouse drag behavior.
        """
        # Panning
        self.current_cursor_pos = event.pos()
        if event.buttons() & QtCore.Qt.MiddleButton:
            delta = event.pos() - self.current_cursor_pos
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.current_cursor_pos = event.pos()
        else:
            self.current_cursor_pos = event.pos()
        
        # Handle Modifier+MouseClick box behavior
        if event.buttons() & QtCore.Qt.LeftButton and event.modifiers() & QtCore.Qt.ControlModifier:
            if self.boxing:
                self.modifierBox.setGeometry(QtCore.QRect(self.modifierBoxOrigin, event.pos()).normalized())
                self.modifierBox.show()
                event.accept()
                return

        self.updateNetwork()
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        QtGui.QGraphicsView.mousePressEvent(self, event)

    def event(self, event):
        """
        Capture the tab key press event.
        """
        if (event.type()==QtCore.QEvent.KeyPress) and (event.key()==QtCore.Qt.Key_Tab):
            self.tabPressed.emit()
        return QtGui.QGraphicsView.event(self, event)

    def keyPressEvent(self, event):
        """
        Fit the viewport if the 'A' key is pressed
        """
        graphicsScene = self.scene()
        graph = graphicsScene.graph

        if event.key() == QtCore.Qt.Key_A:
            # get the bounding rect of the graphics scene
            boundsRect = graphicsScene.itemsBoundingRect()
            
            # set it to the GraphicsScene item selection bounds...
            #self.setSceneRect(boundsRect)

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
                if isinstance(item, node_widgets.NodeWidget):                    
                    graphicsScene.network.remove_node(item.uuid)
                    graphicsScene.removeItem(item)

        self.updateNetwork()
        return QtGui.QGraphicsView.keyPressEvent(self, event)

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
    nodeAdded          = QtCore.Signal(object)
    nodeChanged        = QtCore.Signal(object)

    def __init__(self, parent=None):
        QtGui.QGraphicsScene.__init__(self, parent)

        self.line        = None
        self.sceneNodes  = weakref.WeakValueDictionary()
        self.graph       = None
        self.network     = None

    # TODO: do we need this anymore?
    def setNodeManager(self, val):
        self.graph = val
        self.network = val.network

    def addItem(self, item):
        """
        item = NodeWidget
        """
        self.nodeAdded.emit(item)
        self.sceneNodes[item.uuid] = item
        item.nodeChanged.connect(self.nodeChangedAction)

        dropshd = QtGui.QGraphicsDropShadowEffect()
        dropshd.setBlurRadius(12)
        dropshd.setColor(QtGui.QColor(0,0,0, 120))
        dropshd.setOffset(4,4)
        item.setGraphicsEffect(dropshd)
        item.setZValue(1)

        QtGui.QGraphicsScene.addItem(self, item)

    def nodeChangedAction(self, uuid, **kwargs):
        node = self.sceneNodes.get(uuid, None)
        if node:
            self.nodeChanged.emit(node)

    def dropEvent(self, event):
        newPos = event.scenePos()

    """
    # CONNECTING NODES:

         - we need to implement mousePressEvent, mouseMoveEvent & mouseReleaseEvent methods
    """
    def getNodes(self):
        """
        Returns a list of node widgets.
        """
        return self.sceneNodes.values()

    def mousePressEvent(self, event):
        """
        If an input/output connector is selected, draw a line
        """
        item = self.itemAt(event.scenePos())
        if event.button() == QtCore.Qt.LeftButton and (isinstance(item, core.nodes.NodeInput) or isinstance(item, core.nodes.NodeOutput)):
            self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
            self.addItem(self.line)
        QtGui.QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.line:
            newLine = QtCore.QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(newLine)
        QtGui.QGraphicsScene.mouseMoveEvent(self, event)
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
        self.line = None
        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        items = self.selectedItems()
        if items:
            for item in items:
                posy = item.boundingRect().topRight().y()
                item.setExpanded(not item.expanded)
                item.setY(item.pos().y() - posy)
                item.update()
        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)

    def connectionTest(self, startItems, endItems):
        """
        Check that the two nodes that the user is connecting can be connected
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
