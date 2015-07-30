#!/usr/bin/env python
from PySide import QtCore
from SceneGraph import core
from . import node_widgets
from . import commands

log = core.log


class SceneHandler(QtCore.QObject):
    # graph -> scene
    nodesAdded          = QtCore.Signal(list)
    edgesAdded          = QtCore.Signal(list)
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
        from SceneGraph.icn import icons
        


        self.icons          = icons.ICONS
        self.ui             = parent.ui 
        self.graph          = None
        self._initialized   = False # set to false until the current scene has been read & built

        if parent is not None:
            self.ui.icons = self.icons
            self.ui.action_evaluate.triggered.connect(self.evaluate)
            if self.connectGraph(parent):
                self.connectSignals()
    
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

                    # load the node widgets from disk
                    self.graph.plug_mgr.load_widgets()

                    # start the autosave timer for 2min (120s x 1000)
                    self.ui.autosave_timer.start(30000)
                    return True
        return False

    def connectSignals(self):
        """
        Setup widget signals.
        """
        log.info('SceneHandler: connecting SceneHandler to Scene.') 
        # connect scene functions
        self.nodesAdded.connect(self.scene.addNodes)
        self.edgesAdded.connect(self.scene.addEdges)
        self.nodesUpdated.connect(self.scene.updateNodesAction)

        # connect graph functions
        self.dagNodesUpdated.connect(self.graph.updateDagNodes)

    def graphReadAction(self):
        """
        Graph -> Handler.
        """
        self._initialized = True

    def evaluate(self, dagnodes=[]):
        """
        Do cool shit here.
        """
        #self.updateStatus('evaluating...')
        if dagnodes:
            self.updateConsole('evaluating %d nodes' % len(dagnodes))
            return self.graph.evaluate(dagnodes=dagnodes)
        return

    def updateConsole(self, msg, clear=False, graph=False):
        """
        Send output to the console.

        params:
            msg (str) - message to send.
        """
        if clear:
            self.ui.consoleTextEdit.clear()
        handler = 'SceneHandler'
        if graph:
            handler = 'Graph'
        console_msg = '# [%s]: %s\n' % (handler, msg)
        self.ui.consoleTextEdit.insertPlainText(console_msg)

    def resetScene(self):
        """
        Resets the current scene.
        """
        self.updateConsole('resetting Scene...')
        self.scene.initialize()

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
    def dagNodesAdded(self, dagids):
        """
        Signal Graph -> GraphicsScene.

        params:
            dagnodes (list) - list of dagnode objects.
        """
        old_snapshot = self.graph.snapshot()
        self.updateConsole('adding %d nodes' % len(dagids))
        self.nodesAdded.emit(dagids)
        new_snapshot = self.graph.snapshot()
        self.undo_stack.push(commands.SceneNodesCommand(old_snapshot, new_snapshot, self.scene, msg='nodes added'))

    def dagEdgesAdded(self, edges):
        """
        Signal Graph -> GraphicsScene.

        params:
            edges (list) - list edge dictionaries.
        """
        if type(edges) not in [list, tuple]:
            edges = [edges,]

        for edge in edges:
            src_id = edge.get('src_id')
            dest_id = edge.get('dest_id')
            
            src_attr = edge.get('src_attr')
            dest_attr = edge.get('dest_attr')
            wgt = edge.get('weight', 1)

        self.edgesAdded.emit(edges)

    def dagUpdated(self, dagids):
        """
        Signal Graph -> GraphicsScene.
        """
        scene = self.scene
        widgets_to_remove = []
        for id in scene.scenenodes:
            widget = scene.scenenodes.get(id)
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
                node.close()

            if self.scene.is_node(node):
                node.close()

    def updateNodes(self, dagnodes):
        """
        Signal Graph -> GraphicsScene.
        """
        self.updateConsole('updating %d nodes...' % len(dagnodes))
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
        old_snapshot = self.graph.snapshot()      
        if not nodes:
            log.error('no nodes specified.')
            return False

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
        self.scene.update()
        # push to undo here

"""
def dagNodesRemoved(self, dagids):
    ntype = 'node'
    if type(dagids) is tuple:
        ntype = 'edge'
    
    if ntype == 'node':
        for id in dagids:
            if id in self.scene.scenenodes:
                widget = self.scene.scenenodes.pop(id)
                log.info('removing %s: "%s"' % (ntype, widget.name))
                self.updateConsole('removing %s: "%s"' % (ntype, widget.name))
                if widget and widget not in nodes_to_remove:
                    nodes_to_remove.append(widget)

    elif ntype == 'edge':
        for id in self.scene.scenenodes:
            widget = self.scene.scenenodes.get(id)
            if self.scene.is_edge(widget):
                if widget.ids == dagids:
                    self.updateConsole('removing %s: "%s"' % (ntype, widget.name))
                    if widget and widget not in nodes_to_remove:
                        nodes_to_remove.append(widget)
"""

