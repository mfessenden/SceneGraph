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
    statusEvent          = QtCore.Signal(dict)

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

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    def updateNetworkGraphAttributes(self):
        """
        Update networkx graph attributes from the current UI.
        """
        self.scene().network.graph['scale']=self.getScaleFactor()
        self.scene().network.graph['xform']=self.getTranslation()
        self.scene().network.graph['gview_rect']=self.sceneRect().getCoords()
        self.scene().network.graph['gscene_rect']=self.scene().sceneRect().getCoords()

    # debug
    def getContentsSize(self):
        """
        Returns the contents size (physical size)
        """
        crect = self.contentsRect()
        return [crect.width(), crect.height()]

    def getSceneSize(self):
        """
        Returns the scene size.
        """
        srect = self.scene().sceneRect()
        return [srect.width(), srect.height()]

    def getTranslation(self):
        #return [self.transform().m31(), self.transform().m32()]
        return [self.horizontalScrollBar().value(), self.verticalScrollBar().value()]

    def getScaleFactor(self):
        scale_x = '%.3f' % self.transform().m11()
        scale_y = '%.3f' % self.transform().m22()
        return [scale_x, scale_y]

    def resizeEvent(self, event):
        #self.sendConsoleStatus(event)
        QtGui.QGraphicsView.resizeEvent(self, event)

    def viewportEvent(self, event):
        #self.sendConsoleStatus(event)
        return QtGui.QGraphicsView.viewportEvent(self, event)

    def enterEvent(self, event):
        #self.sendConsoleStatus(event)
        QtGui.QGraphicsView.enterEvent(self, event)

    def actionEvent(self, event):
        #self.sendConsoleStatus(event)
        QtGui.QGraphicsView.actionEvent(self, event)

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
        self.updateNetworkGraphAttributes()

    def sendConsoleStatus(self, event):
        """
        Update the parent UI with the view status.

        params:
            event - (QEvent) event object
        """
        #action.setData((action.data()[0], self.mapToScene(menuLocation)))
        # provide debug feedback
        status = dict(
            view_size = self.getContentsSize(),
            scene_rect = self.getSceneSize(),
            zoom_level = self.getScaleFactor(),
            )

        if hasattr(event, 'pos'):
            status['cursor_x'] = event.pos().x()
            status['cursor_y'] = event.pos().y()

            #status['cursor_sx'] = self.mapFromScene(event.pos()).x()
            #status['cursor_sy'] = self.mapFromScene(event.pos()).y()

            status['cursor_sx'] = self.mapToScene(event.pos()).x()
            status['cursor_sy'] = self.mapToScene(event.pos()).y()

        self.statusEvent.emit(status)

    def actionEvent(self, event):
        #self.sendConsoleStatus(event)
        QtGui.QGraphicsView.actionEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Panning the viewport around and CTRL+mouse drag behavior.
        """        
        self.current_cursor_pos = event.pos()
        self.sendConsoleStatus(event)

        # Panning
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

        self.updateNetworkGraphAttributes()
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        #self.sendConsoleStatus(event)
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
                    print '# GraphicsView: deleting node "%s"' % item.dagnode.name
                    graphicsScene.network.remove_node(str(item.dagnode.UUID))
                    graphicsScene.removeItem(item)
                    continue
                else:
                    if hasattr(item, '_is_node'):
                        if item._is_node:
                            print '# GraphicsView: deleting node "%s"' % item.dagnode.name
                            graphicsScene.network.remove_node(str(item.dagnode.UUID))
                            graphicsScene.removeItem(item)
                            continue
                print '# Error: GraphicsView: "%s" has an invalid type: "%s"' % (item.dagnode.name, str(item.__class__.__name__))

        self.updateNetworkGraphAttributes()
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

    def showContextMenu(self, pos):
        """
        Pop up a node creation context menu at a given location.
        """
        menu = QtGui.QMenu()
        menuActions = self.parent().createCreateMenuActions()
        for action in menuActions:
            action.setData((action.data()[0], self.mapToScene(pos)))
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(pos))


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
        self.sceneNodes[item.UUID] = item
        item.nodeChanged.connect(self.nodeChangedAction)

        dropshd = QtGui.QGraphicsDropShadowEffect()
        dropshd.setBlurRadius(12)
        dropshd.setColor(QtGui.QColor(0,0,0, 120))
        dropshd.setOffset(4,4)
        item.setGraphicsEffect(dropshd)
        item.setZValue(1)

        QtGui.QGraphicsScene.addItem(self, item)

    def nodeChangedAction(self, UUID, **kwargs):
        node = self.sceneNodes.get(UUID, None)
        if node:
            self.nodeChanged.emit(node)

    def dropEvent(self, event):
        newPos = event.scenePos()

    def getNodes(self):
        """
        Returns a list of node widgets.
        """
        return self.sceneNodes.values()

    def mousePressEvent(self, event):
        QtGui.QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        QtGui.QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        items = self.selectedItems()
        if items:
            for item in items:
                posy = item.boundingRect().topRight().y()

                #item.setExpanded(not item.expanded)
                #item.setY(item.pos().y() - posy)
                #item.update()
        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)

