#!/usr/bin/env python
from PySide import QtCore
from SceneGraph import core

log = core.log


class SceneHandler(QtCore.QObject):
    # graph -> scene
    nodesAdded        = QtCore.Signal(list)
    nodesRemoved      = QtCore.Signal(list)   # remove??
    nodesUpdated      = QtCore.Signal(list)
    graphNodesRenamed = QtCore.Signal(list)
    
    # scene -> graph
    sceneNodesUpdated    = QtCore.Signal(list)
    dagNodesUpdated   = QtCore.Signal(list)
    
    """
    SceneHandler class:
        - Signal the scene that nodes have been
          updated in the Graph.
        - Update the Graph when nodes are
          updated in the scene.
    """
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        
        self.ui    = parent.ui 
        self.graph = None

        if parent is not None:
            if self.connectGraph(parent):
                self.connectSignals()
    
    @property 
    def scene(self):
        return self.parentItem()

    def connectGraph(self, scene):
        """
        Connect the parent scenes' Graph object.

        params:
            scene (GraphicsScene) - current QGraphicsScene scene.

        returns:
            (bool) - connection was successful.
        """
        if hasattr(scene, 'graph'):            
            graph = scene.graph
            if graph.mode == 'standalone':
                self.graph = graph

                # make sure the graph doesn't have a handler instance.
                if not getattr(graph, 'handler'):
                    self.graph.handler=self
                    self.graph.mode = 'ui'
                    log.info('SceneHandler: connecting Graph...')
                    return True
        return False

    def connectSignals(self):
        """
        Setup widget signals.
        """
        log.info('SceneHandler: connecting SceneHandler to Scene.') 
        # connect scene functions
        self.nodesAdded.connect(self.scene.addNodes)
        self.nodesUpdated.connect(self.scene.updateNodesAction)

        # connect graph functions
        self.dagNodesUpdated.connect(self.graph.updateNetwork)

    def evaluate(self):
        """
        Do cool shit here.
        """
        return self.graph.evaluate()

    def updateNetworkAttributes(self):
        """
        Update the Graph.network with UI attributes.
        """
        preferences = dict()
        preferences.update(edge_type=self.ui.edge_type)
        preferences.update(use_gl=self.ui.use_gl)
        preferences.update(viewport_mode=self.ui.viewport_mode)
        preferences.update(render_fx=self.ui.render_fx)
        preferences.update(antialiasing=self.ui.antialiasing)
        return preferences

    #- Graph to Scene ----    
    def addNodes(self, dagids):
        """
        Signal Graph -> GraphicsScene.

        params:
            dagnodes (list) - list of dagnode objects.
        """
        num_nodes = len(dagids)
        if num_nodes > 1:
            node_type = '%ss' % node_type
        log.debug('SceneHandler: sending %d %s to scene...' % (num_nodes, node_type))
        self.nodesAdded.emit(dagids)

    def dagNodesRemoved(self, dagids):
        """
        Signal Graph -> GraphicsScene.
        """
        nodes_to_remove = []
        for id in dagids:
            if id in self.scene.scenenodes:
                widget = self.scene.scenenodes.pop(id)

        for w in widgets:
            self.scene.removeItem(w)

    def updateNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        log.info('SceneHandler: updating %d nodes...' % len(dagnodes))
        self.nodesUpdated.emit(dagnodes)

    def renameNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        log.info('SceneHandler: renaming %d nodes...' % len(dagnodes))
        self.graphNodesRenamed.emit(dagnodes)

    #- Scene to Graph ----
    def removeSceneNodes(self, nodes):
        """
        Signal GraphicsScene -> Graph.

        params:
            nodes (list) - list of node/edge widgets.
        """
        # connect to Graph        
        if not nodes:
            print '# no nodes passed.'
            return False

        items_to_remove = []
        for node in nodes:
            dagnode = node.dagnode
            if issubclass(type(dagnode), core.DagNode):
                # for nodes, query any connected edges from the networkx graph
                connected_edges = self.graph.connectedDagEdges(dagnode)

            if issubclass(type(dagnode), core.DagEdge):
                # for edges, we need to remove the edge widgets from 
                if node.breakConnections():
                    print '# breaking edge connections'

        for dtr in dagnodes_to_remove:
            if issubclass(type(dtr), core.DagNode):
                nname = dtr.name

            if issubclass(type(dtr), core.DagEdge):
                eid = dtr.id
                if self.graph.removeEdge(dtr):
                    print '# removing dag edge: %s' % eid

    def sceneNodesUpdatedAction(self, nodes):
        """
        Signal GraphicsScene -> Graph.
        """
        # Signal GraphicsScene -> SceneGraphUI.
        self.sceneNodesUpdated.emit(nodes)

        # connect to Graph
        dagnodes = [x.dagnode for x in nodes]
        self.dagNodesUpdatedAction(dagnodes)

    #- Atribute Editor ----
    def dagNodesUpdatedAction(self, dagnodes):
        """
        Signal AttributeEditor -> Graph.
        """
        self.dagNodesUpdated.emit(dagnodes)