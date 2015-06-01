#!/usr/bin/env python
import os
import re
import simplejson as json
import networkx as nx

from .. import logger


class Graph(object):
    """
    Wrapper for NetowrkX graph
    """
    def __init__(self, parent, gui):

        self.viewport       = parent
        self.scene          = self.viewport.scene()
        
        self.network        = nx.Graph()

        self._copied_nodes  = []
        self._startdir      = gui._startdir
        self._default_name  = 'scene_graph_v001'            # default scene name

        # add the current scene attribute
        self.network.graph['scene'] = os.path.join(os.getenv('HOME'), 'graphs', '%s.json' % self._default_name)

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
        return self.scene.sceneNodes.keys()
    
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

    def addNode(self, name, node_type, **kwargs):
        """
        Creates a node in the parent graph

        returns:
            (object)  - created node
        """
        name = self._nodeNamer(name)
        return self.scene.addNode(node_type, name=name, **kwargs)

    def removeNode(self, node):
        """
        Removes a node from the graph

        params:
            node    - (obj) node object

        returns:
            (object)  - removed node
        """
        name = node.name
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

    def _getNames(self):
        """
        Returns the names of all the current nodes
        """
        return sorted(self.getNodes().keys())

    def _nodeNamer(self, name):
        """
        Returns a legal node name
        """
        name = re.sub(r'[^a-zA-Z0-9\[\]]','_', name)
        if not re.search('\d+$', name):
            name = '%s1' % name
        all_names = self._getNames()
        if name in all_names:
            node_num = int(re.search('\d+$', name).group())
            node_base = name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):
                if '%s%d' % (node_base, i) not in all_names:
                    name = '%s%d' % (node_base, i)
                    break
        return name

    def write(self, filename='/tmp/scene_graph_output.json'):
        """
        Write the graph to scene file
        """
        from SceneGraph import core
        data = {}
        data.update(nodes={})
        data.update(connections={})
        conn_idx = 0
        for item in self.scene.items():
            if isinstance(item, core.nodes.NodeBase):
                data.get('nodes').update(**{item.name:item.data})
            elif isinstance(item, core.nodes.LineClass):
                startItem = str(item.myStartItem)
                endItem = str(item.myEndItem)
                data.get('connections').update(**{'connection%d' % conn_idx: {'start':startItem, 'end':endItem}})
                conn_idx+=1
        fn = open(filename, 'w')
        output_data=data
        json.dump(output_data, fn, indent=4)
        fn.close()

    def read(self, filename='/tmp/scene_graph_output.json'):
        """
        Read a graph from a saved scene
        """
        import os
        if os.path.exists(filename):
            raw_data = open(filename).read()
            tmp_data = json.loads(raw_data, object_pairs_hook=dict)
            node_data = tmp_data.get('nodes', {})
            conn_data = tmp_data.get('connections', {})

            # BUILD NODES
            for node in node_data.keys():
                logger.getLogger().info('building node: "%s"' % node)
                posx = node_data.get(node).pop('x')
                posy = node_data.get(node).pop('y')

                myNode = self.addNode('generic', name=node, pos=[posx, posy], force=True)

                node_attributes = dict()
                if node_data.get(node):
                    for attr, val in node_data.get(node).iteritems():
                        attr = re.sub('^__', '', attr)
                        node_attributes.update({attr:val})
                    myNode.addNodeAttributes(**node_attributes)

                myNode.setX(posx)
                myNode.setY(posy)

            # BUILD CONNECTIONS
            for conn in conn_data.keys():
                cdata = conn_data.get(conn)
                start_str = cdata.get('start')
                end_str = cdata.get('end')
                logger.getLogger().info('connecting: %s >> %s' % (start_str, end_str))
                self.connectNodes(start_str, end_str)

            self.viewport.setSceneRect(self.scene.itemsBoundingRect())

        else:
            logger.getLogger().error('filename "%s" does not exist' % filename)

    #- CONNECTIONS ----
    def connect(self, source, dest):
        """
        Connect two nodes
        """
        source_node, source_conn = source.split('.')
        dest_node, dest_conn = dest.split('.')


