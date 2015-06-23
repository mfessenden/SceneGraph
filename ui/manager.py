#!/usr/bin/env python
from PySide import QtCore


class WindowManager(QtCore.QObject):

    nodesAdded      = QtCore.Signal(list)
    nodesRemoved    = QtCore.Signal(list)
    nodesUpdated    = QtCore.Signal(list)

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
            self.connectGraph(parent)
    
    def connectGraph(self, scene):
        """
        Connect the parent scenes' Graph object.
        """
        if hasattr(scene, 'graph'):
            graph = scene.graph
            if graph.mode == 'standalone':
                self.graph = graph
                self.graph.manager=self
                self.graph.mode = 'ui'
                return True
        return False
    
    def addNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
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
