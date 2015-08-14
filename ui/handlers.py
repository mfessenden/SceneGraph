#!/usr/bin/env python
from PySide import QtCore

from SceneGraph import core
from SceneGraph.ui import node_widgets
from SceneGraph.ui import commands


log = core.log


class SceneEventHandler(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
   
        self.ui             = None 
        self.graph          = None
        self._initialized   = False # set to false until the current scene has been read & built

        if parent is not None:
            self.ui = parent.ui
            self.ui.action_evaluate.triggered.connect(self.evaluate)
            self.ui.action_update_graph.triggered.connect(self.graphUpdated)
            
            if not self.connectGraph(parent):
                log.error('cannot connect SceneEventHandler to Graph.')

    def updateStatus(self, msg, level='info'):
        self.ui.updateStatus(msg, level=level)

    @property 
    def scene(self):
        return self.parent()

    @property 
    def undo_stack(self):
        return self.ui.undo_stack

    def connectGraph(self, scene):
        """
        Connect the parent scenes' Graph object.

        :param SceneGraph.ui.graphics.GraphicsScene scene: current QGraphicsScene scene.

        :returns: connection was successful.
        :rtype: bool
        """
        if hasattr(scene, 'graph'):            
            graph = scene.graph
            if graph.mode == 'standalone':
                self.graph = graph

                # connect graph signals
                self.graph.nodesAdded += self.nodesAddedEvent
                self.graph.edgesAdded += self.edgesAddedEvent
                self.graph.graphUpdated += self.graphUpdated

                self.graph.mode = 'ui'
                log.info('SceneHandler: connecting Graph...')

                # load the node widgets from disk
                self.graph.plug_mgr.load_widgets()

                # start the autosave timer for 2min (120s x 1000)
                self.ui.autosave_timer.start(30000)
                return True
        return False

    #- Events ----

    def evaluate(self):
        return True

    def nodesAddedEvent(self, graph, ids):
        """
        Callback method.

        :param list ids: DagNode ids.
        """
        self.scene.addNodes(ids)

    def edgesAddedEvent(self, graph, edges):
        """
        Callback method.
        """
        self.scene.addEdges(edges)

    def removeSceneNodes(self, nodes):
        """
        Signal Graph when the scene is updated.

        :param list nodes: list of widgets.
        """
        # connect to Graph
        old_snapshot = self.graph.snapshot()      
        if not nodes:
            log.error('no nodes specified.')
            return False

        #print '# DEBUG: removing scene nodes...'
        for node in nodes:
            if self.scene:
                if self.scene.is_node(node):
                    dag = node.dagnode
                    nid = dag.id
                    if self.graph.remove_node(nid):
                        log.debug('removing dag node: %s' % nid)
                    node.close()

            if self.scene.is_edge(node):
                if node.ids in self.graph.network.edges():
                    log.debug('removing edge: %s' % str(node.ids))
                    self.graph.remove_edge(*node.ids)
                node.close()
        new_snapshot = self.graph.snapshot()
        self.undo_stack.push(commands.SceneNodesCommand(old_snapshot, new_snapshot, self.scene, msg='nodes deleted'))

    def graphUpdated(self, *args):
        """
        Signal when the graph updates.
        """
        widgets_to_remove = []
        for id in self.scene.scenenodes:
            widget = self.scene.scenenodes.get(id)
            if self.scene.is_node(widget):
                if widget.id not in self.graph.network.nodes():
                    widgets_to_remove.append(widget)

            if self.scene.is_edge(widget):
                if widget.ids not in self.graph.network.edges():
                    widgets_to_remove.append(widget)

        for node in widgets_to_remove:            
            if self.scene.is_edge(node):
                src_conn = node.source_item
                dest_conn = node.dest_item
                print '# DEBUG: removing edge: ', node 
                node.close()

            if self.scene.is_node(node):
                print '# DEBUG: removing node: ', node
                node.close()

    def dagNodesUpdatedEvent(self, dagnodes):
        """
        Update dag nodes from an external UI.
        """
        if dagnodes:
            print '# DEBUG: dag nodes updated: ', [node.name for node in dagnodes]