#!/usr/bin/env python
import os
import re
import weakref
import simplejson as json
import networkx as nx
from functools import partial

from SceneGraph.core import log, DagNode, DagEdge


class Graph(object):
    """
    Wrapper for NetworkX graph. Adds methods to query nodes,
    read & write graph files, etc.
    """
    def __init__(self, *args, **kwargs):

        self.network        = nx.DiGraph()
        #self.network        = nx.MultiDiGraph() # mutliple edges between nodes
        
        self.mode           = 'standalone'
        self.grid           = Grid(5, 5)
        self.manager        = None

        # attributes for current nodes/dynamically loaded nodes
        self._node_types     = dict() 
        self.dagnodes        = dict()

        # setup node types
        self.initializeNodeTypes()

        # initialize the NetworkX graph
        self.initializeGraph()

        for arg in args:
            if os.path.exists(arg):
                self.read(arg)
                continue

    def __str__(self):
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        return json.dumps(graph_data, indent=5)

    def initializeGraph(self, scene=None):
        """
        Add default attributes to the networkx graph.
        """
        from SceneGraph.options import VERSION_AS_STRING
        self.network.graph['version'] = VERSION_AS_STRING
        self.network.graph['scene'] = scene
        self.network.graph['temp_scene'] = os.path.join(os.getenv('TMPDIR'), 'scenegraph_temp.json')
        self.network.graph['environment'] = 'command_line'

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

    def evaluate(self, verbose=False):
        """
        Evaluate the graph.
        """
        import time
        tstart=time.time()

        dagnodes = self.getNodes()
        dagedges = self.getEdges()

        dag_ids = [str(d.id) for d in dagnodes]
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
                dagedge = self.getEdge(edge_id)
                src_name = self.getNode(src_id)
                dest_name = self.getNode(dest_id)

                if edge_id not in edge_ids:
                    log.warning('invalid edge "%s".' % dagedge.name)

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
        if self.network.nodes(data=True):
            for node in self.network.nodes(data=True):
                id, data = node
                name = data.get('name')
                node_names.append(name)
        return node_names
    
    def getNodes(self):
        """
        Returns a list of all dag nodes.

        returns:
            (list) - list of DagNode objects.
        """
        nodes = []
        for node in  self.network.nodes(data=True):
            UUID, attrs = node
            if UUID in self.dagnodes:
                nodes.append(self.dagnodes.get(UUID))
        return nodes

    def getNodeNames(self):
        """
        Returns a list of all dag node names.

        returns:
            (list)
        """
        return [n.name for n in self.getNodes()]

    def getNode(self, *args):
        """
        Return a dag node by name.

        params:
            node - (str) name of node to return

        returns:
            (obj)
        """
        nodes=[]
        for arg in args:
            if arg in self.dagnodes:
                nodes.append(self.dagnodes.get(arg))

        if self.dagnodes:
            for UUID in self.dagnodes:
                node = self.dagnodes.get(UUID)
                if node and node.name in args or str(node.id) in args:
                    nodes.append(node)
        return nodes

    def getEdges(self):
        """
        Returns a list of all dag edges.

        returns:
            (list) - list of DagEdge objects.
        """
        edges = []
        for edge in  self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            UUID = attrs.get('id')
            if UUID in self.dagnodes:
                edges.append(self.dagnodes.get(UUID))
        return edges

    def allNodes(self):
        """
        Returns a list of all dag connection strings.

        returns:
            (list)
        """
        return [node.name for node in self.getNodes()]

    def allConnections(self):
        """
        Returns a list of human-readable edge
        connections.

        returns:
            (list) - list of connection strings. 
        """
        connections = []
        for edge in self.getEdges():

            src_attr = edge.get('src_attr')
            dest_attr = edge.get('dest_attr')

            src_nodes = self.getNode(edge.get('src_id'))
            dest_nodes = self.getNode(edge.get('dest_id'))

            # query node names
            if src_nodes and dest_nodes:
                src_node = src_nodes[0]
                dest_node = dest_nodes[0]
                connections.append('%s.%s,%s.%s' % (src_node.name, src_attr, 
                                                    dest_node.name, dest_attr))
        return connections

    def parseEdgeName(self, edge):
        """
        Parse an edge name string into human-readable format.
        Since we don't store node names in edges (because UUIDs are immutable),
        we need to parse the UUID into a node name.

        params:
            edge - (DagEdge) edge instance

        returns:
            (str) - edge connection string.
        """
        src_nodes = self.getNode(edge.src_id)
        dest_nodes = self.getNode(edge.dest_id)

        if not src_nodes or not dest_nodes:
            log.error('invalid node ids in edge "%s"' % edge.name)
            return 

        src_name = src_nodes[0].name
        src_str = '%s.%s' % (src_name, edge.src_attr)
        dest_name = dest_nodes[0].name
        dest_str = '%s.%s' % (dest_name, edge.dest_attr)
        return '%s,%s' % (src_str, dest_str)

    def getEdgeIDs(self):
        """
        Returns a list of all edges in the network.
        """
        ids = []
        for edge in self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            ids.append(attrs.get('id'))
        return ids

    def getEdge(self, *args):
        """
        Return a dag edge.

        Pass 

        returns:
            (obj)
        """
        edges=[]
        for arg in args:
            # if UUID is passed
            if arg in self.dagnodes:
                edges.append(self.dagnodes.get(arg))

        for edge in self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            edge_id = attrs.get('UUID')
            src_attr = attrs.get('src_attr', None)
            dest_attr = attrs.get('dest_attr', None)

            src_nodes = self.getNode(src_id)
            dest_nodes = self.getNode(dest_id)

            if not src_nodes and dest_nodes:
                continue

            if not src_attr and dest_attr:
                continue

            src_name = src_nodes[0].name
            dest_name = dest_nodes[0].name
            conn_str = '%s.%s,%s.%s' % (src_name, src_attr, dest_name, dest_attr)
            if conn_str in args:
                edges.append(self.dagnodes.get(edge_id))
        return edges

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
        name  = kwargs.pop('name', 'node1')

        # check to see if node type is valid
        if node_type not in self.node_types():
            log.error('invalid node type: "%s"' % node_type)
            return

        if not self.validNodeName(name):
            name = self.getValidNodeName(name)

        dag = DagNode(node_type, name=name, **kwargs)
        self.dagnodes[dag.id] = dag
        
        # add the node to the networkx graph
        self.network.add_node(dag.id, **dag)

        # update the scene
        if self.manager is not None:
            self.manager.addNodes([dag,])
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

        params:
            src  - (DagNode) source node
            dest - (DagNode) destination node

        returns:
            (DagEdge) - edge object

        """
        UUID = kwargs.pop('id', None)
        src_attr = kwargs.pop('src_attr', 'output')
        dest_attr = kwargs.pop('dest_attr', 'input')

        if src is None or dest is None:
            return False

        if not src or not dest:
            return False

        # don't connect the same node
        if src == dest:
            log.warning('invalid connection: "%s", "%s"' % (src.name, dest.name))
            return

        # create an edge
        edge = DagEdge(src, dest, src_attr=src_attr, dest_attr=dest_attr, id=UUID)
        conn_str = self.parseEdgeName(edge)
        log.debug('parsing edge: "%s"' % conn_str)

        if conn_str in self.allConnections():
            log.warning('connection alread exists: %s' % conn_str)
            return 

        self.network.add_edge(src.id, dest.id, **edge)
        self.dagnodes[edge.id] = edge

        # update the scene
        if self.manager is not None:
            self.manager.addNodes([edge,])
        return edge

    def removeEdge(self, *args): 
        """
        Removes an edge from the graph

        params:
            UUID    - (str) edge UUID
            conn    - (str) connection string (ie "node1.output,node2.input")

        returns:
            (object)  - removed edge
        """
        edges = []
        for arg in args:
            # arg is a DagEdge instance
            if isinstance(arg, DagEdge):
                edges.append(arg)
                continue

            # arg is a UUID str
            if arg in self.dagnodes:
                dag = self.dagnodes.pop(arg)
                edges.append(dag)
                continue

            # arg is a connection str
            if arg in self.allConnections():
                UUID = self.getEdgeID(arg)
                if not UUID:
                    continue
                dag = self.getEdge(UUID)
                if not dag:
                    continue
                edges.append(dag[0])

                continue

        if not edges:
            log.error('no valid edges specified.')
            return False

        for edge in edges:
            try:
                self.network.remove_edge(edge.src_id, edge.dest_id)
                log.info('Removing edge: "%s"' % self.parseEdgeName(edge))
            except Exception, err:
                log.error(err)
                return False
        return True

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


        returns:
            (str) - edge UUID
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

            src_nodes = self.getNode(src_id)
            dest_nodes = self.getNode(dest_id)

            if not src_nodes or not dest_nodes:
                return result

            src_node = src_nodes[0]
            dest_node = dest_nodes[0]

            edge_id = str(edge_attrs.get('UUID'))
            conn_str = '%s.%s,%s.%s' % (src_node.name, src_attr, dest_node.name, dest_attr)
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
        
        # TODO: node signal here
        return

    def copyNodes(self, nodes):
        """
        Copy nodes to the copy buffer
        """
        return False

    def pasteNodes(self):
        """
        Paste saved nodes
        """
        offset = 25
        pasted_nodes = []
        return pasted_nodes

    def connectNodes(self, source, dest):
        """
        Connect two nodes via a "Node.attribute" string
        """
        if not '.' in source or not '.' in dest:
            return False

        s = source.rpartition('.')
        d = dest.rpartition('.')

        if len(s) == 3 and len(d) == 3:
            src_name = s[0]
            src_attr = s[2]

            dest_name = d[0]
            dest_attr = d[2]

            src_nodes = self.getNode(src_name)
            dest_nodes = self.getNode(dest_name)

            src_node = None
            dest_node = None

            if src_nodes:
                src_node = src_nodes[0]
            
            if dest_nodes:
                dest_node = dest_nodes[0]

            if not src_node or not dest_node:
                if not src_node:
                    log.error('invalid source node: "%s"' % src_name)

                if not dest_node:
                    log.error('invalid destination node: "%s"' % dest_name)
                return False

            # add the edge
            return self.addEdge(src_node, dest_node, src_attr=src_attr, dest_attr=dest_attr)
        return False

    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.clear()
        self.dagnodes = dict()

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

    def getValidNodeName(self, name):
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

                src_dag_node = self.getNode(src_id)
                dest_dag_node = self.getNode(dest_id)

                src_string = '%s.%s' % (src_dag_node.name, src_attr)
                dest_string = '%s.%s' % (dest_dag_node.name, dest_attr)

                # TODO: need to get connection node here
                log.debug('building edge: %s > %s' % (src_id, dest_id))
                
                self.addEdge(src=src_string, dest=dest_string, id=edge_id)

            """
            if self.view:
                scene_pos = self.network.graph.get('view_center', (0,0))
                view_scale = self.network.graph.get('view_scale', (1.0, 1.0))
                self.view.resetTransform()

                self.view.setCenterPoint(scene_pos)
                self.view.scale(*view_scale)
            """

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
            dagnode1 = self.getNode(src_id)
            dagnode2 = self.getNode(dest_id)

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
