#!/usr/bin/env python
import os
import re
import weakref
import simplejson as json
import networkx as nx
from functools import partial
from PySide import QtCore, QtGui
from SceneGraph.core import log


class Graph(object):
    """
    Wrapper for NetworkX graph. Adds methods to query nodes,
    read & write graph files, etc.
    """
    def __init__(self, viewport=None):

        # multigraph allows for mutliple edges between nodes
        self.network        = nx.DiGraph()
        #self.network        = nx.MultiDiGraph()
        self.view           = None
        self.scene          = None       
        self.mode           = 'standalone'

        # grid/spacing attributes
        self.grid           = Grid(5, 5)

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
        if view is not None:

            log.debug('setting up GraphicsView...')
            self.view = view
            self.scene = view.scene

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
            log.warning('node path "%s" does not exist.' % path)
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
                    log.warning('cannot find "%s" module %s' % (node_name, node_mod))
                if not os.path.exists(node_data):
                    log.warning('cannot find "%s" metadata %s' % (node_name, node_data))
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
                    log.warning('invalid node "%s" ( %s )' % (node_attrs.get('name'), node_id))

        if self.network.edges():
            for edge in self.network.edges_iter(data=True):
                src_id, dest_id, edge_attrs = edge

                edge_id = edge_attrs.get('id')
                dagedge = self.getDagEdge(edge_id)
                src_name = self.getDagNode(UUID=src_id)
                dest_name = self.getDagNode(UUID=dest_id)

                if edge_id not in edge_ids:
                    log.warning('invalid edge "%s".' % dagedge.name)

        # scene nodes/edges
        if self.view:
            # remove any invalid edge widgets.
            invalid_edge_widgets = []
            edge_widgets = self.scene.sceneEdges.values()

            for edge in edge_widgets:
                dag_edge = edge.dagnode
                UUID = edge.UUID
                if UUID not in edge_ids:
                    if UUID in self.scene.sceneEdges:
                        self.scene.sceneEdges.pop(UUID)
                        print 'Graph.evaluate: removingItem'
                        self.scene.removeItem(edge)
                    else:
                        print 'somethin\' done fucked up' 

            # remove any invalid node widgets.
            invalid_node_widgets = []

            node_widgets = self.view.scene.sceneNodes.values()
            for node in node_widgets:
                dag_node = node.dagnode
                dag_name = dag_node.name
                UUID = node.UUID
                if UUID not in dag_ids:
                    self.view.scene.sceneNodes.pop(UUID)
                    print 'removing (4)'
                    self.view.scene.removeItem(node)

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

        return self.view.scene.sceneNodes.values()

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

    def getDagNodeNames(self):
        """
        Returns a list of all dag node names.

        returns:
            (list)
        """
        return [n.name for n in self.getDagNodes()]

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

        return self.view.scene.sceneEdges.values()

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

    def allConnections(self):
        """
        Returns a list of all dag connection strings.

        returns:
            (list)
        """
        return [edge.name for edge in self.getDagEdges()]

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
            log.debug('adding scene graph node "%s"' % name)
        else:
            log.debug('adding node "%s"' % name)
        
        # add the node to the networkx graph
        self.network.add_node(str(dag.UUID))
        nn = self.network.node[str(dag.UUID)]

        nn['name'] = name
        nn['node_type'] = node_type

        if self.view:
            self.view.scene.addItem(node)
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

            src_node, src_attr = src.split('.')
            dest_node, dest_attr = dest.split('.')

            # don't connect the same node
            if src_node == dest_node:
                log.debug('invalid connection: "%s", "%s"' % (src, dest))
                return


            conn_str = '%s,%s' % (src, dest)
            if conn_str in self.allConnections():
                log.debug('invalid connection: "%s"' % conn_str)
                return

            edge = core.EdgeBase(src, dest, id=UUID)

            src_name = edge.src_name
            src_id = self.getNodeID(src_name)
            dest_name = edge.dest_name
            dest_id = self.getNodeID(dest_name)

            edge.ids = (src_id, dest_id)
            log.info('connecting: "%s" > "%s"' % (src_name, dest_name))

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
                    self.view.scene.addItem(edge_widget)
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

        if UUID: 
            if UUID in self.dagedges:
                dag = self.dagedges.pop(UUID)
                
                try:
                    self.network.remove_edge(*dag.ids)
                    log.info('Removing edge: "%s"' % dag.name)
                except Exception, err:
                    log.error(err)
                    return False

                # TODO: edge doesn't disappear from the graph, but is
                # gone after save/reload
                self.evaluate()
                return True
            else:
                log.warning('UUID %s not in edge dictionary' % UUID)
        else:
            log.warning('No UUID')

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
        if not self.validNodeName(new_name):
            log.error('"%s" is not unique' % new_name)
            return

        UUID = self.getNodeID(old_name)
        self.network.node[UUID]['name'] = new_name
        for node in self.view.scene.sceneNodes.values():
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
        input_name, input_conn = input.split('.')
        output_name, output_conn = output.split('.')

        input_node = self.getDagNode(name=input_name)
        output_node = self.getDagNode(name=output_name)

        return self.addEdge(output, output)


    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.clear()
        self.view.scene.clear()
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
                log.debug('building node "%s"' % node_attrs.get('name'))

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

                log.debug('building edge: %s > %s' % (src_id, dest_id))
                self.addEdge(src=src_string, dest=dest_string, id=edge_id)

            if self.view:
                scene_pos = self.network.graph.get('view_center', (0,0))
                view_scale = self.network.graph.get('view_scale', (1.0, 1.0))
                self.view.resetTransform()

                self.view.setCenterPoint(scene_pos)
                self.view.scale(*view_scale)

            return self.setScene(filename)
        return 
    
    @property
    def version(self):
        """
        Returns the current scene version.
        """
        return self.network.graph.get('version', '0.0')

    @version.setter
    def version(self, val):
        """
        Set the current scene version.
        """        
        self.network.graph['version'] = str(val)
        return self.version

    #- Virtual ----
    def is_connected(self, node1, node2):
        """
        Returns true if two nodes are connected.

        params:
            node1 - (NodeBase) - first node to query.
            node2 - (NodeBase) - second node to query.

        returns:
            (bool) - nodes are connected.
        """
        dag_names = [node1.name, node2.name]
        for edge in self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            dagnode1 = self.getDagNode(UUID=src_id)
            dagnode2 = self.getDagNode(UUID=dest_id)

            if dagnode1.name in dag_names and dagnode2.name in dag_names:
                return True
        return False

    def outputs(self, node):
        """
        Returns a list of connections/connectable attributes.
        """
        return []

    def inputs(self, node):
        """
        Returns a list of connections/connectable attributes.
        """
        return []



class Array(object):
    """
    Represents an array.
    """
    def __init__(self, capacity, fillValue=None):
        """
        :param capacity: static size of the array
        :type capacity: int

        :param fillValue: value to hold each position
        :type fillValue: n/a
        """
        self._items = list()
        for count in range(capacity):
            self._items.append(fillValue)

    def __len__(self):
        return len(self._items)

    def __add__(self, x):
        tmp = Array(len(self)+x)
        for i in range(len(self)):
            tmp[i]=self[i]
        return tmp

    def __sub__(self, x):
        tmp = Array(len(self)-x)
        for i in range(len(self)-x):
            tmp[i]=self[i]
        return tmp

    def __str__(self):
        return str(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, item):
        self._items[index] = item


class Grid(object):
    """
    Represents a two-dimensional grid.
    """
    def __init__(self, rows, columns, fillValue=None):

        self._data      = Array(rows)
        self._row       = 0
        self._col       = 0
        self._current   = None

        for row in range(rows):
            self._data[row] = Array(columns, fillValue)

    def __repr__(self):
        return "\n"+self.__str__()

    def __str__(self):
        """
        returns a string representation of the grid.
        """
        result = """"""
        for row in range(self.height):
            for col in range(self.width):
                result += str(self._data[row][col]) + " "
            result += "\n"
        return result

    def __iter__(self):
        for r in range(self.height):
            for c in range(self.width):
                yield self.get(r, c)

    def __len__(self):
        return ( self.height * self.width )

    def items(self):
        return [x for x in self]

    def next(self):
        """
        Returns the next value in the grid.
        """
        val = self.get(self._row, self._col)
        if self._col < self.width-1:            
            self._col += 1
        else:
            if self._row < self.height-1:
                self._col = 0
                self._row+=1
        return val

    def find(self, val):
        """
        Get the graph coordinates of a specific value.

        params:
            val - (any) value to search for

        returns:
            (tuple) - coordiates of val in the grid.
        """
        result = ()
        for r in range(self.height):
            for c in range(self.width):
                if self.get(r, c) == val:
                    result = result + ((r, c),)
        return result

    def count(self, val):
        """
        Return the number of times the given value
        exists in the current graph.

        params:
            val - (any) value to search for

        returns:
            (int) - number of times this value exists.
        """
        return len(self.find(val))

    def fill(self):
        """
        Fill the grid with r:c values.
         (for debugging/testing)
        """
        for r in range(self.height):
            for c in range(self.width):
                val = '%d:%d' % (r,c)
                self.set(r, c, int(str(r) + str(c)))

    def reset(self):
        """
        Reset the grid coordinates.

        returns:
            (tuple) - current row-column coordinates
        """
        self._row = 0
        self._col = 0
        return self.pos

    @property
    def pos(self):
        """
        Return the current position in the grid.

        returns:
            (tuple) - current row-column coordinates
        """
        return (self._row, self._col)

    @property
    def height(self):
        """
        returns the number of rows
        """
        return len(self._data)

    @property
    def width(self):
        """
        returns the number of columns
        """
        return len(self._data[0])

    def __getitem__(self, index):
        """
        supports two-dimensional indexing
        with [row][column].
        """
        return self._data[index]

    def get(self, row, column):
        return self._data[row][column]

    def set(self, row, column, item):
        self._data[row][column] = item
