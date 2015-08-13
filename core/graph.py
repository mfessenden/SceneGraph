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
from SceneGraph.core import log, PluginManager, Attribute
from SceneGraph.core import nodes
from SceneGraph import util


class Graph(object):
    """
    Wrapper for NetworkX MultiDiGraph. Adds methods to query nodes,
    read & write graph files, etc.
    """
    def __init__(self, *args, **kwargs):

        #self.network        = nx.DiGraph()
        self.network        = nx.MultiDiGraph() # mutliple edges between nodes
        
        self.mode           = 'standalone'
        self.grid           = Grid(5, 5)
        self.handler        = None
        self.plug_mgr       = PluginManager()
        self._initialized   = 0

        # attributes for current nodes/dynamically loaded nodes
        self._node_types     = dict() 
        self.dagnodes        = dict()
        self.autosave_path   = os.path.join(os.getenv('TMPDIR'), 'sg_autosave.json') 
        self._autosave_file  = None

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
        graph_data = self.snapshot()
        return json.dumps(graph_data, indent=5)

    def initializeNetworkAttributes(self, scene=None):
        """
        Add default attributes to the networkx graph.

        :param scene: name of scene file.
        :type scene: str
        """
        self.network.graph['api_version'] = options.API_VERSION
        self.network.graph['scene'] = scene
        self.network.graph['environment'] = self.mode
        self.network.graph['preferences'] = dict()

    def getNetworkPreferences(self, key=None):
        """
        Return the network preferences.

        :param key: section of key to isolate.
        :type key: str

        :returns: graph preferences.
        :rtype: dict
        """
        return self.network.graph.get('preferences', {})

    def scanNodeTypes(self, path):
        """
        Scan the given directory for node types.

        :param str path: path to scan.
        """
        nodes = dict()
        if not os.path.exists(path):
            log.warning('node path "%s" does not exist.' % path)
            return nodes

        for fn in os.listdir(path):
            if fn not in ['README']:
                node_name = os.path.splitext(os.path.basename(fn))[0]
                node_mod = os.path.join(path, '%s.py' % node_name)
                node_data = os.path.join(path, '%s.mtd' % node_name)
                if os.path.exists(node_mod) and os.path.exists(node_data):
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
        self.clean_legacy_attrs()
        self.network.graph['api_version'] = options.API_VERSION
        self.network.graph['scene'] = self.getScene()
        self.network.graph['environment'] = self.mode
        self.network.graph['preferences'] = dict()

        if self.handler is not None:
            self.network.graph.get('preferences').update(self.handler.updateGraphAttributes())

    def clean_legacy_attrs(self, attributes=['autosave']):
        """
        For cleaning up legacy scenes.

        :param attributes: deprecated attributes.
        :type attributes: list
        """
        for attr in attributes:
            if attr in self.network.graph:
                self.network.graph.pop(attr)

    #- Events -----
    def nodeNameChangedEvent(self, *args, **kwargs):
        node, new_name = args
        print '# Event: node name changed: "%s" --> "%s"' % (node.name, new_name)

        if not self.is_valid_name(new_name):
            node.nodeNameChanged.new_name = self.get_valid_name(new_name) 

    def nodePositionChangedEvent(self, *args, **kwargs):
        node, pos = args
        print '# Event: node position changed: "%s" --> "%s"' % (node.name, '%.2f, %.2f' % (pos[0], pos[1]))

    def nodeAttributeUpdatedEvent(self, *args, **kwargs):
        node, attr_name, attr_value = args
        print '# Event: node attribute updated: "%s" --> "%s: %s"' % (node.name, attr_name, str(attr_value))

    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        if event.type == 'nameChanged':
            old_name = obs.name
            new_name = event.data.get("new_name")
            if old_name == new_name:
                return

            # update the event to reflect a better name choice
            if not self.is_valid_name(new_name):
                valid_name = self.get_valid_name(new_name)
                event.data.update(valid_name=valid_name)

    def updateDagNodes(self, dagnodes, debug=False):
        """
        Update the networkx nodes and links attributes from scene values.

        :param dagnodes: list of dag node objects.
        :type dagnodes: list
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes=[dagnodes,]

        for dag in dagnodes:
            log.debug('Graph: updating dag node "%s"' % dag.name)
            nid = dag.id
            if nid in self.network.nodes():
                #self.network.node[nid].update(dag.data)
                dag_data = json.loads(str(dag), object_pairs_hook=dict)
                nx_data = self.network.node[nid]
                nx_data.update(dag_data)
                
                if debug:
                    # write temp file
                    filename = os.path.join(os.path.dirname(self.autosave_path), '%s.json' % dag.name)
                    fn = open(filename, 'w')
                    json.dump(dag_data, fn, indent=4)
                    fn.close()                

    def evaluate(self, dagnodes=[], verbose=False):
        """
        Evalute the Graph, updating networkx graph.
        """
        result = True
        if not dagnodes:
            dagnodes = self.dagnodes.values()

        # update network nodes from dag attributes
        self.updateDagNodes(dagnodes)

        node_ids = []
        invalid_node_ids = []
        for node in dagnodes:
            if issubclass(type(node), nodes.Node):
                if node.id not in node_ids:
                    node_ids.append(node.id)

        if self.network.edges():
            for edge in self.network.edges_iter(data=True):
                src_id, dest_id, edge_attrs = edge

                source_node = self.dagnodes.get(src_id, None)
                dest_node = self.dagnodes.get(dest_id, None)

        if self.network.nodes():
            for node in self.network.nodes_iter(data=True):
                node_id, node_attrs = node
                if node_id not in node_ids:
                    invalid_node_ids.append(node_id)
                    log.warning('invalid node "%s" ( %s )' % (node_attrs.get('name'), node_id))
                    result = False
        return result

    def node_types(self, plugins=[], disabled=False):
        """
        Returns a list of node types.
        """
        return self.plug_mgr.node_types(plugins=plugins, disabled=disabled)

    #-- NetworkX Stuff -----
    def getScene(self):
        """
        Return the current graphs' scene attribute
        
        :returns: scene file name.
        :rtype: str
        """
        return self.network.graph.get('scene', None)

    def setScene(self, filename=None):
        """
        Set the current scene value.

        :param filename: scene file name.
        :type filename: str

        :returns: scene file name.
        :rtype: str
        """
        tmp_dir = os.getenv('TMPDIR')
        if not tmp_dir:
            log.warning('environment "TMPDIR" not set, please set and restart.')
        if tmp_dir not in filename:
            self.network.graph['scene'] = filename
        return self.getScene()

    def listNodes(self):
        """
        Returns a dictionary of networkx node data.
        
        :returns: networkx node data.
        :rtype: dict
        """
        return self.network.nodes(data=True)

    def nx_node_names(self):
        """
        Returns a list of nx node names in the scene.
        
        :returns: networkx node names.
        :rtype: list
        """
        node_names = []
        nodes = self.network.nodes(data=True)
        if nodes:
            for node in nodes:
                id, data = node
                name = data.get('name', None)
                if name is not None:
                    node_names.append(name)
        return node_names

    def node_names(self):
        """
        Returns a dag node names.

        :returns: list of DagNode names.
        :rtype: list
        """
        return [node.name for node in self.nodes()]

    def nodes(self):
        """
        Returns a list of all dag nodes.

        :returns: list of DagNode objects.
        :rtype: list
        """
        nodes = []
        for node in  self.network.nodes(data=True):
            UUID, attrs = node
            if UUID in self.dagnodes:
                nodes.append(self.dagnodes.get(UUID))
        return nodes

    def edges(self, *args):
        """
        Returns a list of all dag edges.

        returns:
            (list) - list of edges.
        """
        return self.network.edges(data=True)

    def get_node(self, *args):
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

    def connections(self):
        """
        Returns a list of human-readable edge
        connections.

        returns:
            (list) - list of connection strings. 
        """
        connections = []
        # edge: (id, id, {attrs})
        for edge in self.edges():
            srcid, destid, edge_attrs = edge

            src_attr = edge_attrs.get('src_attr')
            dest_attr = edge_attrs.get('dest_attr')

            src_nodes = self.get_node(srcid)
            dest_nodes = self.get_node(destid)

            if not src_nodes or not dest_nodes:
                continue

            # query node names
            src_node = src_nodes[0]
            dest_node = dest_nodes[0]
            connections.append('%s.%s,%s.%s' % (src_node.name, src_attr, 
                                                    dest_node.name, dest_attr))
        return connections

    def add_node(self, node_type='default', **kwargs):
        """
        Creates a node in the parent graph

        :param node_type: node type.
        :type node_type: str

        :returns:
            
            :type: `core.DagNode`
                
                - in standalone mode

            :type: `ui.NodeWidget`
                
                - in ui mode

        :rtype: DagNode
        :rtype: NodeWidget
        """
        # check to see if node type is valid
        if node_type not in self.node_types():
            log.error('invalid node type: "%s"' % node_type)
            return

        pos  = kwargs.pop('pos', self.grid.coords)

        # get the default name for the node type and validate it
        name = self.get_valid_name(self.plug_mgr.default_name(node_type))

        if 'name' in kwargs:
            name = kwargs.pop('name')

        # parse attributes
        attributes = dict()
        for attr, val in kwargs.iteritems():
            if util.is_dict(val):
                attributes[attr]=val
                
        # get the dag node from the PluginManager
        dag = self.plug_mgr.get_dagnode(node_type=node_type, name=name, pos=pos, _graph=self, attributes=attributes, **kwargs)

        # connect signals
        dag.nodeNameChanged += self.nodeNameChangedEvent
        dag.nodePositionChanged += self.nodePositionChangedEvent
        dag.nodeAttributeUpdated += self.nodeAttributeUpdatedEvent

        # advance the grid to the next value.
        self.grid.next()
        self.dagnodes[dag.id] = dag
        
        # todo: figure out why I have to load this (need JSONEncoder)
        node_data = json.loads(str(dag), object_pairs_hook=dict)
        # add the node to the networkx graph
        self.network.add_node(dag.id, **node_data)

        # update the scene
        if self.handler is not None:
            self.handler.dagNodesAdded([dag.id,])
        return dag

    def parse_connections(self, data):
        """
        parse connections from parsed graph data.
        """
        attributes = dict()
        for k, v in data.iteritems():
            if hasattr(v, keys):
                attributes[k] = data.pop(k)
        return attributes

    def remove_node(self, *args):
        """
        Removes a node from the graph

        :param *args: node name, node id
        :type *args: str

        :returns: node was removed.
        :rtype: bool
        """
        node_ids = []
        nodes = self.get_node(*args)

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

        if node_ids:
            # update the scene
            if self.handler is not None:
                self.handler.dagUpdated(node_ids)
            return True
        return False

    def add_edge(self, src, dest, **kwargs):
        """
        Add an edge connecting two nodes.

        :param src: source node
        :type src: DagNode

        :param dest: destination node
        :type dest: DagNode

        :returns: edge object
        :rtype: dict
        """
        src_attr = kwargs.pop('src_attr', 'output')
        dest_attr = kwargs.pop('dest_attr', 'input')
        weight = kwargs.pop('weight', 1.0)
        edge_type = kwargs.pop('edge_type', 'bezier')

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

        conn_str = '%s.%s,%s.%s' % (src.name, src_attr, dest.name, dest_attr)
        if conn_str in self.connections():
            log.warning('connection already exists: %s' % conn_str)
            return 
        
        # edge attributes for nx graph
        edge_attrs = dict(src_id=src.id, dest_id=dest.id, src_attr=src_attr, dest_attr=dest_attr, edge_type=edge_type)

        src_conn = src.get_connection(src_attr)
        dest_conn = dest.get_connection(dest_attr)
        edge_id_str = '(%s,%s)' % (src.id, dest.id)

        if edge_id_str not in src_conn._edges and edge_id_str not in dest_conn._edges:            
            # add the nx edge        
            self.network.add_edge(src.id, dest.id, key='attributes', weight=weight, attr_dict=edge_attrs)
            log.info('adding edge: "%s"' % self.edge_nice_name(src.id, dest.id))

            # new edge = {'attributes': {'dest_attr': 'input', 'src_attr': 'output', 'weight': 1}}
            new_edge = self.network.edge[src.id][dest.id]
            
            src_conn._edges.append(edge_id_str)
            dest_conn._edges.append(edge_id_str)

            # update the scene
            if self.handler is not None:
                self.handler.dagEdgesAdded(new_edge.get('attributes'))
            return new_edge
        return

    def get_edge(self, *args):
        """
        Return a dag edge.

        Pass connection string ie: ('node1.output, node2.input'),
        or source dest (ie: 'node1.output', 'node2.input')

        :returns: list of nx edges (id, id, {attributes})
        :rtype: list
        """
        edges=[]

        cs = lambda x: [y.strip() for y in x.split(',')]

        # variables to match
        src_conn  = None
        dest_conn = None

        src_name  = None
        dest_name = None

        src_attr  = 'output'
        dest_attr = 'input'

        edgeid    = None

        # parse connection strings
        if len(args):
            if len(args) > 1:
                if (args[0], args[1]) in self.network.edges():
                    edgeid = (args[0], args[1])

                if type(args[0]) is str and type(args[1]) is str:

                    src_conn = args[0]
                    dest_conn = args[1]
            else:
                if type(args[0]) is str:
                    if ',' in args[0]:
                        src_conn, dest_conn = cs(args[0])

        if not src_conn or not dest_conn:
            log.warning('invalid arguments passed.')
            return

        if '.' in src_conn:
            src_name, src_attr = src_conn.split('.')

        if '.' in dest_conn:
            dest_name, dest_attr = dest_conn.split('.')

        # loop through nx edges
        # edge: (id, id, {'src_id': id, 'dest_attr': 'input', 'src_attr': 'output', 'dest_id': id, 'weight': 1})
        for edge in self.network.edges(data=True):

            srcid, destid, attrs = edge
            edge_id = (srcid, destid)

            #match two ids
            if edge_id == edgeid:
                edges.append(edge)

            sn_attr = attrs.get('src_attr', None)
            dn_attr = attrs.get('dest_attr', None)

            src_nodes = self.get_node(srcid)
            dest_nodes = self.get_node(destid)

            if not src_nodes or not dest_nodes:
                continue

            if not sn_attr or not dn_attr:
                continue

            src_node  = src_nodes[0]
            dest_node = dest_nodes[0]

            sn_name = src_node.name
            dn_name = dest_node.name

            if src_name == sn_name and dest_name == dn_name:
                if src_attr == sn_attr and dest_attr == dn_attr:
                    edges.append(edge)
        return edges

    def get_edge_ids(self, *args):
        """
        Returns a valid nx ids tuple.

        :returns: (src_id, dest_id)
        :rtype: tuple 
        """
        edges = self.get_edge(*args)
        if edges:
            return [(edge[0], edge[1]) for edge in edges]
        return []

    def edge_nice_name(self, *args):
        """
        Returns a connection string from ids.

        :returns: connection string.
        :rtype: str
        """
        edges = self.get_edge(*args)

        if not edges:
            return '(Invalid)'

        if len(edges) > 1:
            return '(Invalid)'

        # edge: (id, id, attrs)
        edge = edges[0]
        
        source_name = self.dagnodes.get(edge[0]).name
        dest_name = self.dagnodes.get(edge[1]).name

        return '%s.%s,%s.%s' % (source_name, edge[2].get('src_attr', 'output'),
                                dest_name, edge[2].get('dest_attr', 'input'))

    def remove_edge(self, *args): 
        """
        Removes an edge from the graph.

        :param str UUID: edge UUID
        :param str conn: connection string (ie "node1.output,node2.input")

        :returns: edge removal was successful.
        :rtype: bool
        """
        edges = self.get_edge(*args)
        if not edges:
            log.warning('cannot find edge.')
            return

        for edge in edges:
            edge_id = (edge[0], edge[1])

            if edge_id in self.network.edges():
                log.debug('Removing edge: "%s"' % self.edge_nice_name(*edge_id))
                self.network.remove_edge(*edge_id)                
                self.remove_node_edge(*edge_id)        

                # update the scene
                if self.handler is not None:
                    self.handler.dagUpdated(edge_id)
                return True
        return False

    def remove_node_edge(self, src_id, dest_id):
        """
        Remove deleted edges from current dagnodes.
        """
        edge_id_str = '(%s,%s)' % (src_id, dest_id)
        for id, dag in self.dagnodes.items():
            for conn_name in dag.connections:
                dagcon = dag.get_connection(conn_name)
                if edge_id_str in dagcon._edges:
                    dagcon._edges.remove(edge_id_str)

    def getNodeID(self, name):
        """
        Return the node given a name.

        :param str name: node ID

        :returns: DagNode UUID
        :rtype: str
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

        :param str conn: edge connection string.

        :returns: edge UUID
        :rtype: str
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

            src_nodes = self.get_node(src_id)
            dest_nodes = self.get_node(dest_id)

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

        :param list dagnodes: dagnode(s)

        :returns: list of connected edges.
        :rtype: list
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
                dag_edges = self.get_edge(edge_id)
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
        if not self.is_valid_name(new_name):
            log.error('"%s" is not unique' % new_name)
            return

        UUID = self.getNodeID(old_name)

        if UUID:
            dagnodes = self.get_node(UUID)
            self.network.node[UUID]['name'] = new_name
            
            if dagnodes:
                # update the scene
                if self.handler is not None:
                    self.handler.renameNodes(dagnodes[0])
        return

    def rename_connection(self, id, old, new):
        """
        Rename an attribute in the network.

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

            # update any connections
            if self.network.edges():
                for edge in self.network.edges(data=True):
                    src_id, dest_id, attrs = edge
                    if id in [src_id, dest_id]:
                        for attr in ['src_attr', 'dest_attr']:
                            val = attrs.get(attr, None)
                            if val is not None:
                                if val == old:
                                    print 'updating attribute name: "%s": "%s" ("%s")' % (attr, new, old)
                                    self.network.edge[src_id][dest_id]['attributes'][attr] = new
            return True
        return False

    def copyNodes(self):
        """
        Paste saved nodes
        """
        offset = 25
        pasted_nodes = []
        return pasted_nodes

    def pasteNodes(self, nodes, offset=[200, 200]):
        """
        Copy nodes to the copy buffer
        """
        import copy
        result = []
        for node in nodes:
            new_name = self.get_valid_name(node.name)
            data = copy.deepcopy(node.data)
            data.update(pos=[node.pos[0]+offset[0], node.pos[1]+offset[1]])
            data.update(name=new_name)
            data.pop('node_type')
            data.pop('id')
            new_node = self.add_node(node.node_type, **data)
            print '# adding node: "%s"' % new_node.name
            result.append(new_node)
        return result

    def connect(self, source, dest):
        """
        Connect two nodes via a "Node.attribute" string

        :param src: connection string (ie: 'node1.output')
        :type src: str

        :param dest: connection string (ie: 'node2.input')
        :type dest: str

        :returns: edge was added successfully.
        :rtype: bool
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

            src_nodes = self.get_node(src_name)
            dest_nodes = self.get_node(dest_name)

            if not src_nodes or not dest_nodes:
                return False

            src_node = src_nodes[0]            
            dest_node = dest_nodes[0]

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
        self._initialized = 0
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

    def is_valid_name(self, name):
        """
        Returns true if name not already assigned to a node.

        params:
            name (str) - node name to check against other nodes
                         in the graph.

        returns:
            (bool) - node name is valid.
        """
        return name not in self.node_names()

    def get_valid_name(self, name, force_int=True):
        """
        Returns a legal node name

        params:
            name      (str)  - node name to query
            force_int (bool) - always force a number as the last character (maya behavior)

        returns:
            (str) - valid node name.
        """
        # cleaup invalid characters.
        name = re.sub(r'[^a-zA-Z0-9\[\]]','_', name)

        if force_int:
            if not re.search('\d+$', name):
                name = '%s1' % name

        while not self.is_valid_name(name):
            node_num = int(re.search('\d+$', name).group())
            node_base = name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):
                if '%s%d' % (node_base, i) not in self.node_names():
                    name = '%s%d' % (node_base, i)
                    break
        return name
    
    #- Actions ----
    def nodeChangedAction(self, UUID, **kwargs):
        """
        Runs when a node is changed in the graph.
        """
        print '# Graph: node changed: ', UUID
        
    #- Snapshots, Reading & Writing -----
    def snapshot(self):
        """
        Returns a snapshot dictionary for writing scenes 
        and updating undo stack.

         * todo: look into nxj.adjacency_data() method.
        """
        if not self.evaluate():
            log.warning('graph did not evaluate correctly.')
        attrs = {'source': 'source', 'target': 'target', 'key': 'key', 
                'id': 'id', 'src_id': 'src_id', 'dest_id': 'dest_id', 'src_attr': 'src_attr', 'dest_attr': 'dest_attr'}
        graph_data = nxj.node_link_data(self.network, attrs=attrs)
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

            dagnode = self.get_node(node.get('name'))
            node_data_filtered.append(node)
            link_data_filtered.extend(self.connectedEdges(dagnode))

        result.update(nodes=node_data_filtered)
        result.update(links=link_data_filtered)
        return result

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

        :param dict data: dictionary of scene graph data.
        :param bool nodes: restore nodes/edges.
        :param bool graph: restore scene attributes/preferences.
        """
        self.reset()

        graph_data = data.get('graph', [])
        node_data = data.get('nodes', [])
        edge_data = data.get('links', [])
        
        self.updateConsole(msg='restoring %d nodes' % len(node_data))

        # update graph attributes
        for gdata in graph_data:
            if len(gdata):
                if graph or gdata[0] in ['scene', 'api_version']:
                    self.network.graph[gdata[0]]=gdata[1]

        # build nodes from data
        if nodes:
            for node_attrs in node_data:
                # get the node type
                node_type = node_attrs.pop('node_type', 'default')

                # add the dag node/widget
                dag_node = self.add_node(node_type, **node_attrs)
                log.debug('building node "%s"' % node_attrs.get('name'))

            # edge : ['src_attr', 'target', 'weight', 'dest_id', 'source', 'dest_attr', 'key', 'src_id']
            for edge in edge_data:

                src_id = edge.get('src_id')
                dest_id = edge.get('dest_id')

                src_attr = edge.get('src_attr')
                dest_attr = edge.get('dest_attr')

                weight = edge.get('weight', 1.0)

                src_dag_nodes = self.get_node(src_id)
                dest_dag_nodes = self.get_node(dest_id)

                if not src_dag_nodes or not dest_dag_nodes:
                    log.warning('cannot parse nodes.')
                    return

                src_dag_node = src_dag_nodes[0]
                dest_dag_node = dest_dag_nodes[0]
                src_string = '%s.%s' % (src_dag_node.name, src_attr)
                dest_string = '%s.%s' % (dest_dag_node.name, dest_attr)

                # TODO: need to get connection node here
                log.info('connecting nodes: "%s" "%s"' % (src_string, dest_string))            
                dag_edge = self.add_edge(src_dag_node, dest_dag_node, src_attr=src_attr, dest_attr=dest_attr, weight=weight)

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
        self._initialized = 1

    def write(self, filename, auto=False, data={}):
        """
        Write the graph to scene file.

        params:
            filename (str)  - file to save.
            auto     (bool) - file is an autosave, don't set
                              it as the current scene.
            data     (dict) - dictionary of graph data.
        """  
        if not data:
            data = self.snapshot()

        fn = open(filename, 'w')
        json.dump(data, fn, indent=4)
        fn.close()

        if auto:
            self._autosave_file = filename
            filename = filename[:-1]
        return self.setScene(filename)

    def read(self, filename, force=False):
        """
        Read a graph from a saved scene.

        params:
            filename - (str) file to read
        """
        graph_data = self.read_file(filename)
        if not graph_data:
            log.error('scene "%s" appears to be invalid.' % filename)
            return False

        api_ver = [x[1] for x in graph_data.get('graph', []) if x[0] == 'api_version'][0]
        if not self.version_check(graph_data):
            if not force:
                log.error('scene "%s" requires api version %s ( %s )' % (filename, options.API_MINIMUM, api_ver))
                return False   

        # restore from state.
        self.restore(graph_data)
        if self.handler is not None:
            self.handler.graphReadAction()
        return self.setScene(filename)
    
    def read_file(self, filename):
        """
        Read a data file and return the data.

        params:
            filename - (str) file to read
        """
        # expand user home path.
        filename = os.path.expanduser(filename)
        autosave_file = '%s~' % filename

        if not os.path.exists(filename):
            log.error('file %s does not exist.' % filename)
            return False

        if os.path.exists(autosave_file):
            os.remove(autosave_file)
            log.info('removing autosave "%s"' % autosave_file)

        log.info('reading scene file "%s"' % filename)
        raw_data = open(filename).read()
        graph_data = json.loads(raw_data, object_pairs_hook=dict)
        return graph_data

    def version_check(self, data):
        """
        Check to make sure the document is readable.

        params:
            data (dict) - raw json data from file.

        returns:
            (bool) - file is readable.
        """
        # version check
        api_ver = 0.0
        gdata = data.get('graph', [])

        for gd in gdata:
            key, val = gd
            if key == 'api_version':
                try:
                    api_ver = float(val)
                except:
                    api_ver = float('.'.join(val.split('.')[:-1]))
        if api_ver:
            return api_ver >= options.API_MINIMUM
        return False

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
            dagnode1 = self.get_node(src_id)
            dagnode2 = self.get_node(dest_id)

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
        if self.plug_mgr._node_data:
            print '-' * 35
            print 'PLUGINS LOADED: %d' % (len(self.plug_mgr._node_data)) 

        row = 0          
        for node_type, data in self.plug_mgr._node_data.iteritems():
            widget = data.get('widget', None)

            if widget is not None:
                widget = widget.__name__
            dagnode = data.get('dagnode', None)

            if dagnode is not None:
                dagnode = dagnode.__name__
            if not row:
                print '%s\nPlugin: %s\n%s' % ('-' *35, node_type, '-' * 35)
            else:
                print '\n%s\nPlugin: %s\n%s' % ('-' *35, node_type, '-' * 35)
            print 'source file: %s' % data.get('source')
            print 'metadata:    %s' % data.get('metadata')
            print 'dagnode:     %s' % dagnode
            print 'widget:      %s' % widget
            row+=1



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
