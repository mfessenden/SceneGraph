#!/usr/bin/env python
from PySide import QtCore
from SceneGraph.core import log


class WindowManager(QtCore.QObject):
    # graph -> scene
    nodesAdded      = QtCore.Signal(list)
    nodesRemoved    = QtCore.Signal(list)
    nodesUpdated    = QtCore.Signal(list)
    nodesRenamed    = QtCore.Signal(list)
    # scene -> graph
    widgetsUpdated  = QtCore.Signal(list)
    dagNodesUpdated = QtCore.Signal(list)
    
    """
    WindowManager class:
        - Signal the scene that nodes have been
          updated in the Graph.
        - Update the Graph when nodes are
          updated in the scene.
    """
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        
        self.scene = parent
        self.graph = None

        if parent is not None:
            if self.connectGraph(parent):
                self.connectSignals()
    
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

                # make sure the graph doesn't have a manager instance.
                if not getattr(graph, 'manager'):
                    self.graph.manager=self
                    self.graph.mode = 'ui'
                    log.info('WindowManager: connecting Graph...')
                    return True
        return False

    def connectSignals(self):
        """
        Setup widget signals.
        """
        log.info('WindowManager: connecting WindowManager to Scene.') 
        self.nodesAdded.connect(self.scene.addNodes)
        self.dagNodesUpdated.connect(self.graph.updateGraph)
        self.nodesUpdated.connect(self.scene.updateNodesAction)

    def evaluate(self):
        """
        Do cool shit here.
        """
        pass

    #- Graph to Scene ----    
    def addNodes(self, dagnodes, edges=False):
        """
        Signal Graph -> GraphicsScene.

        params:
            dagnodes (list) - list of dagnode objects.
        """
        num_nodes = len(dagnodes)
        node_type = 'node'
        if edges:
            node_type = 'edge'

        if num_nodes > 1:
            node_type = '%ss' % node_type
        log.debug('WindowManager: sending %d %s to scene...' % (num_nodes, node_type))
        self.nodesAdded.emit(dagnodes)

    def removeNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        self.nodesRemoved.emit(dagnodes)

    def updateNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        log.info('WindowManager: updating %d nodes...' % len(dagnodes))
        self.nodesUpdated.emit(dagnodes)

    def renameNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        log.info('WindowManager: renaming %d nodes...' % len(dagnodes))
        self.nodesRenamed.emit(dagnodes)

    #- Scene to Graph ----
    def widgetsUpdatedAction(self, nodes):
        """
        Signal GraphicsScene -> Graph.
        """
        # connect to main UI
        self.widgetsUpdated.emit(nodes)

        # connect to Graph
        dagnodes = [x.dagnode for x in nodes]
        self.dagNodesUpdated.emit(dagnodes)

    #- Atribute Editor ----
    def dagNodesUpdatedAction(self, dagnodes):
        """
        Signal AttributeEditor -> Graph.
        """
        self.dagNodesUpdated.emit(dagnodes)