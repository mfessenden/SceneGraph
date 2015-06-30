#!/usr/bin/env python
from PySide import QtCore
from SceneGraph.core import log


class WindowManager(QtCore.QObject):
    # graph -> scene
    nodesAdded      = QtCore.Signal(list)
    nodesRemoved    = QtCore.Signal(list)
    nodesUpdated    = QtCore.Signal(list)
    # scene -> graph
    widgetsUpdated  = QtCore.Signal(list)
    """
    Node Manager class:
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
    
    def connectSignals(self):
        """
        Setup widget signals.
        """
        log.info('WindowManager: connecting WindowManager to Scene.') 
        self.nodesAdded.connect(self.scene.addNodes)
        self.widgetsUpdated.connect(self.graph.updateGraph)

    def connectGraph(self, scene):
        """
        Connect the parent scenes' Graph object.

        params:
            scene (QGraphicsScene)
        """
        if hasattr(scene, 'graph'):
            graph = scene.graph
            if graph.mode == 'standalone':
                self.graph = graph
                self.graph.manager=self
                self.graph.mode = 'ui'
                log.info('WindowManager: connecting Graph...')
                return True
        return False
    
    #- Graph to Scene ----    
    def addNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        log.debug('WindowManager: sending %d nodes to scene...' % len(dagnodes))
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
        self.nodesUpdated.emit(dagnodes)

    #- Scene to Graph ----    
    def updateWidgets(self, dagnodes):
        """
        Signal GraphicsScene -> Graph.
        """
        self.widgetsUpdated.emit(dagnodes)

