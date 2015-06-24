#!/usr/bin/env python
import os
from PySide import QtCore, QtGui, QtSvg
from functools import partial

from SceneGraph import core
from . import node_widgets
from . import manager

reload(core)
reload(node_widgets)
reload(manager)

# logger
log = core.log


class GraphicsView(QtGui.QGraphicsView):

    tabPressed    = QtCore.Signal()
    statusEvent   = QtCore.Signal(dict)

    def __init__(self, parent=None, ui=None, **kwargs):
        QtGui.QGraphicsView.__init__(self, parent)

        self.log                 = log
        self._parent             = ui
                
        self._scale              = 1
        self.current_cursor_pos  = QtCore.QPointF(0, 0)

        self.initializeSceneGraph(ui.graph)
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

    def initializeSceneGraph(self, graph):
        """
        Setup the GraphicsScene
        """
        scene = GraphicsScene(self, graph=graph)
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
        Returns the current scrollbar 
        """
        #return [self.transform().m31(), self.transform().m32()]
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
        Scale the viewport with the middle-mouse wheel
        """
        QtGui.QGraphicsView.wheelEvent(self, event)
        factor = 1.2
        if event.delta() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        self._scale = factor
        self.updateGraphViewAttributes()

    def mouseMoveEvent(self, event):
        """
        Panning the viewport around and CTRL+mouse drag behavior.
        """        
        self.current_cursor_pos = event.pos()
        self.updateStatus(event)

        # set up timer for node drops
        timer = QtCore.QTimer()
        #timer.timeout.connect(self.splitNodeConnection)

        selected_nodes = self.scene().selectedNodes()

        # query any edges at the current position
        event_item = self.itemAt(event.pos())
        event_edge = None
        if hasattr(event_item, 'node_class'):
            if event_item.node_class in ['edge']:
                event_edge = event_item
        # Panning
        if event.buttons() & QtCore.Qt.MiddleButton:
            delta = event.pos() - self.current_cursor_pos
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.current_cursor_pos = event.pos()
        else:
            self.current_cursor_pos = event.pos()


        # translate the view when left mouse/control are active
        if event.buttons() & QtCore.Qt.LeftButton and event.modifiers() & QtCore.Qt.ControlModifier:
            if self.boxing:
                self.modifierBox.setGeometry(QtCore.QRect(self.modifierBoxOrigin, event.pos()).normalized())
                self.modifierBox.show()
                event.accept()
                return

        if event.buttons() & QtCore.Qt.LeftButton:            
            if event.modifiers() & QtCore.Qt.AltModifier:
                if event_item:
                    if hasattr(event_item, 'node_class'):
                        if event_item.node_class in ['dagnode']:
                            UUID = event_item.dagnode.UUID
                            if UUID:
                                # get downstream nodes 
                                ds_ids = self.scene().graph.downstream(UUID)
                                for nid in ds_ids:
                                    node_widget = self.view.getNode(nid)
                                    node_widget.setSelected(True)

            if event.modifiers() & QtCore.Qt.ShiftModifier:             
                if selected_nodes:
                    if len(selected_nodes) == 1:
                        sel_node = selected_nodes[0]
                        sel_node_conn = sel_node.listConnections()

                        if sel_node_conn:
                            # TODO: add connetion check here
                            self.popNode(sel_node)


            if event.modifiers() & QtCore.Qt.MetaModifier: 
                if event_item is not None:
                    if selected_nodes:
                        if len(selected_nodes) == 1:
                            sel_node = selected_nodes[0]
                            coll_items = self.scene().collidingItems(sel_node)
                            ext_coll = []
                            for c in coll_items:
                                if hasattr(c, 'dagnode'):
                                    if c.dagnode.name != sel_node.dagnode.name:
                                        if c not in ext_coll:
                                            ext_coll.append(c)
                            col_nodes = [x for x in ext_coll if hasattr(x, 'node_class')]

                            if len(col_nodes):
                                if len(col_nodes) == 1:
                                    edge_widget = col_nodes[0]
                                    if sel_node.node_class in ['dagnode']:                                
                                        self.splitNodeConnection(sel_node, edge_widget)

        self.updateGraphViewAttributes()
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
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
            nodes = self.scene().selectedNodes()
            bRect = self.scene().selectionArea().boundingRect()
            self.fitInView(bRect, QtCore.Qt.KeepAspectRatio)

        elif event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = graph.selectedNodes()

            if graph.copyNodes(nodes):
                log.info('copying nodes: %s' % ', '.join(nodes))

        elif event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = graph.pasteNodes()
            if nodes:
                log.info('pasting nodes: %s' % ', '.join(nodes))

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
        menuActions = self._parent.initializeViewContextMenu()
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
    def __init__(self, parent=None, graph=None):
        QtGui.QGraphicsScene.__init__(self, parent)

        self.graph       = graph
        self.network     = graph.network

        self.line        = None    # temp line
        self.edge_type   = 'bezier'
        self.manager     = manager.WindowManager(self)
        self.scenenodes  = dict()

    def addNodes(self, nodes):
        """
        Add nodes to the current scene.
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]

        for node in nodes:
            if node.Type > 65536:
                if node.dagnode.UUID not in self.scenenodes:
                    self.scenenodes[node.dagnode.UUID]=node
                    self.addItem(node)

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

    def selectedNodes(self):
        """
        Returns a list of selected node widgets.
        """
        nodes = []
        selected = self.selectedItems()
        for item in selected:
            if hasattr(item, 'node_class'):
                if item.node_class in ['dagnode']:
                    nodes.append(item)
        return nodes

    def getEdges(self):
        """
        Returns a list of edge widgets.
        """
        return self.scenenodes.values()

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

