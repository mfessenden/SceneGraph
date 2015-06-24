#!/usr/bin/env python
import os
from PySide import QtCore, QtGui
from functools import partial
from SceneGraph import core
from . import manager
# test nodes
from SceneGraph.test import nodes

# logger
log = core.log


class GraphicsView(QtGui.QGraphicsView):

    tabPressed    = QtCore.Signal()
    statusEvent   = QtCore.Signal(dict)

    def __init__(self, parent=None, ui=None, opengl=False, debug=False, **kwargs):
        QtGui.QGraphicsView.__init__(self, parent)

        self.log                 = log
        self._parent             = ui
        
        self._scale              = 1
        self.current_cursor_pos  = QtCore.QPointF(0, 0)

        self.initializeSceneGraph(ui.graph, opengl=opengl, debug=debug)
        self.setUpdateMode(False)

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
        self.connectSignals()

    def initializeSceneGraph(self, graph, opengl=False, debug=False):
        """
        Setup the GraphicsScene
        """
        if opengl:
            from PySide import QtOpenGL
            self.setViewport(QtOpenGL.QGLWidget())
            log.info('initializing OpenGL renderer.')
        scene = GraphicsScene(self, graph=graph, debug=debug)
        scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(scene)

    def setUpdateMode(self, full):
        """
        Set the viewport update mode.
        """
        if full:
            self.setViewportUpdateMode(QtGui.QGraphicsView.SmartViewportUpdate)
        else:
            self.setViewportUpdateMode(QtGui.QGraphicsView.FullViewportUpdate)

    def updateGraphViewAttributes(self):
        """
        Update networkx graph attributes from the current UI.

        TODO: check speed hit on this one
        """
        self.scene().network.graph['view_scale']=self.getScaleFactor()
        self.scene().network.graph['view_center']=self.getCenterPoint()
        self.scene().network.graph['scene_size']=self.scene().sceneRect().getCoords()

    def connectSignals(self):
        self.scene().changed.connect(self.sceneChangedAction)
        self.scene().sceneRectChanged.connect(self.sceneRectChangedAction)
        self.scene().selectionChanged.connect(self.sceneSelectionChangedAction)

    # debug
    def getContentsSize(self):
        """
        Returns the contents size (physical size)
        """
        crect = self.contentsRect()
        return [crect.width(), crect.height()]
    
    def getCenterPoint(self):
        """
        Returns the correct center point of the current view.
        """
        # maps center to a QPointF
        center_point = self.mapToScene(self.viewport().rect().center())
        return (center_point.x(), center_point.y())
    
    def setCenterPoint(self, pos):
        """
        Sets the current scene center point.

        params:
            pos - (tuple) x & y coordinates.
        """
        self.centerOn(pos[0],pos[1])

    def getSceneSize(self):
        """
        Returns the scene size.
        """
        srect = self.scene().sceneRect()
        return [srect.width(), srect.height()]

    def getTranslation(self):
        """
        Returns the current scrollbar positions.
        """
        return [self.horizontalScrollBar().value(), self.verticalScrollBar().value()]

    def getScaleFactor(self):
        """
        Returns the current scale factor.
        """
        return [self.transform().m11(), self.transform().m22()]

    def updateStatus(self, event):
        """
        Update the parent UI with the view status.

        params:
            event - (QEvent) event object
        """
        #action.setData((action.data()[0], self.mapToScene(menuLocation)))
        # provide debug feedback
        status = dict(
            view_size = self.getContentsSize(),
            scene_size = self.getSceneSize(),
            zoom_level = self.getScaleFactor(),
            )
 
        if hasattr(event, 'pos'):
            epos = event.pos()
            spos = self.mapToScene(event.pos())
            status['view_cursor'] = (epos.x(), epos.y())            
            status['scene_cursor'] = (spos.x(), spos.y())
            status['scene_pos'] = self.getCenterPoint()

        self.statusEvent.emit(status)

    def wheelEvent(self, event):
        """
        Wheel event to implement a smoother scaling.
        """
        factor = 1.41 ** ((event.delta()*.5) / 240.0)
        self.scale(factor, factor)
        self._scale = factor
        self.updateGraphViewAttributes()

    def mouseMoveEvent(self, event):

        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        self.current_cursor_pos = event.pos()
        if event.modifiers() & QtCore.Qt.ControlModifier:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        QtGui.QGraphicsView.mousePressEvent(self, event)

    def event(self, event):
        """
        Capture the tab key press event.
        """
        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Tab:
            self.tabPressed.emit()
        return QtGui.QGraphicsView.event(self, event)

    def keyPressEvent(self, event):
        """
        Fit the viewport if the 'A' key is pressed
        """
        if event.key() == QtCore.Qt.Key_A:
            # get the bounding rect of the graphics scene
            boundsRect = self.scene().itemsBoundingRect()            
            
            # resize
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)
            #self.setSceneRect(boundsRect) # this resizes the scene rect to the bounds rect, not desirable

        if event.key() == QtCore.Qt.Key_F:
            snodes = self.scene().selectedNodes()
            bRect = self.scene().selectionArea().boundingRect()
            self.fitInView(bRect, QtCore.Qt.KeepAspectRatio)

        # delete nodes & edges...
        elif event.key() == QtCore.Qt.Key_Delete:
            for item in self.scene().selectedItems():
                if hasattr(item, 'node_class'):
                    if item.node_class in ['dagnode']:
                        self.scene().graph.removeNode(item.dagnode.name, UUID=item.UUID)

                    elif item.node_class in ['edge']:
                        self.scene().graph.removeEdge(UUID=item.UUID)
                    # TODO: scene different error
                    self.scene().removeItem(item)
                    continue

        # disable selected nodes
        elif event.key() == QtCore.Qt.Key_D:
            items = self.scene().selectedItems()
            for item in items:
                dag = item.dagnode
                if hasattr(dag, 'enabled'):
                    try:
                        item.enabled = not item.enabled
                        #item.setSelected(False)
                    except:
                        pass

        self.updateGraphViewAttributes()
        self.scene().update()
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
        menuActions = []
        for action in menuActions:
            #action.setData((action.data()[0], self.mapToScene(pos)))
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(pos))

    def restoreNodes(self, data):
        """
        Undo command.
        """
        selected_nodes = self.selected_nodes()
        self.blockSignals(True)
        for node in selected_nodes:
            node.dagnode.update(**data)
        self.blockSignals(False)
    
    #- Actions -----
    def sceneChangedAction(self, *args):
        #print '# GraphicsView: scene changed'
        pass
        
    def sceneRectChangedAction(self, *args):
        #print '# GraphicsView: scene rect changed'
        pass
        
    def sceneSelectionChangedAction(self):
        #print '# GraphicsView: scene selection changed'
        pass


class GraphicsScene(QtGui.QGraphicsScene):
    """
    Notes:

    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes

    """
    def __init__(self, parent=None, graph=None, debug=False):
        QtGui.QGraphicsScene.__init__(self, parent)

        self.graph       = graph
        self.network     = graph.network
        self.debug       = debug

        self.line        = None    # temp line
        self.edge_type   = 'bezier'
        self.manager     = manager.WindowManager(self)
        self.scenenodes  = dict()

    def addNodes(self, dagnodes):
        """
        Add dag nodes to the current scene.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]

        widgets = []
        for dag in dagnodes:
            if isinstance(dag, core.DagNode):              
                if dag.UUID not in self.scenenodes:
                    widget = nodes.Node(dag)

                    # set the debug mode
                    widget.setDebug(self.debug)
                    self.scenenodes[dag.UUID]=widget
                    self.addItem(widget)
                    widgets.append(widget)

            elif isinstance(dag, core.DagEdge):              
                if dag.UUID not in self.scenenodes:
                    widget = nodes.Edge(dag)

                    # set the debug mode
                    widget.setDebug(self.debug)
                    self.scenenodes[dag.UUID]=widget
                    self.addItem(widget)
                    widgets.append(widget)

            else:
                log.warning('unknown node type: "%s"' % dag.__class__.__name__)
        return widgets

    def getNodes(self):
        """
        Returns a list of node widgets.
        """
        return self.scenenodes.values()

    def getNode(self, val):
        """
        Get a named node from the scene.
        """
        if val in self.scenenodes:
            return self.scenenodes.get(val)

        for id, node in self.scenenodes.iteritems():
            node_name = node.dagnode.name
            if node_name == val:
                return node

    def selectedNodes(self):
        """
        Returns a list of selected node widgets.
        """
        dagnodes = []
        selected = self.selectedItems()
        for item in selected:
            if isinstance(item, core.DagNode):
                dagnodes.append(item)
        return dagnodes

    def selectedEdges(self):
        """
        Returns a list of selected edge widgets.
        """
        edges = []
        selected = self.selectedItems()
        for item in selected:
            if hasattr(item, 'node_class'):
                if item.node_class in ['edge']:
                    edges.append(item)
        return edges

    def getEdges(self):
        """
        Returns a list of edge widgets.
        """
        return self.scenenodes.values()

    def getEdge(self, edge):
        return

    def popNode(self, node):
        """
        'Pop' a node from it's current connections.
        """
        return True

    def insertNode(self, node, edge):
        """
        Insert a node into the selected edge.
        """
        return True

    def itemPositionChanged(self, item, pos):
        """
        Update the dag node when the widget position changes
        """
        item.dagnode.pos_x = pos[0]
        item.dagnode.pos_y = pos[1]
        # manager: update Graph nodss
        #self.nodeChanged.emit(item)

    def validateConnection(self, source_item, dest_item, force=True):
        """
        When the mouse is released, validate the two connections.
        """
        if not hasattr(source_item, 'node_class') or not hasattr(dest_item, 'node_class'):
            return False

        if source_item.node_class not in ['connection'] or dest_item.node_class not in ['connection']:
            return False

        if source_item.isInputConnection() or dest_item.isOutputConnection():
            return False

        # don't let the user connect input/output on the same node!
        if str(source_item.dagnode.UUID) == str(dest_item.dagnode.UUID):
            return False

        # check here to see if destination can take another connection
        if hasattr(dest_item, 'is_connectable'):
            if not dest_item.is_connectable:
                if not force:
                    return False

                # remove the connected edge
                dest_node = dest_item.node
                edges = dest_node.listConnections().values()

                for edge in edges:
                    edge_id = str(edge.dagnode.UUID)
                    self.graph.removeEdge(UUID=edge_id)
                return True

        return True

