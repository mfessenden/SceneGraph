#!/usr/bin/env python
import os
import re
import simplejson as json
import networkx as nx
from functools import partial
from PySide import QtCore, QtGui

from .. import logger


class Graph(object):
    """
    Wrapper for NetworkX graph. Adds methods to query nodes,
    read & write graph files, etc.
    """
    def __init__(self, viewport=None):

        self.network        = nx.DiGraph()
        self.view           = None
        self.scene          = None      
        self.mode           = 'standalone'

        self._copied_nodes  = []
        self._default_name  = 'scene_graph_v001'            # default scene name

        # if we're in graphics mode
        self.initializeUI(viewport)

        # initialize the NetworkX graph
        self.initializeGraph()

    def __str__(self):
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        return json.dumps(graph_data, indent=5)

    def initializeGraph(self):
        """
        Add default attributes to the networkx graph.
        """
        # add the current scene attribute
        self.network.graph['scene'] = os.path.join(os.getenv('HOME'), 'graphs', '%s.json' % self._default_name)

    def initializeUI(self, view):
        """
        Setup the graphicsView.

        params:
            view - (object) QtGui.QGraphicsView
        """
        if view is not None:
            logger.getLogger().info('setting up GraphicsView...')
            self.view = view
            self.scene = view.scene()
            self.mode = 'ui'        

    #-- NetworkX Stuff -----
    def getScene(self):
        """
        Return the current graphs' scene attribute
        
        returns:
            (str)
        """
        return self.network.graph.get('scene', os.path.join(os.getenv('HOME'), 'graphs', '%s.json' % self._default_name))

    def setScene(self, scene):
        """
        Set the current scene value.

        params:
            scene (str)

        returns:
            scene (str)
        """
        self.network.graph['scene'] = scene
        return self.getScene()

    def listNodes(self):
        """
        Returns a list of nodes in the scene
        
        returns:
            (list)
        """
        return self.network.nodes(data=True)

    def listNodeNames(self):
        """
        Returns a list of node names in the scene
        
        returns:
            (list)
        """
        node_names = []
        if self.network.nodes():
            for node in self.network.nodes(data=True):
                id, data = node
                name = data.get('name')
                node_names.append(name)
        return node_names
    
    #- Scene Management -----
    def getSceneNodes(self):
        """
        Returns a list of all scene node widgets.

        returns:
            (list)
        """
        if self.mode != 'ui':
            return []

        return self.scene.sceneNodes.values()

    def getSceneNode(self, name):
        """
        Get a scene node by name.

        params:
            name - (str) name of node to query

        returns:
            (obj)
        """
        if self.mode != 'ui':
            return

        nodes = self.getSceneNodes()
        if nodes:
            for node in nodes:
                if node.dagnode.name == name:
                    return node
        return

    def getDagNodes(self):
        """
        Returns a list of all dag node.

        returns:
            (list)
        """
        if self.mode != 'ui':
            return

        nodes = self.getSceneNodes()
        if nodes:
            return [node.dagnode for node in self.getSceneNodes()]
        return []

    def getDagNode(self, name):
        """
        Return a dag node by name.

        params:
            name - (str) name of node to return

        returns:
            (obj)
        """
        if self.mode != 'ui':
            return
        dagNodes = self.getDagNodes()
        if dagNodes:
            for dag in dagNodes:
                if dag.name == name:
                    return dag
        return

    def selectedNodes(self):
        """
        Returns nodes selected in the graph

        returns:
            (list)
        """
        if self.mode != 'ui':
            return []
        selected_nodes = []
        for nn in self.getSceneNodes():
            if nn.isSelected():
                selected_nodes.append(nn)
        return selected_nodes

    def addNode(self, node_type, **kwargs):
        """
        Creates a node in the parent graph

        params:
            node_type - (str) type of node to create

        returns:
            (object)  - created node:
                          - dag in standalone mode
                          - node widget in ui mode
        """
        from SceneGraph import core
        from SceneGraph import ui
        reload(core)
        reload(ui)

        UUID = kwargs.pop('id', None)
        name   = kwargs.pop('name', 'node1')
        
        pos_x = kwargs.pop('pos_x', 0)
        pos_y = kwargs.pop('pos_y', 0)
        width = kwargs.pop('width', 120)
        height = kwargs.pop('height', 175)
        expanded = kwargs.pop('expanded', False)

        if not self.validNodeName(name):
            name = self._nodeNamer(name)

        dag = core.NodeBase(node_type, name=name, id=UUID, **kwargs)

        if self.mode == 'ui':
            node = ui.NodeWidget(dag, pos_x=pos_x, pos_y=pos_y, width=width, height=height, expanded=expanded)
            logger.getLogger().info('adding scene graph node "%s" at ( %f, %f )' % (name, pos_x, pos_y))
        else:
            logger.getLogger().info('adding node "%s"' % name)
        
        # add the node to the networkx graph
        self.network.add_node(str(dag.UUID))
        nn = self.network.node[str(dag.UUID)]

        nn['name'] = name
        nn['node_type'] = node_type

        if self.mode == 'ui':
            nn['pos_x'] = node.pos().x()
            nn['pos_y'] = node.pos().y()
            nn['width'] = node.width
            nn['height'] = node.height

            self.scene.addItem(node)
            #node.setPos(pos_x, pos_y)
            return node
        return dag

    def getNodeID(self, name):
        """
        Return the node given a name.

        params:
            name - (str) node name
        """
        result = None
        for node in self.network.nodes(data=True):
            UUID, data = node
            if 'name' in data:
                if data['name'] == name:
                    result = UUID
        return result 

    def getNode(self, name):
        """
        Return the node given a name.

        params:
            name - (str) node name
        """
        result = None
        for node in self.network.nodes(data=True):
            UUID, data = node
            if 'name' in data:
                if data['name'] == name:
                    result = node
        return result

    def removeNode(self, name):
        """
        Removes a node from the graph

        params:
            node    - (str) node name

        returns:
            (object)  - removed node
        """
        logger.getLogger().info('Removing node: "%s"' % name)

        self.scene.removeItem(node)
        if name in self.scene.sceneNodes.keys():
            return self.scene.sceneNodes.pop(name)
        return

    def renameNode(self, old_name, new_name):
        """
        Rename a node in the graph

        params:
            old_name    - (str) name to replace
            new_name    - (str) name to with

        returns:
            (object)  - renamed node
        """
        if not self.validNodeName(new_name):
            logger.getLogger().error('"%s" is not unique' % new_name)
            return

        UUID = self.getNodeID(old_name)
        self.network.node[UUID]['name'] = new_name
        for node in self.scene.sceneNodes.values():
            if node.dagnode.name == old_name:
                node.dagnode.name = new_name
                return node
        return

    def copyNodes(self, nodes):
        """
        Copy nodes to the copy buffer
        """
        self._copied_nodes = []
        self._copied_nodes = nodes
        return self._copied_nodes

    def pasteNodes(self):
        """
        Paste saved nodes
        """
        offset = 25
        pasted_nodes = []
        for node in self._copied_nodes:
            node.setSelected(False)
            new_name = self._nodeNamer(node.dagnode.name)
            posx = node.pos().x() + node.width
            posy = node.pos().y() + node.height
            new_node = self.addNode(node.dagnode.node_type, name=new_name, pos_x=node.pos().x() + offset, pos_y=node.pos().y() + offset)
            new_node.dagnode.addNodeAttributes(**node.dagnode.getNodeAttributes())
            new_node.setSelected(True)
            pasted_nodes.append(new_node)
        return pasted_nodes

    def connectNodes(self, output, input):
        """
        Connect two nodes via a "Node.attribute" string
        """
        from PySide import QtCore
        from SceneGraph import core
        input_name, input_conn = input.split('.')
        output_name, output_conn = output.split('.')
        input_node = self.getNode(input_name)
        output_node = self.getNode(output_name)

        input_conn_node  = input_node.getInputConnection(input_conn)
        output_conn_node = output_node.getOutputConnection(output_conn)

        if input_conn_node and output_conn_node:
            connectionLine = core.nodes.LineClass(output_conn_node, input_conn_node, QtCore.QLineF(output_conn_node.scenePos(), input_conn_node.scenePos()))
            self.scene.addItem(connectionLine)
            connectionLine.updatePosition()
        else:
            if not input_conn_node:
                logger.getLogger().error('cannot find an input connection "%s" for node "%s"' % (input_conn, input_node ))

            if not output_conn_node:
                logger.getLogger().error('cannot find an output connection "%s" for node "%s"' % (output_conn, output_node))


    # TODO: we need to store a weakref dict of dag nodes in the graph
    def updateGraph(self):
        """
        Update the networkx graph from the UI.
        """
        if self.mode != 'ui':
            return False

        for node in self.getDagNodes():
            self.network.node[str(node.UUID)].update(node.getNodeAttributes())

    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.clear()
        from SceneGraph import core
        for item in self.scene.items():
            if isinstance(item, core.nodes.NodeBase):
                self.scene.removeItem(item)
            elif isinstance(item, core.nodes.LineClass):
                self.scene.removeItem(item)

    def validNodeName(self, name):
        """
        Returns true if name not already assigned to a node.
        """
        return name not in self.listNodeNames()

    def _nodeNamer(self, name):
        """
        Returns a legal node name

        params:
            name (str) - node name to query
        """
        name = re.sub(r'[^a-zA-Z0-9\[\]]','_', name)
        if not re.search('\d+$', name):
            name = '%s1' % name

        while not self.validNodeName(name):
            node_num = int(re.search('\d+$', name).group())
            node_base = name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):
                if '%s%d' % (node_base, i) not in self.listNodeNames():
                    name = '%s%d' % (node_base, i)
                    break
        return name
    
    #- Actions ----
    def nodeChangedAction(self, UUID, **kwargs):
        """
        Runs when a node is changed in the graph.
        """
        print '# Graph: node changed: ', UUID
        print kwargs
        
    #- Reading & Writing -----
    
    def write(self, filename):
        """
        Write the graph to scene file
        """
        self.updateGraph()
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        #graph_data = nxj.adjacency_data(self.network)
        fn = open(filename, 'w')
        json.dump(graph_data, fn, indent=4)
        fn.close()
        return self.setScene(filename)

    def read(self, filename):
        """
        Read a graph from a saved scene.

        params:
            filename - (str) file to read
        """
        import os
        if os.path.exists(filename):
            raw_data = open(filename).read()
            tmp_data = json.loads(raw_data, object_pairs_hook=dict)
            self.network.clear()
            graph_data = tmp_data.get('graph', [])
            nodes = tmp_data.get('nodes', [])

            # build graph attributes
            for gdata in graph_data:
                if len(gdata):
                    self.network.graph[gdata[0]]=gdata[1]

            # build nodes from data
            for node_attrs in nodes:

                # get the node type
                node_type = node_attrs.pop('node_type', 'default')

                # add the dag node/widget
                node_widget = self.addNode(node_type, **node_attrs)

            return self.setScene(filename)

        else:
            logger.getLogger().error('filename "%s" does not exist' % filename)
        return 

    #- CONNECTIONS ----
    def connect(self, source, dest):
        """
        Connect two nodes
        """
        source_node, source_conn = source.split('.')
        dest_node, dest_conn = dest.split('.')


