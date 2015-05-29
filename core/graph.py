#!/usr/bin/env python
import re
import simplejson as json

from .. import logger


class Graph(object):
    """
    Manages nodes in the parent graph
    """
    def __init__(self, parent, gui):

        self.viewport       = parent
        self.scene          = self.viewport.scene()
        self.root_node      = None
        self._copied_nodes  = []
        self._startdir      = gui._startdir
        self._default_name  = 'scene_graph_v001'            # default scene name
    
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

    def getNode(self, node_name):
        """
        Get a node by name
        """
        if node_name in self.getNodes():
            return self.getNodes().get(node_name)
        return

    def getRootNode(self):
        """
        Return the root node

        returns:
            (object)  - root node
        """
        return self.root_node

    def selectedNodes(self):
        """
        Returns nodes selected in the graph
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
        force = kwargs.get('force', False)
        node_name = kwargs.pop('name', 'node')
        if not force:
            node_name = self._nodeNamer(node_name)
        return self.scene.addNode(node_type, name=node_name, **kwargs)

    def createRootNode(self, hide=False, **kwargs):
        """
        Creates a root node

        params:
            hide      - (bool) hide the root node when created

        returns:
            (object)  - created node
        """
        import os
        sceneName = os.path.normpath(os.path.join(self._startdir, '%s.json' % self._default_name))
        self.root_node = self.scene.addNode('root', **kwargs)
        if hide:
            self.root_node.hide()
        self.root_node.addNodeAttributes(sceneName=sceneName)
        return self.root_node

    def removeNode(self, node):
        """
        Removes a node from the graph

        params:
            node    - (obj) node object

        returns:
            (object)  - removed node
        """
        node_name = node.node_name
        logger.getLogger().info('Removing node: "%s"' % node_name)
        self.scene.removeItem(node)
        if node_name in self.scene.sceneNodes.keys():
            return self.scene.sceneNodes.pop(node_name)
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
        node.node_name = new_name
        self.scene.sceneNodes[node.node_name]=node
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
            new_name = self._nodeNamer(node.node_name)
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
        from SceneGraph import core
        for item in self.scene.items():
            if isinstance(item, core.nodes.NodeBase):
                self.scene.removeItem(item)
            elif isinstance(item, core.nodes.LineClass):
                self.scene.removeItem(item)
        self.createRootNode()

    def _getNames(self):
        """
        Returns the names of all the current nodes
        """
        return sorted(self.getNodes().keys())

    def _nodeNamer(self, node_name):
        """
        Returns a legal node name
        """
        node_name = re.sub(r'[^a-zA-Z0-9\[\]]','_', node_name)
        if not re.search('\d+$', node_name):
            node_name = '%s1' % node_name
        all_names = self._getNames()
        if node_name in all_names:
            node_num = int(re.search('\d+$', node_name).group())
            node_base = node_name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):
                if '%s%d' % (node_base, i) not in all_names:
                    node_name = '%s%d' % (node_base, i)
                    break
        return node_name

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
                data.get('nodes').update(**{item.node_name:item.data})
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
                if node != 'Root':
                    myNode = self.addNode('generic', name=node, pos=[posx, posy], force=True)
                    node_attributes = dict()
                    if node_data.get(node):
                        for attr, val in node_data.get(node).iteritems():
                            attr = re.sub('^__', '', attr)
                            node_attributes.update({attr:val})
                        myNode.addNodeAttributes(**node_attributes)
                else:
                    # update root node
                    root_attributes = dict()
                    if not self.root_node:
                        self.createRootNode()
                    if node_data.get(node):
                        for attr, val in node_data.get(node).iteritems():
                            attr = re.sub('^__', '', attr)
                            root_attributes.update({attr:val})
                        self.root_node.addNodeAttributes(**root_attributes)
                    self.root_node.setX(posx)
                    self.root_node.setY(posy)

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


