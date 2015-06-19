#!/usr/bin/env python
import os
import weakref
from PySide import QtCore, QtGui, QtSvg
from functools import partial

from SceneGraph import core
# logger
log = core.log

from . import node_widgets
reload(core)
reload(node_widgets)



class GraphicsView(QtGui.QGraphicsView):

    tabPressed    = QtCore.Signal()
    statusEvent   = QtCore.Signal(dict)

    def __init__(self, parent=None, ui=None, **kwargs):
        QtGui.QGraphicsView.__init__(self, parent)

        self.parent              = ui
        scene                    = GraphicsScene(self)
        self.setScene(scene)
        scene.setSceneRect(-5000, -5000, 10000, 10000)
        
        self._scale              = 1
        self.current_cursor_pos  = QtCore.QPointF(0, 0)

        # Mouse Interaction
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        #self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)

        # update mode - full fixes bg errors on resize # 
        #self.setViewportUpdateMode(QtGui.QGraphicsView.SmartViewportUpdate)
        self.setViewportUpdateMode(QtGui.QGraphicsView.FullViewportUpdate)

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
        #self.updateSceneRect(self.scene().sceneRect()) 
        self.scene().update() 
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

        # set up timer for node drops
        timer = QtCore.QTimer()
        timer.timeout.connect(partial(self.edgeDrop, event))

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
                                    node_widget = self.scene().graph.getSceneNode(UUID=nid)
                                    node_widget.setSelected(True)

            if event_item is not None:
                if selected_nodes:
                    if len(selected_nodes) == 1:
                        sel_node = selected_nodes[0]
                        coll_items = self.scene().collidingItems(sel_node)


                        if event_item in coll_items:
                            print 'edge collision: "%s"' % (sel_node.dagnode.name)
                timer.start(1)

        self.updateNetworkGraphAttributes()
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def edgeDrop(self, event):
        item = self.itemAt(event.pos())
        if item:
            if hasattr(item, 'node_class'):
                collisions = self.scene().collidingItems(item)
                edges = []
                if collisions:
                    for c in collisions:
                        if hasattr(c, 'node_class'):
                            if c.node_class == 'edge':
                                edges.append(c)
                if edges:
                    edge = edges[0]
                    source_item = edge.source_item
                    dest_item = edge.source_item
                    print 'dropping node: ', item

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        #self.sendConsoleStatus(event)
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
            self.fitInView(graphicsScene.sceneRect(), QtCore.Qt.KeepAspectRatio)

        elif event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = self.scene().graph.selectedNodes()
            self.scene().graph.copyNodes(nodes)
            log.debug('copying nodes: %s' % ', '.join(nodes))

        elif event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = self.scene().graph.pasteNodes()
            log.debug('pasting nodes: %s' % ', '.join(nodes))

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

        self.updateNetworkGraphAttributes()
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
        menuActions = self.parent.initializeViewContextMenu()
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


class GraphicsScene(QtGui.QGraphicsScene):
    """
    Notes:

    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes

    """
    nodeAdded          = QtCore.Signal(object)
    edgeAdded          = QtCore.Signal(object)
    nodeChanged        = QtCore.Signal(object)
    edgeChanged        = QtCore.Signal(object)

    def __init__(self, parent=None):
        QtGui.QGraphicsScene.__init__(self, parent)

        self.line        = None    # temp line
        self.edge_type   = 'bezier'
        self.sceneNodes  = weakref.WeakValueDictionary()
        self.sceneEdges  = weakref.WeakValueDictionary()
        self.graph       = None
        self.network     = None

    def setGraph(self, val):
        """
        Add references to the graph and network objects.
        """
        self.graph      = val
        self.network    = val.network

    def update(self, *args):
        """
        Update certain node/edge attributes on update.
        """
        for item in self.items():
            if hasattr(item, 'debug_mode'):
                item.debug_mode = bool(eval(os.getenv("SCENEGRAPH_DEBUG", "0")))
                item.update()

            if hasattr(item, 'edge_type'):  
                item.edge_type = self.edge_type
                item.update()

        QtGui.QGraphicsScene.update(self, *args)

    def addItem(self, item):
        """
        item = widget type
        """        
        if hasattr(item, 'node_class'):
            if item.node_class in ['dagnode']:
                self.sceneNodes[str(item.UUID)] = item
                self.nodeAdded.emit(item)
                item.nodeChanged.connect(self.nodeChangedAction)
                item.scenePositionChanged.connect(self.itemPositionChanged)

            if item.node_class in ['edge']:
                self.sceneEdges[str(item.UUID)] = item
                self.edgeAdded.emit(item)
                # edges are QGraphicsLineItems, no signals
                #item.nodeChanged.connect(self.edgeChangedAction)
        QtGui.QGraphicsScene.addItem(self, item)

    def removeItem(self, item):
        """
        Update the graph if a dag node or edge is removed.
        """
        # since we don't want to eval the graph every time a node part is removed,
        # only force an update if we're removing a daganode/edge
        update_graph = False
        if hasattr(item, 'dagnode'):
            update_graph = True

        QtGui.QGraphicsScene.removeItem(self, item)
        if update_graph:
            self.graph.evaluate()

    def nodeChangedAction(self, UUID, attrs):
        # find the node widget
        node = self.sceneNodes.get(UUID, None)
        if node:
            self.nodeChanged.emit(node)
            print '# GraphicsScene: sending node changed: ', node
            self.update()

    def itemPositionChanged(self, item, pos):
        """
        Update the dag node when the widget position changes
        """
        item.dagnode.pos_x = pos[0]
        item.dagnode.pos_y = pos[1]
        self.nodeChanged.emit(item)

    def edgeChangedAction(self, UUID, attrs):
        # find the node widget
        edge = self.sceneEdges.get(UUID, None)
        if edge:
            self.edgeChanged.emit(edge)
            print '# GraphicsScene: sending edge changed: ', edge
            self.update()

    def dropEvent(self, event):
        newPos = event.scenePos()

    def getNodes(self):
        """
        Returns a list of node widgets.
        """
        return self.sceneNodes.values()

    def selectedNodes(self):
        """
        Returns a list of selected node widgets.
        """
        nodes = []
        selected = self.selectedItems()
        for item in selected:
            if hasattr(item, 'node_class'):
                nodes.append(item)
        return nodes

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

    def keyPressEvent(self, event):
        return QtGui.QGraphicsScene.keyPressEvent(self, event)

    def resizeEvent(self, event):        
        QtGui.QGraphicsScene.resizeEvent(self, event)
        self.update()        

    def mousePressEvent(self, event):
        """
        Draw a line if a connection widget is selected and dragged.
        """
        item = self.itemAt(event.scenePos())
        if event.button() == QtCore.Qt.LeftButton:
            if hasattr(item, 'node_class'):
                if item.node_class in ['connection']:
                    if item.isOutputConnection():
                        self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
                        self.addItem(self.line)
                        self.update(self.itemsBoundingRect())
            

        if event.button() == QtCore.Qt.RightButton:
            pass

        QtGui.QGraphicsScene.mousePressEvent(self, event)
        self.update()

    def mouseMoveEvent(self, event):
        """
        Update the line as the user draws.
        """
        item = self.itemAt(event.scenePos())
        if item:
            pass
        if self.line:
            newLine = QtCore.QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(newLine)

        QtGui.QGraphicsScene.mouseMoveEvent(self, event)
        self.update()

    def mouseReleaseEvent(self, event):
        """
        Create an edge if the connections are valid.
        """
        if self.line:
            source_items = self.items(self.line.line().p1())
            if len(source_items) and source_items[0] == self.line:
                source_items.pop(0)
            dest_items = self.items(self.line.line().p2())
            if len(dest_items) and dest_items[0] == self.line:
                dest_items.pop(0)

            self.removeItem(self.line)
            if len(source_items) and len(dest_items):

                # these are connection widgets
                source_conn = source_items[0]
                dest_conn = dest_items[0]

                if self.validateConnection(source_conn, dest_conn):
                    source_node = source_conn.node
                    dest_node = dest_conn.node

                    src_dag = source_node.dagnode
                    dest_dag = source_node.dagnode                    
                    edge = self.graph.addEdge(src=source_conn.name, dest=dest_conn.name)

        self.line = None
        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)
        self.update()

    def mouseDoubleClickEvent(self, event):
        items = self.selectedItems()
        if items:
            for item in items:
                if hasattr(item, 'setExpanded'):
                    posy = item.boundingRect().topRight().y()

                    # expand/collapse the node
                    item.setExpanded(not item.dagnode.expanded)
                    item.setY(item.pos().y() - posy)
                    item.update()

                if hasattr(item, 'node_class'):
                    if item.node_class == 'edge':
                        if item.visible:
                            edge = item.edge
                            print '# splitting nodes: ', edge.source_item, edge.dest_item

        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)
        self.update()

