#!/usr/bin/env python
import os
import re
import simplejson as json
import networkx as nx
from functools import partial
from PySide import QtCore

from .. import logger


class Graph(object):
    """
    Wrapper for NetowrkX graph
    """
    def __init__(self, parent, gui):

        self.viewport       = parent
        self.scene          = self.viewport.scene()
        
        self.network        = nx.DiGraph()

        self._copied_nodes  = []
        self._startdir      = gui._startdir
        self._default_name  = 'scene_graph_v001'            # default scene name

        # add the current scene attribute
        self.network.graph['scene'] = os.path.join(os.getenv('HOME'), 'graphs', '%s.json' % self._default_name)

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
    
    def getNodes(self):
        """
        Returns a weakref to all of the scene nodes

        returns:
            (weakref)
        """
        return self.scene.sceneNodes

    def getNode(self, name):
        """
        Get a node by name
        """
        if name in self.getNodes():
            return self.getNodes().get(name)
        return

    def selectedNodes(self):
        """
        Returns nodes selected in the graph

        returns:
            (list)
        """
        selected_nodes = []
        for nn in self.getNodes():
            node = self.getNode(nn)
            if node.isSelected():
                selected_nodes.append(node)
        return selected_nodes

    def addNode(self, node_type, **kwargs):
        """
        Creates a node in the parent graph

        returns:
            (object)  - created node
        """
        from SceneGraph import core
        from SceneGraph import ui
        reload(core)
        reload(ui)
        uuid = kwargs.get('UUID', None)
        name   = kwargs.get('name', 'node1')
        logger.getLogger().info('adding node "%s"' % name)
        pos    = kwargs.get('pos', [0,0])
        width = kwargs.get('width', 100)
        height = kwargs.get('height', 175)

        if not self.validNodeName(name):
            name = self._nodeNamer(name)

        dag = core.NodeBase(name=name, node_type=node_type, UUID=uuid, width=width, height=height)
        node = ui.NodeWidget(dag, UUID=str(dag.uuid), pos_x=pos[0], pos_y=pos[1], width=width, height=height)

        self.network.add_node(str(dag.uuid))
        nn = self.network.node[str(dag.uuid)]

        nn['name'] = name
        nn['node_type'] = node_type
        nn['pos_x'] = node.pos().x()
        nn['pos_y'] = node.pos().y()
        nn['width'] = node.width
        nn['height'] = node.height

        self.scene.addItem(node)
        node.setPos(pos[0], pos[1])
        return node

    def getNodeID(self, name):
        """
        Return the node given a name.

        params:
            name - (str) node name
        """
        result = None
        for node in self.network.nodes(data=True):
            uuid, data = node
            if 'name' in data:
                if data['name'] == name:
                    result = uuid
        return result 

    def getNode(self, name):
        """
        Return the node given a name.

        params:
            name - (str) node name
        """
        result = None
        for node in self.network.nodes(data=True):
            uuid, data = node
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
        if new_name in self._getNames():
            logger.getLogger().error('"%s" is not unique' % new_name)
            return

        node=self.scene.sceneNodes.pop(old_name)
        node.name = new_name
        self.scene.sceneNodes[node.name]=node
        node.update()
        return node

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
        pasted_nodes = []
        for node in self._copied_nodes:
            node.setSelected(False)
            new_name = self._nodeNamer(node.name)
            posx = node.pos().x() + node.width
            posy = node.pos().y() + node.height
            new_node = self.addNode('generic', name=new_name, pos=[posx, posy])
            new_node.addNodeAttributes(**node.getNodeAttributes())
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

    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.graph.clear()
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
    def nodeChangedAction(self, uuid, **kwargs):
        """
        Runs when a node is changed in the graph.
        """
        print '# Graph: node changed: ', uuid
        print kwargs
        
    #- Reading & Writing -----
    
    def write(self, filename):
        """
        Write the graph to scene file
        """
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        #graph_data = nxj.adjacency_data(self.network)
        fn = open(filename, 'w')
        json.dump(graph_data, fn, indent=4)
        fn.close()

    def read(self, filename):
        """
        Read a graph from a saved scene
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
            for node in nodes:                

                uuid = node.get('id')
                name = node.get('name')
                node_type = node.get('node_type', 'default')
                posx = node.get('pos_x')
                posy = node.get('pos_y')

                width = node.get('width')
                height = node.get('height')

                myNode = self.addNode(node_type, name=name, pos=[posx, posy], width=width, height=height)

        else:
            logger.getLogger().error('filename "%s" does not exist' % filename)

    #- CONNECTIONS ----
    def connect(self, source, dest):
        """
        Connect two nodes
        """
        source_node, source_conn = source.split('.')
        dest_node, dest_conn = dest.split('.')


