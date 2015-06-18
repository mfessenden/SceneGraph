#!/usr/bin/env python
import os
import re
import weakref
import simplejson as json
import networkx as nx
from functools import partial
from PySide import QtCore, QtGui
from . import logger

log = logger.myLogger()


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

        # attribute for dynamically loaded nodes
        self._node_types    = dict()

        self.dagnodes       = dict()
        self.dagedges       = dict()

        # temp attributes
        self._copied_nodes  = []

        # setup node types
        self.initializeNodeTypes()

        # if we're in graphics mode
        self.initializeUI(viewport)

        # initialize the NetworkX graph
        self.initializeGraph()

    def __str__(self):
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        return json.dumps(graph_data, indent=5)

    def initializeUI(self, view):
        """
        Setup the graphicsView.

        params:
            view - (object) QtGui.QGraphicsView
        """
        from SceneGraph.core import log
        if view is not None:
            log.info('setting up GraphicsView...')
            self.view = view
            self.scene = view.scene()

    def initializeNodeTypes(self):
        """
        Scan the dag nodes directory for node types.
        """
        from SceneGraph.options import SCENEGRAPH_NODE_PATH
        self._node_types = self.scanNodeTypes(SCENEGRAPH_NODE_PATH)

        if 'SCENEGRAPH_EXT_NODES' in os.environ:
            ext_node_path = os.getenv('SCENEGRAPH_EXT_NODES')
            if os.path.exists(ext_node_path):

                self._node_types.update(**self.scanNodeTypes(ext_node_path))
        return self._node_types

    def scanNodeTypes(self, path):
        """
        Scan the given directory for node types.
        """
        nodes = dict()
        if not os.path.exists(path):
            print '# WARNING: node path "%s" does not exist.' % path
            return nodes

        #print '# searching for nodes in: "%s"' % path
        for fn in os.listdir(path):
            node_name = os.path.splitext(os.path.basename(fn))[0]
            node_mod = os.path.join(path, '%s.py' % node_name)
            node_data = os.path.join(path, '%s.mtd' % node_name)
            if os.path.exists(node_mod) and os.path.exists(node_data):
                #print '# loading node type "%s"' % node_name
                node_attrs = dict()
                node_attrs['module'] = node_mod
                node_attrs['metadata'] = node_data
                nodes[node_name]=node_attrs
            else:
                if not os.path.exists(node_mod):
                    print '# WARNING: cannot find "%s" module %s' % (node_name, node_mod)
                if not os.path.exists(node_data):
                    print '# WARNING: cannot find "%s" metadata %s' % (node_name, node_data)
        return nodes

    def initializeGraph(self, scene=None):
        """
        Add default attributes to the networkx graph.
        """
        from SceneGraph.options import VERSION_AS_STRING
        self.network.graph['version'] = VERSION_AS_STRING
        self.network.graph['scene'] = scene
        self.network.graph['temp_scene'] = os.path.join(os.getenv('TMPDIR'), 'scenegraph_temp.json')
        self.network.graph['environment'] = 'command_line'

    def updateGraph(self):
        """
        Update the networkx graph from the UI.

        TODO: we need to store a weakref dict of dag nodes in the graph
        """
        if not self.view:
            return False

        for node in self.getDagNodes():
            nid = str(node.UUID)
            if nid in self.network.nodes():
                self.network.node[nid].update(node.getNodeAttributes())

    def evaluate(self, verbose=False):
        """
        Evaluate the graph.
        """
        import time
        tstart=time.time()

        dagnodes = self.getDagNodes()
        dagedges = self.getDagEdges()

        dag_ids = [d.UUID for d in dagnodes]
        edge_ids = self.getEdgeIDs()

        if self.network.nodes():
            for node in self.network.nodes_iter(data=True):
                node_id, node_attrs = node
                if node_id not in dag_ids:
                    print '# WARNING: invalid node "%s".' % node_attrs.get('name')

        if self.network.edges():
            for edge in self.network.edges_iter(data=True):
                src_id, dest_id, edge_attrs = edge

                edge_id = edge_attrs.get('id')
                dagedge = self.getDagEdge(edge_id)
                src_name = self.getDagNode(UUID=src_id)
                dest_name = self.getDagNode(UUID=dest_id)

                if edge_id not in edge_ids:
                    print '# WARNING: invalid edge "%s".' % dagedge.name

        # scene nodes/edges
        if self.view:
            # remove any invalid edge widgets.
            invalid_edge_widgets = []
            edge_widgets = self.scene.sceneEdges.values()

            for edge in edge_widgets:
                dag_edge = edge.dagnode
                UUID = edge.UUID
                if UUID not in edge_ids:
                    #print '# WARNING: invalid edge widget: "%s" ' % str(edge)
                    if UUID in self.scene.sceneEdges:
                        self.scene.sceneEdges.pop(UUID)
                    self.scene.removeItem(edge)

            # remove any invalid node widgets.
            invalid_node_widgets = []

            node_widgets = self.scene.sceneNodes.values()
            for node in node_widgets:
                dag_node = node.dagnode
                dag_name = dag_node.name
                UUID = node.UUID
                if UUID not in dag_ids:
                    #print '# WARNING: invalid node widget: "%s" ' % dag_name
                    self.scene.sceneNodes.pop(UUID)
                    self.scene.removeItem(node)

        tend=time.time()
        if verbose:
            readTime, tstart = tend - tstart, tend
            print '# Graph evaluated in %1.2f seconds. (%d items)' %  (readTime, len(dagnodes) + len(dagedges))

    def node_types(self):
        """
        Returns a list of node types.
        """
        return self._node_types.keys()

    #-- NetworkX Stuff -----
    def getScene(self):
        """
        Return the current graphs' scene attribute
        
        returns:
            (str)
        """
        return self.network.graph.get('scene', None)

    def setScene(self, scene=None):
        """
        Set the current scene value.

        params:
            scene (str)

        returns:
            scene (str)
        """
        tmp_dir = os.getenv('TMPDIR')
        if tmp_dir not in scene:
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
        if not self.view:
            return []

        return self.scene.sceneNodes.values()

    def getSceneNode(self, name=None, UUID=None):
        """
        Get a scene node by name.

        params:
            name - (str) name of node to query

        returns:
            (obj)
        """
        if not self.view:
            return

        nodes = self.getSceneNodes()
        if nodes:
            for node in nodes:
                if node.dagnode.name == name or node.dagnode.UUID == UUID:
                    return node
        return

    def getDagNodes(self):
        """
        Returns a list of all dag nodes.

        returns:
            (list)
        """
        return self.dagnodes.values()

    def getDagNode(self, name=None, UUID=None):
        """
        Return a dag node by name.

        params:
            node - (str) name of node to return

        returns:
            (obj)
        """

        if self.dagnodes:
            for NUUID in self.dagnodes:
                dag = self.dagnodes.get(NUUID)
                if dag and dag.name == name or dag.UUID == UUID:
                    return dag
        return

    def selectedNodes(self):
        """
        Returns nodes selected in the graph

        returns:
            (list)
        """
        if not self.view:
            return []

        selected_nodes = []
        for nn in self.getSceneNodes():
            if nn.isSelected():
                selected_nodes.append(nn)
        return selected_nodes

    def getSceneEdges(self):
        """
        Returns a list of all scene edge widgets.

        returns:
            (list)
        """
        if not self.view:
            return []

        return self.scene.sceneEdges.values()

    def getSceneEdge(self, conn=None, UUID=None):
        """
        Get a scene edge.

        params:
            conn - (str) connection string (ie: "node1.output,node2.input")
            UUID - (str) edge UUID

        returns:
            (obj)
        """
        if not self.view:
            return

        edges = self.getSceneEdges()
        if edges:
            for edge in edges:
                if conn is not None:
                    if edge.dagnode.name == conn:
                        return edge

                if UUID is not None:
                    if edge.dagnode.UUID == UUID:
                        return edge
        return

    def getDagEdges(self):
        """
        Returns a list of all dag edges.

        returns:
            (list)
        """
        return self.dagedges.values()

    def getEdgeIDs(self):
        """
        Returns a list of all edges in the network.
        """
        ids = []
        for edge in self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            ids.append(attrs.get('id'))
        return ids

    def getDagEdge(self, conn):
        """
        Return a dag edge by name.

        params:
            conn - (str) connection string (ie: "node1.output,node2.input")

        returns:
            (obj)
        """
        if conn in self.dagedges:
            return self.dagedges.get(conn)
        
        if self.dagedges:
            for UUID in self.dagedges:
                dag = self.dagedges.get(UUID)
                if dag and dag.name == conn:
                    return dag
        return

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
        reload(core)
        name   = kwargs.pop('name', 'node1')

        if not self.validNodeName(name):
            name = self._nodeNamer(name)

        dag = core.NodeBase(node_type, name=name, **kwargs)
        self.dagnodes[str(dag.UUID)] = dag

        if self.view:
            from SceneGraph import ui
            reload(ui)
            #node = ui.NodeWidget(dag, pos_x=pos_x, pos_y=pos_y, width=width, height=height, expanded=expanded)
            node = ui.NodeWidget(dag)
            log.info('adding scene graph node "%s"' % name)
        else:
            log.info('adding node "%s"' % name)
        
        # add the node to the networkx graph
        self.network.add_node(str(dag.UUID))
        nn = self.network.node[str(dag.UUID)]

        nn['name'] = name
        nn['node_type'] = node_type

        if self.view:
            self.scene.addItem(node)
            node.setPos(dag.pos_x, dag.pos_y)
            node.setSelected(True)
            self.view.parent.updateAttributeEditor(node.dagnode)

        return dag

    def removeNode(self, name, UUID=None):
        """
        Removes a node from the graph

        params:
            node    - (str) node name

        returns:
            (object)  - removed node
        """
        if UUID is None:
            UUID = self.getNodeID(name)
        if UUID and UUID in self.dagnodes:
            from SceneGraph.core import log
            log.info('Removing node: "%s"' % name)
            if UUID in self.dagnodes:
                self.dagnodes.pop(UUID)

            if UUID in self.network.nodes():
                self.network.remove_node(UUID)
            self.evaluate()
            return True

        return False

    def addEdge(self, src, dest, **kwargs):
        """
        Add an edge connecting two nodes.

          src = source node string, ie "node1.output"
          dest = source node string, ie "node1.output"
        """
        UUID = kwargs.pop('id', None)
        if src is None or dest is None:
            return False

        if src and dest:
            from SceneGraph import core
            reload(core)

            edge = core.EdgeBase(src, dest, id=UUID)

            src_name = edge.src_name
            src_id = self.getNodeID(src_name)
            dest_name = edge.dest_name
            dest_id = self.getNodeID(dest_name)

            edge.ids = (src_id, dest_id)
            print '# Graph.addEdge: connecting: "%s.%s"' % (src_name, dest_name)

            self.network.add_edge(src_id, 
                dest_id,
                id=str(edge.UUID),
                src_id=src_id,
                dest_id=dest_id,
                src_attr=edge.src_attr, 
                dest_attr=edge.dest_attr)

            self.dagedges[str(edge.UUID)] = edge
            #print '# Graph.addEdge: new edge ID: %s' % str(edge.UUID)

            if self.view:
                from SceneGraph import ui
                reload(ui)

                # get the widgets
                src_widget = self.getSceneNode(name=src_name)
                dest_widget= self.getSceneNode(name=dest_name)

                if src_widget and dest_widget:
                    edge_widget = ui.EdgeWidget(src_widget.output_widget, dest_widget.input_widget, edge=edge)
                    self.scene.addItem(edge_widget)
            return edge

    def removeEdge(self, conn=None, UUID=None): 
        """
        Removes an edge from the graph

        params:
            UUID    - (str) edge UUID
            conn    - (str) connection string (ie "node1.output,node2.input")

        returns:
            (object)  - removed edge
        """
        if UUID is None:
            if conn is None:
                log.error('please enter a valid edge connection string or UUID')
                return False
            UUID = self.getEdgeID(conn)

        if UUID and UUID in self.dagedges:
            dag = self.dagedges.pop(UUID)
            log.info('Removing edge: "%s"' % dag.name)
            try:
                self.network.remove_edge(*dag.ids)
            except:
                pass

            self.evaluate()
            return True
        return False

    def getNodeID(self, name):
        """
        Return the node given a name.

        params:
            name - (str) node ID
        """
        result = None
        for node in self.network.nodes(data=True):
            UUID, data = node
            if 'name' in data:
                if data['name'] == name:
                    result = str(UUID)
        return result 

    def getEdgeID(self, conn):
        """
        Return the edge given a connection.

            connection: "node1.output,node2.input"

        params:
            name - (str) edge ID
        """
        result = None
        for data in self.network.edges(data=True):
            src_id = data[0]
            dest_id = data[1]
            edge_attrs = data[2]

            src_id = edge_attrs.get('src_id')
            dest_id = edge_attrs.get('dest_id')

            src_attr = edge_attrs.get('src_attr')
            dest_attr = edge_attrs.get('dest_attr')

            src_node = self.getDagNode(UUID=src_id)
            dest_node = self.getDagNode(UUID=dest_id)

            if src_node is None or dest_node is None:
                return result

            edge_id = str(edge_attrs.get('id'))
            
            conn_str = '%s.%s,%s.%s' % (src_node.name, src_attr, dest_node.name, dest_attr)
            # todo: do some string cleanup here
            if conn_str == conn:
                result = edge_id
        return result 

    def connectedEdges(self, nodes):
        """
        Returns a list of all connected edges to the given node(s).

        params:
            nodes - (str) or (list)

        returns:
            (list) - list of connected edges.
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]
        result = self.network.in_edges(nbunch=[self.getNodeID(n) for n in nodes], data=True)
        result.extend(self.network.out_edges(nbunch=[self.getNodeID(n) for n in nodes], data=True))
        return result

    def in_edges(self, nodes):
        """
        Returns a list of all incoming edges to the given node(s).

        params:
            nodes - (str) or (list)

        returns:
            (list
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]
        return self.network.in_edges(nbunch=[self.getNodeID(n) for n in nodes], data=True)

    def out_edges(self, nodes):
        """
        Returns a list of all outgoing edges to the given node(s).

        params:
            nodes - (str) or (list)

        returns:
            (list
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]
        return self.network.out_edges(nbunch=[self.getNodeID(n) for n in nodes], data=True)

    def renameNode(self, old_name, new_name):
        """
        Rename a node in the graph

        params:
            old_name    - (str) name to replace
            new_name    - (str) name to with

        returns:
            (object)  - renamed node
        """
        from SceneGraph.core import log
        if not self.validNodeName(new_name):
            log.error('"%s" is not unique' % new_name)
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
            # dag node
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
                core.log.error('cannot find an input connection "%s" for node "%s"' % (input_conn, input_node ))

            if not output_conn_node:
                core.log.error('cannot find an output connection "%s" for node "%s"' % (output_conn, output_node))

    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.clear()
        self.scene.clear()
        self.dagnodes = dict()
        self.dagedges = dict()

    def downstream(self, node):
        """
        Return downstream nodes from the given node.
        """
        nid = None
        if node not in self.network.nodes():
            if self.getNodeID(node):
                nid = self.getNodeID(node)
        else:
            nid = node

        if nid is not None:
            #return self.network.successors(nid)
            return nx.descendants(self.network, nid)            
        return []

    def upstream(self, node):
        """
        Return upstream nodes from the given node.
        """
        nid = None
        if node not in self.network.nodes():
            if self.getNodeID(node):
                nid = self.getNodeID(node)
        else:
            nid = node

        if nid is not None:
            #return self.network.predecessors(nid)
            return nx.ancestors(self.network, nid)  
        return []

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
        from SceneGraph.core import log

        if os.path.exists(filename):
            raw_data = open(filename).read()
            tmp_data = json.loads(raw_data, object_pairs_hook=dict)
            self.network.clear()
            graph_data = tmp_data.get('graph', [])
            nodes = tmp_data.get('nodes', [])
            edges = tmp_data.get('links', [])
            
            # update graph attributes
            for gdata in graph_data:
                if len(gdata):
                    self.network.graph[gdata[0]]=gdata[1]

            # build nodes from data
            for node_attrs in nodes:
                # get the node type
                node_type = node_attrs.pop('node_type', 'default')

                # add the dag node/widget
                dag_node = self.addNode(node_type, **node_attrs)
                log.info('building node "%s"' % node_attrs.get('name'))

            for edge_attrs in edges:
                edge_id = edge_attrs.get('id')
                src_id = edge_attrs.get('src_id')
                dest_id = edge_attrs.get('dest_id')

                src_attr = edge_attrs.get('src_attr')
                dest_attr = edge_attrs.get('dest_attr')

                src_dag_node = self.getDagNode(UUID=src_id)
                dest_dag_node = self.getDagNode(UUID=dest_id)

                src_string = '%s.%s' % (src_dag_node.name, src_attr)
                dest_string = '%s.%s' % (dest_dag_node.name, dest_attr)

                log.info('building edge: %s > %s' % (src_id, dest_id))
                self.addEdge(src=src_string, dest=dest_string, id=edge_id)

            return self.setScene(filename)
        return 

    #- CONNECTIONS ----
    def connect(self, source, dest):
        """
        Connect two nodes
        """
        source_node, source_conn = source.split('.')
        dest_node, dest_conn = dest.split('.')


