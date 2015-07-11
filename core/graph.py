#!/usr/bin/env python
import os
import re
import weakref
import simplejson as json
import networkx as nx
import networkx.readwrite.json_graph as nxj
from functools import partial
import inspect
from collections import OrderedDict as dict
from SceneGraph import options
from SceneGraph.core import log, DagNode, DagEdge, PluginManager


class Graph(object):
    """
    Wrapper for NetworkX graph. Adds methods to query nodes,
    read & write graph files, etc.

    Nodes are stored:

        # NetworkX graph
        Graph.network.nodes()

        # dictionary of id, DagNode type
        Graph.dagnodes 
    """
    def __init__(self, *args, **kwargs):

        #self.network        = nx.DiGraph()
        self.network        = nx.MultiDiGraph() # mutliple edges between nodes
        
        self.mode           = 'standalone'
        self.grid           = Grid(5, 5)
        self.handler        = None
        self.pmanager       = PluginManager()

        # attributes for current nodes/dynamically loaded nodes
        self._node_types     = dict() 
        self.dagnodes        = dict()
        self.temp_scene      = os.path.join(os.getenv('TMPDIR'), 'sg_autosave.json') 

        # testing mode only
        self.debug           = kwargs.pop('debug', False)

        # initialize the NetworkX graph attributes
        self.initializeNetworkAttributes()

        # if scene file is passed as an argument, read it
        for arg in args:
            if os.path.exists(arg):
                self.read(arg)
                continue

        if self.debug:
            self.read(os.path.join(os.getenv('HOME'), 'graphs', 'connections.json'))

    def __str__(self):
        import networkx.readwrite.json_graph as nxj
        graph_data = nxj.node_link_data(self.network)
        return json.dumps(graph_data, indent=5)

    def initializeNetworkAttributes(self, scene=None):
        """
        Add default attributes to the networkx graph.

        params:
            scene (str) - name of scene file.
        """
        self.network.graph['api_version'] = options.API_VERSION_AS_STRING
        self.network.graph['scene'] = scene
        self.network.graph['autosave'] = self.temp_scene
        self.network.graph['environment'] = self.mode
        self.network.graph['preferences'] = dict()

    def getNetworkPreferences(self, key=None):
        """
        Return the network preferences.
        """
        return self.network.graph.get('preferences', {})

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
            if fn not in ['README']:
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

    def updateGraphAttributes(self):
        """
        Update the network graph attributes.
        """
        self.network.graph['api_version'] = options.API_VERSION_AS_STRING
        self.network.graph['scene'] = self.getScene()
        self.network.graph['autosave'] = self.temp_scene
        self.network.graph['environment'] = self.mode
        self.network.graph['preferences'] = dict()

        if self.handler is not None:
            self.network.graph.get('preferences').update(self.handler.updateGraphAttributes())

    def updateDagNodes(self, dagnodes):
        """
        Update the networkx nodes and links attributes from scene values.

        params:
            dagnodes (list) - list of dag node objects.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes=[dagnodes,]

        for dag in dagnodes:
            log.debug('Graph: updating dag node "%s"' % dag.name)
            nid = dag.id
            if nid in self.network.nodes():
                self.network.node[nid].update(json.loads(str(dag)))

    def evaluate(self, dagnodes=[], verbose=False):
        """
        Evalute the Graph, updating networkx graph.
        """
        result = True
        if not dagnodes:
            dagnodes = self.dagnodes.values()

        self.updateDagNodes(dagnodes)
        edge_ids = self.getEdgeIDs()
        node_ids = []

        for node in dagnodes:
            if issubclass(type(node), DagNode):
                if node.id not in node_ids:
                    node_ids.append(node.id)

        # check for invalid edges.
        if self.network.edges():
            for edge in self.network.edges_iter(data=True):
                src_id, dest_id, edge_attrs = edge

                edge_id = edge_attrs.get('id')
                dagedge = self.getEdge(edge_id)
                src_name = self.getNode(src_id)
                dest_name = self.getNode(dest_id)

                if edge_id not in edge_ids:
                    log.warning('invalid edge "%s".' % dagedge.name)
                    result = False

        if self.network.nodes():
            for node in self.network.nodes_iter(data=True):
                node_id, node_attrs = node
                if node_id not in node_ids:
                    log.warning('invalid node "%s" ( %s )' % (node_attrs.get('name'), node_id))
                    result = False
        return result

    def node_types(self):
        """
        Returns a list of node types.
        """
        return self.pmanager.node_types

    #-- NetworkX Stuff -----
    def getScene(self):
        """
        Return the current graphs' scene attribute
        
        returns:
            (str)
        """
        return self.network.graph.get('scene', None)

    def setScene(self, filename=None):
        """
        Set the current scene value.

        params:
            filename (str) - scene file name.

        returns:
            (str) - scene file name.
        """
        tmp_dir = os.getenv('TMPDIR')
        if not tmp_dir:
            log.warning('environment "TMPDIR" not set, please set and restart.')
        if tmp_dir not in filename:
            self.network.graph['scene'] = filename
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
        Returns a list of node names in the scene.
        
        returns:
            (list)
        """
        node_names = []
        nodes = self.network.nodes(data=True)
        if nodes:
            for node in nodes:
                id, data = node
                name = data.get('name')
                node_names.append(name)
        return node_names

    def nodes(self):
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

    def edges(self):
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

    def getNode(self, *args):
        """
        Return a dag node by name.

        params:
            node - (str) name of node to return

        returns:
            (obj)
        """
        nodes=[]
        network_nodes = self.network.nodes()
        if self.dagnodes:
            for UUID in self.dagnodes:
                if UUID in network_nodes:
                    node = self.dagnodes.get(UUID)
                    if node and node.name in args or str(node.id) in args:
                        nodes.append(node)
        return nodes

    def node_names(self):
        """
        Returns a list of all dag connection strings.

        returns:
            (list)
        """
        return [node.name for node in self.nodes()]

    def connections(self):
        """
        Returns a list of human-readable edge
        connections.

        returns:
            (list) - list of connection strings. 
        """
        connections = []
        for edge in self.edges():

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

        returns:
            (list) - list of edge ids.
        """
        ids = []
        for edge in self.network.edges(data=True):
            src_id, dest_id, attrs = edge
            ids.append(attrs.get('id'))
        return ids

    def getEdge(self, *args):
        """
        Return a dag edge.

        returns:
            (obj) - dag edge.
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

            if src_nodes and dest_nodes:
                src_name = src_nodes[0].name
                dest_name = dest_nodes[0].name
                conn_str = '%s.%s,%s.%s' % (src_name, src_attr, dest_name, dest_attr)
                if conn_str in args:
                    edges.append(self.dagnodes.get(edge_id))
        return edges

    def add_node(self, node_type='default', **kwargs):
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
        pos  = kwargs.pop('pos', self.grid.coords)

        # check to see if node type is valid
        if node_type not in self.node_types():
            log.error('invalid node type: "%s"' % node_type)
            return

        if not self.validNodeName(name):
            name = self.getValidNodeName(name)

        # get the dag node from the PluginManager
        dag = self.pmanager.get_dagnode(node_type=node_type, name=name, pos=pos, _graph=self, **kwargs)

        # advance the grid to the next value.
        self.grid.next()
        self.dagnodes[dag.id] = dag
        
        # todo: figure out why I have to load this
        node_data = json.loads(str(dag))
        # add the node to the networkx graph
        self.network.add_node(dag.id, **node_data)

        # update the scene
        if self.handler is not None:
            self.handler.dagNodesAdded([dag.id,])
        return dag

    def remove_node(self, *args):
        """
        Removes a node from the graph

        params:
            (str) node name or id

        returns:
            (bool) - node was removed.
        """
        node_ids = []
        nodes = self.getNode(*args)

        # iterate through the nodes
        for node in nodes:
            dag_id = node.id
            # remove from networkx
            if dag_id in self.network.nodes():
                self.network.remove_node(dag_id)

            # remove from dagnodes
            if dag_id in self.dagnodes:
                dn = self.dagnodes.get(dag_id)
                if self.dagnodes.pop(dag_id):
                    node_ids.append(dag_id)

        # todo: check that method appears to be getting called twice
        for edge_id, edge in self.dagnodes.iteritems():
            if issubclass(type(edge), DagEdge):
                ptr = (edge.src_id, edge.dest_id)
                if ptr not in self.network.edges():
                    if edge_id not in node_ids:
                        node_ids.append(edge_id)

        if node_ids:
            # update the scene
            if self.handler is not None:
                self.handler.dagNodesRemoved(node_ids)
            return True
        return False

    def add_edge(self, src, dest, **kwargs):
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
            log.warning('none type passed.')
            return False

        if not src or not dest:
            log.warning('please specify two nodes to connect.')
            return False

        # don't connect the same node
        if src.name == dest.name:
            log.warning('invalid connection: "%s", "%s"' % (src.name, dest.name))
            return

        # create an edge
        edge = DagEdge(src, dest, src_attr=src_attr, dest_attr=dest_attr, id=UUID, _graph=self)

        conn_str = self.parseEdgeName(edge)
        log.debug('parsing edge: "%s"' % conn_str)

        if conn_str in self.connections():
            log.warning('connection already exists: %s' % conn_str)
            return 

        # TODO: networkx check here!
        src_id, dest_id, edge_attrs = edge.data
        self.network.add_edge(src_id, dest_id, **edge_attrs)
        self.dagnodes[edge.id] = edge

        # update the scene
        if self.handler is not None:
            self.handler.dagNodesAdded([edge.id,])
        return edge

    def remove_edge(self, *args): 
        """
        Removes an edge from the graph

        params:
            UUID    - (str) edge UUID
            conn    - (str) connection string (ie "node1.output,node2.input")

        returns:
            (object)  - removed edge
        """
        dagedges = []
        for arg in args:
            # arg is a DagEdge instance
            if isinstance(arg, DagEdge):
                dagedges.append(arg)
                continue

            # arg is a UUID str
            if arg in self.dagnodes:
                dag = self.dagnodes.get(arg)
                dagedges.append(dag)
                continue

            # arg is a connection str
            if arg in self.connections():
                UUID = self.getEdgeID(arg)
                if not UUID:
                    continue
                dag = self.getEdge(UUID)
                if not dag:
                    continue
                dagedges.append(dag[0])
                continue

        if not dagedges:
            #log.error('no valid edges specified.')
            return False

        edge_ids = []
        for edge in dagedges:
            edge_ids.append(edge.id)
            if edge.id in self.dagnodes:
                
                self.dagnodes.pop(edge.id)

                # remove references to nodes that were connected
                edge.breakConnections()

            if (edge.src_id, edge.dest_id) in self.network.edges():
                self.network.remove_edge(edge.src_id, edge.dest_id)
                log.info('Removing edge: "%s"' % self.parseEdgeName(edge))
            
            # delete the edge
            del edge

        # update the scene
        if self.handler is not None:
            self.handler.dagNodesRemoved(edge_ids)
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

    def connectedEdges(self, dagnodes):
        """
        Returns a list of all connected edges to the given node(s).

        params:
            dagnodes - (str) or (list)

        returns:
            (list) - list of connected edges.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]
        result = self.network.in_edges(nbunch=[self.getNodeID(n.name) for n in dagnodes], data=True)
        result.extend(self.network.out_edges(nbunch=[self.getNodeID(n.name) for n in dagnodes], data=True))
        return result

    def connectedDagEdges(self, dagnodes):
        """
        Returns a list of all connected edges to the given node(s).

        params:
            dagnodes - (str) or (list)

        returns:
            (list) - list of connected DagEdges.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]
        result = []
        edges = self.connectedEdges(dagnodes)
        if edges:
            for edge in edges:
                src_id, dest_id, attrs = edge
                edge_id = attrs.get('id', None)
                dag_edges = self.getEdge(edge_id)
                if dag_edges:
                    for d in dag_edges:
                        if d not in result:
                            result.append(d)
        return result

    def in_edges(self, dagnodes):
        """
        Returns a list of all incoming edges to the given node(s).

        params:
            nodes - (str) or (list) node names to query.

        returns:
            (list) - list of edge dictionaries.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]
        return self.network.in_edges(nbunch=[self.getNodeID(n) for n in dagnodes], data=True)

    def out_edges(self, dagnodes):
        """
        Returns a list of all outgoing edges to the given node(s).

        params:
            nodes - (str) or (list) node names to query.

        returns:
            (list) - list of edge dictionaries.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]
        return self.network.out_edges(nbunch=[self.getNodeID(n) for n in dagnodes], data=True)

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

        if UUID:
            dagnodes = self.getNode(UUID)
            self.network.node[UUID]['name'] = new_name
            
            if dagnodes:
                # update the scene
                if self.handler is not None:
                    self.handler.renameNodes(dagnodes[0])
        return

    def rename_attribute(self, id, old, new):
        """
        Rename an attribute.

        params:
            id   - (str) node UUID
            old  - (str) old attribute name
            new  - (str) new attribute name
        """
        if not id in self.network.nodes():
            log.error('invalid id: "%s"' % id)
            return False

        nn = self.network.node[id]
        if old in nn:
            val = nn.pop(old)
            nn[new] = val
            return True
        return False

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
            return self.add_edge(src_node, dest_node, src_attr=src_attr, dest_attr=dest_attr)
        return False

    def reset(self):
        """
        Remove all node & connection data
        """
        # clear the Graph
        self.network.clear()
        self.dagnodes = dict()

        if self.handler is not None:
            self.handler.resetScene()

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
        
    #- Snapshots, Reading & Writing -----
    def snapshot(self):
        """
        Returns a snapshot dictionary for writing scenes 
        and updating undo stack.

         * todo: look into nxj.adjacency_data() method.
        """
        if not self.evaluate():
            log.warning('graph did not evaluate correctly.')
        graph_data = nxj.node_link_data(self.network)
        return graph_data

    def graph_snapshot(self):
        """
        Returns a snapshot of just the graph.

        returns:
            (dict) - dictionary of graph data.
        """
        data = self.snapshot()
        for d in ['nodes', 'links']:
            if d in data:
                data.pop(d)
        return data

    def node_snapshot(self, nodes=[]):
        """
        Returns a snapshot of just the graph.

        params:
            dagnodes (list) - list of dag node names.

        return:
            (dict) - dictionary of nodes & connected edges.
        """
        if nodes:
            if type(nodes) not in [list, tuple]:
                nodes = [nodes,]

        self.evaluate()
        data = self.snapshot()
        result = dict()
        node_data = data.get('nodes', dict())

        # filter just the nodes we're querying.
        node_data_filtered = []
        link_data_filtered = []
        for node in node_data:

            # filter nodes
            if nodes:
                if node.get('name') not in nodes:
                    continue

            dagnode = self.getNode(node.get('name'))
            node_data_filtered.append(node)
            link_data_filtered.extend(self.connectedEdges(dagnode))

        result.update(nodes=node_data_filtered)
        result.update(links=link_data_filtered)
        return result

    def write(self, filename):
        """
        Write the graph to scene file
        """  
        graph_data = self.snapshot()
        fn = open(filename, 'w')
        json.dump(graph_data, fn, indent=4)
        fn.close()
        return self.setScene(filename)

    def save(self):
        """
        Save the current scene.
        """
        if not self.getScene():
            log.error('please save the current scene.')
            return

        log.info('saving current scene: "%s"' % self.getScene())
        return self.write(self.getScene())

    def restore(self, data, nodes=True, graph=True):
        """
        Restore current DAG state from data.

        params:
            data  (dict) - dictionary of scene graph data.
            nodes (bool) - restore nodes/edges.
            graph (bool) - restore scene attributes/preferences.
        """
        self.reset()

        graph_data = data.get('graph', [])
        nodes = data.get('nodes', [])
        edges = data.get('links', [])
        
        self.updateConsole(msg='restoring %d nodes' % len(nodes))

        # update graph attributes
        for gdata in graph_data:
            if len(gdata):
                if graph or gdata[0] in ['scene', 'api_version']:
                    self.network.graph[gdata[0]]=gdata[1]

        # build nodes from data
        if nodes:
            for node_attrs in nodes:
                # get the node type
                node_type = node_attrs.pop('node_type', 'default')

                # add the dag node/widget
                dag_node = self.add_node(node_type, **node_attrs)
                log.debug('building node "%s"' % node_attrs.get('name'))

            for edge_attrs in edges:
                edge_id = edge_attrs.get('id')
                src_id = edge_attrs.get('src_id')
                dest_id = edge_attrs.get('dest_id')

                src_attr = edge_attrs.get('src_attr')
                dest_attr = edge_attrs.get('dest_attr')

                src_dag_nodes = self.getNode(src_id)
                dest_dag_nodes = self.getNode(dest_id)

                if not src_dag_nodes or not dest_dag_nodes:
                    log.warning('cannot parse nodes.')
                    return

                src_dag_node = src_dag_nodes[0]
                dest_dag_node = dest_dag_nodes[0]
                src_string = '%s.%s' % (src_dag_node.name, src_attr)
                dest_string = '%s.%s' % (dest_dag_node.name, dest_attr)

                # TODO: need to get connection node here
                log.debug('connecting nodes: "%s" "%s"' % (src_string, dest_string))            
                dag_edge = self.add_edge(src_dag_node, dest_dag_node, src_id=src_id, dest_id=dest_id, id=edge_id)


                #self.handler.scene.clear()
                scene_pos = self.network.graph.get('view_center', (0,0))
                view_scale = self.network.graph.get('view_scale', (1.0, 1.0))

                # update the UI.
                if self.handler is not None:
                    if graph:
                        view = self.handler.scene.views()[0]
                        view.resetTransform()
                        view.setCenterPoint(scene_pos)
                        view.scale(*view_scale)

    def read(self, filename):
        """
        Read a graph from a saved scene.

        params:
            filename - (str) file to read
        """
        if not os.path.exists(filename):
            log.error('file %s does not exist.' % filename)
            return False

        log.info('reading scene file "%s"' % filename)
        raw_data = open(filename).read()
        graph_data = json.loads(raw_data, object_pairs_hook=dict)
        
        # restore from state.
        self.restore(graph_data)
        return self.setScene(filename)
    
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

    #- Scene Handler ----
    def updateConsole(self, msg, clear=False):
        """
        Send a message through the SceneHandler.
        """
        if self.handler is not None:
            self.handler.updateConsole(msg, clear=clear, graph=True)

    #- Virtual ----
    def is_connected(self, node1, node2):
        """
        Returns true if two nodes are connected.

        params:
            node1 - (DagNode) - first node to query.
            node2 - (DagNode) - second node to query.

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

    #- Plugins ----
    @property 
    def plugins(self):
        """
        Prints a list of plugins.
        """
        for node_type, data in self.pmanager._node_data.iteritems():
            print '\n# Node: %s: ' % node_type
            print '    source file: %s' % data.get('source')
            print '    metadata:    %s' % data.get('metadata')
            print '    widget:      %s' % data.get('widget', '(none)')


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

        # coordinates
        self._width     = 150
        self._height    = 150

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
    def coords(self):
        """
        Return the current x/y values of the current grid coordinates.

        returns:
            (tuple) - current row-column coordinates
        """
        return (self._row * self._width, self._col * self._height)

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
