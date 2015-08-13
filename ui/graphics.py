#!/usr/bin/env python
import os
from PySide import QtCore, QtGui
from functools import partial
from SceneGraph import core
from SceneGraph.core import nodes

from . import node_widgets
from . import handlers
from . import commands

# logger
log = core.log


class GraphException(Exception):
    def __init__(self, message, errors={}):
        super(GraphException, self).__init__(message)

        self.errors = errors


class GraphicsView(QtGui.QGraphicsView):

    tabPressed        = QtCore.Signal()
    statusEvent       = QtCore.Signal(dict)
    selectionChanged  = QtCore.Signal()
    nodesChanged      = QtCore.Signal(list)

    def __init__(self, parent=None, ui=None, use_gl=False, debug=False, **kwargs):
        QtGui.QGraphicsView.__init__(self, parent)

        self.log                 = log
        self._parent             = ui
        
        self._scale              = 1
        self.current_cursor_pos  = QtCore.QPointF(0, 0)
        self._nodes_to_copy      = []   

        self.initializeSceneGraph(ui.graph, ui, use_gl=use_gl, debug=debug)
        self.viewport_mode       = self._parent.viewport_mode
        
        # Mouse Interaction
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(*[34, 34, 34])))
        self.setMouseTracking(True)
        
        self.boxing = False
        self.modifierBoxOrigin = None
        self.modifierBox = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self)
        self.scale(1.0, 1.0)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connectSignals()

    def initializeSceneGraph(self, graph, ui, **kwargs):
        """
        Setup the GraphicsScene.

        :param core.Graph graph: graph instance.
        :param QtGui.QMainWindow graph: parent window.
         """
        use_gl = kwargs.get('use_gl', ui.use_gl)
        if use_gl:
            from PySide import QtOpenGL
            self.setViewport(QtOpenGL.QGLWidget(QtOpenGL.QGLFormat(QtOpenGL.QGL.SampleBuffers)))
            log.info('initializing OpenGL renderer.')

        # pass the Graph instance to the GraphicsScene 
        scene = GraphicsScene(self, graph=graph, ui=ui)
        scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(scene)

    @property
    def viewport_mode(self):
        """
        Returns the current viewport mode.

        return:
            (str) - update mode.
        """
        mode = self.viewportUpdateMode()
        if mode == QtGui.QGraphicsView.ViewportUpdateMode.FullViewportUpdate:
            return 'full'
        if mode == QtGui.QGraphicsView.ViewportUpdateMode.SmartViewportUpdate:
            return 'smart'
        if mode == QtGui.QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate:
            return 'minimal'
        if mode == QtGui.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate:
            return 'bounding'
        return

    @viewport_mode.setter
    def viewport_mode(self, mode):
        """
        Set the viewport update mode.

        params:
            mode (str) - viewport level (full is slower).
        """
        if mode == 'full':
            mode = QtGui.QGraphicsView.ViewportUpdateMode.FullViewportUpdate

        if mode == 'smart':
            mode = QtGui.QGraphicsView.ViewportUpdateMode.SmartViewportUpdate

        if mode == 'minimal':
            mode = QtGui.QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate

        if mode == 'bounding':
            mode = QtGui.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate

        self.setViewportUpdateMode(mode)

    def connectSignals(self):
        """
        Connect widget signals.
        """
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

        returns:
            (QPointF) - current view center point.
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

    def getSceneCoordinates(self):
        """
        Returns the scene size.

        returns:
            (tuple) - coordinates of current scene. (-x, -y, x, y)
        """
        if self.scene():
            return self.scene().sceneRect().getCoords()
        return (0, 0, 0, 0)

    def getTranslation(self):
        """
        Returns the current scrollbar positions.

        returns:
            (tuple) - scroll bar coordinates (h, v)
        """
        return [self.horizontalScrollBar().value(), self.verticalScrollBar().value()]

    def getScaleFactor(self):
        """
        Returns the current scale factor.
        """
        return [self.transform().m11(), self.transform().m22()]

    def getSceneAttributes(self):
        """
        Returns a dictionary of scene attributes.

        returns:
            (dict) - view position, scale, size.
        """
        scene_attributes = dict()
        scene_attributes.update(view_scale=self.getScaleFactor())
        scene_attributes.update(view_center=self.getCenterPoint())
        scene_attributes.update(view_size=self.getContentsSize())
        scene_attributes.update(scene_size=self.getSceneCoordinates())
        return scene_attributes

    def updateSceneAttributes(self):
        """
        Update networkx graph attributes from the current UI.

         *todo: check speed hit on this one
        """
        scene_attributes = self.getSceneAttributes()
        self.scene().network.graph.update(**scene_attributes)

    def updateStatus(self, event):
        """
        Update the parent console widget with the view status.

        :param QtCore.QEvent event: event object.
        """
        #action.setData((action.data()[0], self.mapToScene(menuLocation)))
        # provide debug feedback
        status = dict(
            view_size = self.getContentsSize(),
            scene_size = self.getSceneCoordinates(),
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

    def mouseMoveEvent(self, event):
        """
        Move connected nodes if the Alt key is pressed.
        """     
        selected_nodes = self.scene().selectedNodes()
        event_item = self.itemAt(event.pos())
        nodes_to_move = []
        if event.buttons() & QtCore.Qt.LeftButton:            
            if event.modifiers() & QtCore.Qt.AltModifier:
                if selected_nodes:                    
                    for sel_node in selected_nodes:
                        if hasattr(sel_node, 'dagnode'):
                            UUID = sel_node.dagnode.id
                            if UUID:
                                # get downstream nodes 
                                ds_ids = self.scene().graph.downstream(UUID)
                                for nid in ds_ids:
                                    node_widget = self.scene().get_node(nid)
                                    if node_widget and node_widget not in nodes_to_move:
                                        nodes_to_move.append(node_widget)

        if nodes_to_move:
            for node_widget in nodes_to_move:
                node_widget.setSelected(True)

        self.updateStatus(event)
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        QtGui.QGraphicsView.mouseDoubleClickEvent(self, event)

    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """        
        self.current_cursor_pos = event.pos()
        if event.button() == QtCore.Qt.LeftButton:
            if event.modifiers() & QtCore.Qt.ControlModifier:
                self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
            else:
                self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)

        # right mouse click
        if event.button() == QtCore.Qt.RightButton:
            item = self.itemAt(event.pos())
            color = False
            attribute = False
            add = True
            if item is not None:
                color = True
                attribute = True
                add = False
            self.showContextMenu(event.pos(), add=add, color=color, attribute=attribute)
            
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
        selected_nodes = self.scene().selectedNodes()
        hover_nodes = self.scene()._hover_nodes

        if event.key() == QtCore.Qt.Key_A:
            # get the bounding rect of the graphics scene
            boundsRect = self.scene().itemsBoundingRect()            
            
            # resize
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)
            #self.setSceneRect(boundsRect) # this resizes the scene rect to the bounds rect, not desirable

        # disable selected nodes
        elif event.key() == QtCore.Qt.Key_X:
            self._parent.toggleDebug()

        # disable selected nodes
        elif event.key() == QtCore.Qt.Key_D:
            if selected_nodes:
                for node in selected_nodes:
                    node.is_enabled = not node.is_enabled

        elif event.key() == QtCore.Qt.Key_F:
            boundsRect = self.scene().selectionArea().boundingRect()

            if not boundsRect:
                if self.scene().selectedNodes():
                    boundsRect = self.scene().scelectedNodesRect()
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)

        # delete nodes & edges...
        elif event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace:
            self.scene().handler.removeSceneNodes(selected_nodes)

        elif event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
            self._nodes_to_copy = self.scene().selectedDagNodes()            
            log.warning('copying nodes: "%s"' % '", "'.join([x.name for x in self._nodes_to_copy]))

        elif event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            if self._nodes_to_copy:
                new_nodes = self.scene().graph.pasteNodes(self._nodes_to_copy)
                log.warning('pasting %d nodes' % len(new_nodes))
                self._nodes_to_copy = []

        # toggle edge types
        elif event.key() == QtCore.Qt.Key_E:
            edge_type = self._parent.edge_type
            toggled = 'polygon'
            if edge_type == 'polygon':
                toggled = 'bezier'
            self._parent.toggleEdgeTypes(edge_type=toggled)

        # update edges if the Alt key is pressed
        elif event.key() == QtCore.Qt.Key_Alt:
            if hover_nodes:
                for node in hover_nodes:
                    if hasattr(node, 'alt_modifier'):
                        node.alt_modifier = True

        self.scene().update()
        return QtGui.QGraphicsView.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        """
        Update edges to remove the 'alt_modifier' flag.
        """
        hover_nodes = self.scene()._hover_nodes
        if hover_nodes:
            for node in hover_nodes:
                if hasattr(node, 'alt_modifier'):
                    node.alt_modifier = False
        return QtGui.QGraphicsView.keyReleaseEvent(self, event)

    def get_scroll_state(self):
        """
        Returns a tuple of scene extents percentages.
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

    def showContextMenu(self, pos, add=True, color=True, attribute=True):
        """
        Pop up a node creation context menu at a given location.

        :param QtCore.QPointF pos: position to launch menu at.
        :param bool add: create **add node** menu.
        :param bool color: create **node color** menu.
        :param bool attribute: create **node attribute** manager menu.
        """
        menu = QtGui.QMenu()
        self._parent.createNodesMenu(menu, self.mapToScene(pos), add=add, color=color, attribute=attribute)
        menu.exec_(self.mapToGlobal(pos))
    
    #- Actions -----
    def addAttributeAction(self, node=None):
        print 'adding something'

    def sceneChangedAction(self, *args):
        """
        Runs when the scene has changed in some manner.
        """
        self.updateSceneAttributes()
        
    def sceneRectChangedAction(self, *args):
        #print '# GraphicsView: scene rect changed'
        self.updateSceneAttributes()
        
    def sceneSelectionChangedAction(self):
        """
        Runs when the scene selection changes.
        """
        self.selectionChanged.emit()


class GraphicsScene(QtGui.QGraphicsScene):
    """
    Notes:

    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes

    """
    def __init__(self, parent=None, graph=None, ui=None, **kwargs):
        QtGui.QGraphicsScene.__init__(self, parent)

        self.ui             = ui
        self.edge_type      = ui.edge_type

        # graph
        self.graph          = graph
        self.network        = graph.network
        self.plug_mgr       = graph.plug_mgr

        # temp line for drawing edges
        self.line           = None  
        self.scenenodes     = dict()

        # temp attributes
        self._hover_nodes   = []

    def initialize(self):
        """
        Initialize the scene nodes attributes and
        clear the current scene.
        """
        self.scenenodes=dict()
        self.clear()

    @property
    def debug(self):
        return self.ui.debug

    @debug.setter
    def debug(self, value):
        self.ui.debug = value

    @property
    def view(self):
        return self.views()[0]
    
    @property 
    def undo_stack(self):
        return self.ui.undo_stack

    def evaluate(self):
        """
        Refresh the scene.
        """
        for nid in self.scenenodes:
            widget = self.scenenodes.get(nid)
            widget.update()
        self.update()

    def updateNodes(self, data):
        """
        Update nodes with arbitrary data.

        params:
            data (dict) - node graph data.
        """
        selected_nodes = self.selected_nodes()
        self.blockSignals(True)
        for node in selected_nodes:
            print 'updating node: ', node.name
            node.dagnode.update(**data)
        self.blockSignals(False)

    def restoreNodes(self, data):
        """
        Restore a working version of the scene.

         *todo: need to rework the scene file format to not blow away the scene.

        params:
            data (dict) - node graph data.

        """
        self.initialize()
        self.blockSignals(True)
        #self.undo_stack.setActive(False)
        self.graph.restore(data, graph=False)
        #self.undo_stack.setActive(True)
        self.blockSignals(False)
        self.update()

    def addNodes(self, dagids):
        """
        Add dag nodes to the current scene.

        :param list dagnodes: list of dag node/edge objects.
        """
        if type(dagids) not in [list, tuple]:
            dagids = [dagids,]

        log.debug('GraphicsScene: adding %d nodes.' % len(dagids))
        widgets = []
        for dag_id in dagids:
            #print 'dag id: ', dag_id
            if dag_id in self.graph.dagnodes:
                dag = self.graph.dagnodes.get(dag_id)

                if issubclass(type(dag), nodes.Node):
                    if dag_id not in self.scenenodes:               
                        widget = self.plug_mgr.get_widget(dag)

                        if not widget:
                            log.warning('invalid widget: "%s"' % dag.name)
                            continue
                            
                        widget._render_effects = self.ui.render_fx
                        widget._font = self.ui.font_family_nodes
                        
                        # set the debug mode
                        widget.setDebug(self.debug)
                        self.scenenodes[dag.id]=widget
                        self.addItem(widget)
                        widgets.append(widget)

                        widget.nodeChanged.connect(self.nodeChangedEvent)
                        widget.nodeDeleted.connect(self.nodeDeletedEvent)
                else:
                    log.warning('invalid dag type: "%s"' % dag.__class__)
               
            else:
                raise GraphException('invalid graph id: "%s"' % dag_id )
        return widgets

    def addEdges(self, edges):
        """
        Add edges to the current scene.

        params:
            edges (list) - list of nx edge dictionaries.
        """
        if type(edges) not in [list, tuple]:
            edges = [edges,]

        widgets = []
        old_snapshot = self.graph.snapshot()

        for edge in edges:

            src_id = edge.get('src_id')
            dest_id = edge.get('dest_id')

            src_attr = edge.get('src_attr', 'output')
            dest_attr = edge.get('dest_attr', 'input')

            weight = edge.get('weight', 1)
            edge_type = edge.get('edge_type', self.ui.edge_type)

            source_node = self.get_node(src_id)
            dest_node  = self.get_node(dest_id)

            # nodes not found? Seeya
            if not source_node:
                raise GraphException('invalid source id: "%s"' % srcid)
                return False

            if not dest_node:
                raise GraphException('invalid destination id: "%s"' % destid)
                return False

            # get the relevant connection terminals
            src_conn_widget = source_node.getOutputConnection(src_attr)
            dest_conn_widget = dest_node.getInputConnection(dest_attr)

            if not src_conn_widget or not dest_conn_widget:
                print 'cannot find a connection widget'
                continue

            edge_widget = node_widgets.EdgeWidget(edge, src_conn_widget, dest_conn_widget, weight=weight, edge_type=edge_type)
            edge_widget.nodeDeleted.connect(self.nodeDeletedEvent)
            edge_widget._render_effects = self.ui.render_fx

            # check that connection is valid. (implement this)
            if edge_widget.connect_terminal(src_conn_widget) and edge_widget.connect_terminal(dest_conn_widget):
                # set the debug mode
                edge_widget.setDebug(self.debug)
                self.scenenodes[edge_widget.ids]=edge_widget
                self.addItem(edge_widget)
                widgets.append(edge_widget)

                new_snapshot = self.graph.snapshot()
                self.undo_stack.push(commands.SceneNodesCommand(old_snapshot, new_snapshot, self, msg='edge added'))

        return widgets

    def removeNodes(self, nodes):
        """
        Remove node widgets from the scene.

        params:
            nodes (list) - list of node widgets.
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]
            
        for node in nodes:
            if self.is_node(node):
                self.graph.remove_node(node.dagnode.id)

            if self.is_edge(node):
                self.graph.remove_edge(*node.ids)

    def is_top_level(self, widget):
        """
        Returns true if the given widget is a dag node type or edge.

        params:
            widget (obj) - QGraphicsObject widget.

        returns:
            (bool) - widget is a Dag node type. 
        """
        if self.is_node(widget) or self.is_edge(widget):
            return True
        return False

    def is_node(self, widget):
        """
        Returns true if the given widget is a dag node type.

        params:
            widget (obj) - QGraphicsObject widget.

        returns:
            (bool) - widget is a Dag node type. 
        """
        if hasattr(widget, 'node_class'):
            if widget.node_class in ['dagnode', 'dot', 'note', 'container']:
                return True
        return False

    def is_connection(self, widget):
        """
        Returns true if the given widget is a dag node connection type.

        params:
            widget (obj) - QGraphicsObject widget.

        returns:
            (bool) - widget is a connection type. 
        """
        if hasattr(widget, 'node_class'):
            if widget.node_class in ['connection']:
                return True
        return False

    def is_edge(self, widget):
        """
        Returns true if the given widget is a edge type.

        params:
            widget (obj) - QGraphicsObject widget.

        returns:
            (bool) - widget is an edge type. 
        """
        if hasattr(widget, 'node_class'):
            if widget.node_class in ['edge']:
                return True
        return False

    def get_nodes(self):
        """
        Returns a list of node widgets.

        :returns: list of DagNode widgets.
        :rtype: list
        """
        widgets = []
        for item in self.items():
            if self.is_node(item):            
                widgets.append(item)
        return widgets

    def get_node(self, name):
        """
        Get a named node widget from the scene.

        :param str name: node name or id.

        :returns: node widget.
        :rtype: SceneGraph.ui.NodeWidget
        """
        if name in self.scenenodes:
            return self.scenenodes.get(name)

        for node in self.get_nodes():
            node_name = node.dagnode.name
            if node_name == name:
                return node

    def selectedNodes(self, nodes_only=False):
        """
        Returns a list of selected item widgets.

        :returns: list of widgets.
        :rtype: list
        """
        widgets = []
        selected = self.selectedItems()
        for item in selected:
            if self.is_node(item):
                widgets.append(item)

            if self.is_edge(item):
                if not nodes_only:
                    widgets.append(item)
        return widgets

    def scelectedNodesRect(self, adjust=25):
        """
        Returns a rect of the currently selected nodes.

        params:
            adjust (int) - amount to buffer the result.

        returns:
            (QtCore.QRectF) - rect of currently selected nodes.
        """
        path = QtGui.QPainterPath()
        for node in self.selectedNodes():
            rect_poly = node.mapToScene(node.boundingRect())
            path.addRect(rect_poly.boundingRect())

        result = path.boundingRect()
        result.adjust(-adjust, -adjust, adjust, adjust)
        return result

    def selectedDagNodes(self):
        """
        Returns a list of selected dag nodes.

        returns:
            (list) - list of selected dag nodes.
        """
        if self.selectedNodes():
            return [n.dagnode for n in self.selectedNodes() if self.is_node(n)]
        return []

    def get_edges(self):
        """
        Returns a list of edge widgets.

        returns:
            (list) - list of Edge widgets.
        """
        edges = []
        for item in self.items():
            if self.is_edge(item):
                edges.append(item)
        return edges

    def get_edge(self, *args):
        """
        Return a named edge.
        """
        edges = []
        for edge in self.get_edges():
            if edge.name in args:
                edges.append(edge)
            if edge.source_connection in args:
                if edge.dest_connection in args:
                    edges.append(edge)
        for arg in args:
            if arg in self.scenenodes:
                edges.append(self.scenenodes.get(arg))
        return edges

    def popNode(self, node):
        """
        'Pop' a node from its current chain.

        params:
            node (NodeWidget) - node widget instance.

        returns:
            (bool) - node was properly removed from its chain.
        """

        if not self.is_node(node):
            log.warning('popNode: invalid widget type')
            return

        dagnode = node.dagnode
        predecessors = self.graph.network.predecessors(dagnode.id)
        successors = self.graph.network.successors(dagnode.id)
        reconnect = len(predecessors) == 1 and len(successors) == 1

        #print '# reconnect: ', reconnect

        # get the connected edges
        connected_edges = []
        for conn_name in node.connections:
            conn_widget = node.connections.get(conn_name)
            if conn_widget.is_connected:
                for edge in conn_widget.connected_edges():
                    if edge not in connected_edges:
                        connected_edges.append(edge)

        reconnections = []
        if connected_edges:
            for cedge in connected_edges:
                if reconnect:
                    #print 'edge to reconnect: ', cedge.name
                    src_conn_widget = edge.source_item()
                    dst_conn_widget = edge.dest_item()

                    src_dag = src_conn_widget.dagnode
                    dst_dag = dst_conn_widget.dagnode

                    if src_dag is not dagnode:
                        #print '# source connection: ', src_dag.name
                        reconnections.append(src_conn_widget.connection_name)

                    if dst_dag is not dagnode:
                        #print '# dest connection: ', dst_dag.name
                        reconnections.append(dst_conn_widget.connection_name)

                if cedge.breakConnections():
                    cedge.close()
        return True

    def insertNode(self, node, edge):
        """
        Insert a node into the selected edge chain.

        params:
            node (DagNode) - node widget instance.
            edge (Edge) - edge widget instance.

        returns:
            (bool) - node was properly inserted into the current chain.
        """
        return True

    def splitEdge(self, edge, pos):
        """
        Insert a dot into the selected edge chain.

        params:
            edge (Edge) - edge widget instance.

        returns:
            (bool) - node was properly inserted into the current chain.
        """
        if not self.is_edge(edge):
            log.warning('splitEdge: invalid widget type')
            return

        src_attr = edge.source_item().name
        dest_attr = edge.dest_item().name

        src = edge.source_node.dagnode
        dest = edge.dest_node.dagnode

        # remove the old edge
        if self.graph.remove_edge(*edge.ids):
            dot = self.graph.add_node('dot', pos=[pos.x(), pos.y()])

            # add the two new edges
            edge1 = self.graph.add_edge(src, dot, src_attr=src_attr, dest_attr='input', edge_type='polygon')
            edge2 = self.graph.add_edge(dot, dest, src_attr='output', dest_attr=dest_attr, edge_type='polygon')
            if edge1 and edge2:
                return True
        return False

    def nodeAt(self, *args):
        """
        Similar to 'itemAt', return a node if available. 
        """
        item = QtGui.QGraphicsScene.itemAt(self, *args)
        if hasattr(item, 'node'):
            if hasattr(item.node, 'node_class'):
                item = item.node
        return item

    def mousePressEvent(self, event):
        """
        Draw a line if a connection widget is selected and dragged.
        """
        item = self.itemAt(event.scenePos())
        node = self.nodeAt(event.scenePos())

        modifiers = QtGui.QApplication.keyboardModifiers()

        # left mouse
        if event.button() == QtCore.Qt.LeftButton:
            if modifiers == QtCore.Qt.AltModifier:
                if item:
                    if self.is_edge(item):
                        if self.splitEdge(item, event.scenePos()):
                            log.info('splitting edge...')
                        else:
                            log.warning('cannot split edge.')

            elif modifiers == QtCore.Qt.ShiftModifier:
                if node:
                    if self.is_node(node):
                        if self.popNode(node):
                            log.info('popping node "%s"' % node.dagnode.name)
                        else:
                            log.warning('cannot pop node "%s"' % node.dagnode.name)
            else:
                if item:
                    if self.is_connection(item):
                        if item.isOutputConnection():
                            crect = item.boundingRect()
                            lpen = QtGui.QPen(QtGui.QBrush(QtGui.QColor(*[251, 251, 251])), 1, QtCore.Qt.SolidLine)
                            self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
                            self.line.setPen(lpen)
                            self.addItem(self.line)
                            self.update(self.itemsBoundingRect())

                        # disconnect the edge if this is an input
                        if item.isInputConnection():
                            # query the edge(s) attached.
                            edges = item.connections.values()                    
                            if edges:
                                if len(edges) == 1:
                                    conn_edge = edges[0]

                                    # remove the edge from the connections
                                    if conn_edge.disconnect_terminal(item):
                                        log.info('disconnecting edge: "%s"' % self.graph.edge_nice_name(*conn_edge.ids))
                                        # todo: call manage?
                                        self.graph.remove_edge(*conn_edge.ids)

                                        edge_line = conn_edge.getLine()
                                        p1 = edge_line.p1()

                                        self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(p1, event.scenePos()))
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
        modifiers = QtGui.QApplication.keyboardModifiers()
        item = self.nodeAt(event.scenePos())
        self._hover_nodes = []

        if item:
            if self.is_node(item) or self.is_edge(item):
                self._hover_nodes.append(item)

        # if we're drawing a line...
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

            self.line.scene().removeItem(self.line)
            self.line = None

            if len(source_items) and len(dest_items):
                # these are connection widgets
                source_conn = source_items[0]
                dest_conn = dest_items[0]

                # if we're not dealing with two connections, return 
                if not self.is_connection(source_conn) or not self.is_connection(dest_conn):
                    return

                if source_conn == dest_conn:
                    return

                if self.validateConnection(source_conn, dest_conn):
                    src_dag = source_conn.dagnode
                    dest_dag = dest_conn.dagnode
                    edge = self.graph.add_edge(src_dag, dest_dag, src_attr=source_conn.name, dest_attr=dest_conn.name)

        QtGui.QGraphicsScene.mouseReleaseEvent(self, event)
        self.update()

    def nodeChangedEvent(self, node):
        """
        Update dag node when widget attributes change. 
        Signal the graph that the data has changed as well.

        :param ui.NodeWidget node: node widget.
        """
        if hasattr(node, 'dagnode'):
            # update the position
            pos = (node.pos().x(), node.pos().y())
            node.setToolTip('(%d, %d)' % (pos[0], pos[1]))
            node.dagnode.pos = pos

            # SIGNAL MANAGER (Scene -> Graph)
            #self.handler.sceneNodesUpdatedAction([node,])           

    def nodeDeletedEvent(self, node):
        """
        Called when a node is deleted.

        params:
            node (QGraphicsObject) - node (or edge) widget.
        """
        if self.is_node(node):
            node.close()

        if self.is_edge(node):
            node.close()

    def colorChangedAction(self, color):
        """
        Color any selected nodes.

        params:
            color (list) - list of RGB values.
        """
        nodes = self.selectedNodes()
        for node in nodes:
            if self.is_node(node):
                node.dagnode.color = color
                node.update()

    def updateNodesAction(self, dagnodes):
        print 'GraphicsScene: updating %d dag nodes' % len(dagnodes)
    
    def validateConnection(self, src, dest, force=True):
        """
        When the mouse is released, validate the two connections.

        params:
            src   (Connection) - connection widget
            dest  (Connection) - connection widget
            force (bool)       - force the connection

        returns:
            (bool) - connection is valid.
        """
        if self.line:
            if not self.is_connection(src) or not self.is_connection(dest):
                print 'Error: source or destination objects are not Connection widgets.'
                return False

            if src.isInputConnection() or dest.isOutputConnection():
                print 'Error: invalid connection order.'
                return False

            # don't let the user connect input/output on the same node!
            if str(src.dagnode.id) == str(dest.dagnode.id):
                print 'Error: same node connection.'
                return False

            # check here to see if destination can take another connection
            if hasattr(dest.dagnode, 'valid_connection'):
                if not dest.dagnode.valid_connection:
                    if not force:
                        log.warning('Error: "%s" is not connectable.' % dest.connection_name)
                        return False

                    # remove the connected edge
                    dest_node = dest.node
                    # edges
                    edges = dest.connections.values()

                    for edge in edges:
                        log.warning('forcing edge removal: "%s"' % edge.name)
                        if self.graph.remove_edge(*edge.ids):
                            continue
                        log.warning('edge removal failed: "%s"' % edge.name)
                    return True

        return True

