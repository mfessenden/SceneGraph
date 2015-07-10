#!/usr/bin/env python
from PySide import QtCore
from SceneGraph import core

log = core.log


class SceneHandler(QtCore.QObject):
    # graph -> scene
    nodesAdded          = QtCore.Signal(list)
    nodesRemoved        = QtCore.Signal(list)   # remove??
    nodesUpdated        = QtCore.Signal(list)
    graphNodesRenamed   = QtCore.Signal(list)
    
    # scene -> graph
    sceneNodesUpdated   = QtCore.Signal(list)
    dagNodesUpdated     = QtCore.Signal(list)
    
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
        return self.parent()

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
        self.dagNodesUpdated.connect(self.graph.updateDagNodes)

    def evaluate(self, dagnodes=[]):
        """
        Do cool shit here.
        """
        return self.graph.evaluate(dagnodes=dagnodes)

    def updateGraphAttributes(self):
        """
        Returns a dictionary of current UI preferences.
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
        self.nodesAdded.emit(dagids)

    def dagNodesRemoved(self, dagids):
        """
        Signal Graph -> GraphicsScene.
        """
        nodes_to_remove = []
        for id in dagids:
            if id in self.scene.scenenodes:
                widget = self.scene.scenenodes.pop(id)
                log.info('removing "%s"' % widget.name)
                if widget and widget not in nodes_to_remove:
                    nodes_to_remove.append(widget)

        for node in nodes_to_remove:
            self.scene.removeItem(node)

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
            log.error('no nodes specified.')
            return False

        for node in nodes:
            dag = node.dagnode
            nid = dag.id

            if issubclass(type(dag), core.DagNode):
                if self.graph.remove_node(nid):
                    log.debug('removing dag node: %s' % nid)
            if issubclass(type(dag), core.DagEdge):
                if self.graph.remove_edge(nid):
                    log.debug('removing dag edge: %s' % nid)

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
