#!/usr/bin/env python
import os
import uuid
import simplejson as json
from collections import MutableMapping
import copy
import sys
from SceneGraph.core import log


sys.setrecursionlimit(100)


"""
Goals:
 - hold basic attributes
 - easily add new attributes
 - query connections easily
 - can be cleanly mapped to and from json & new instances
"""


class DagNode(MutableMapping):

    CLASS_KEY     = "dagnode"
    defaults      = {}          # default attribute values
    private       = []          # attributes that cannot be changed
    # 'reserved' attributes, (need to be handled by the superclass) 
    reserved      = ['_data', '_graph', '_inputs', '_outputs']
    MANAGER       = None             

    def __init__(self, nodetype, **kwargs):

        # stash attributes
        self._data              = dict()
        self._graph             = None
        self._inputs            = dict()
        self._outputs           = dict()

        # reference to the node widget.
        self._widget            = None  

        self.width              = kwargs.pop('width', 100)
        self.height_collapsed   = kwargs.pop('height_collapsed', 15)
        self.height_expanded    = kwargs.pop('height_expanded', 175)

        self.node_type          = nodetype
        self.name               = kwargs.pop('name', 'node1')
        self.color              = kwargs.pop('color', [180, 180, 180])
        self.expanded           = kwargs.pop('expanded', False)

        self.pos                = kwargs.pop('pos', (0,0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # connections
        inputs                  = kwargs.pop('inputs', ['input'])
        outputs                 = kwargs.pop('outputs', ['output'])

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

        # setup connections
        for i in inputs:
            self.addConnection(i, input=True)

        for o in outputs:
            self.addConnection(o, input=False)

    def __str__(self):
        data = self.copy()
        return json.dumps(data, indent=4)

    def __del__(self):
        self.updateGraph('deleting node: "%s"' % self.id)
        # delete any connected connections.
        for conn_name, conn_node in self.getConnections().iteritems():
            self.updateGraph('deleting node connection: "%s"' % conn_name)

            del conn_node

    def __repr__(self):
        return json.dumps(self.__dict__(), indent=5)

    def __dict__(self):
        """
        Filter the current dictionary to only return set values.
        """
        return self.copy()

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if key in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        if key in self.reserved:
            super(DagNode, self).__setattr__(key, value)
        else:
            self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)
    
    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__

    @property
    def data(self):
        """
        Data output for networkx graph.
        """
        data = copy.deepcopy(self._data)
        data.update(_inputs=self._inputs)
        data.update(_outputs=self._outputs)
        return { k: data[k] for k in data.keys() if data[k]}

    def copy(self):
        """
        Data output for display.
        """
        data = copy.deepcopy(self._data)
        name = data.pop('name', 'null')
        data.update(_inputs=self._inputs.keys())
        data.update(_outputs=self._outputs.keys())
        return  {name:{ k: data[k] for k in data.keys() if data[k]}}
  
    def __deepcopy__(self, *args, **kwargs):
        """
        Defines the result of a deepcopy operation.
        """
        data = copy.deepcopy(self._data)
        node_type = data.pop('node_type', 'default')
        ad = self.__class__(node_type, **data)
        return ad
  
    def update(self, **adict):
        for (key, value) in list(adict.items()):
            if key in self.private:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(nodetype, data):
        """
        Instantiate a new instance from a dictionary.
        """
        self = DagNode(nodetype, **data)
        return self

    @property
    def node_class(self):
        return self.CLASS_KEY

    @property
    def height(self):
        if self.expanded:
            return self.height_expanded
        return self.height_collapsed

    @height.setter
    def height(self, value):
        if self.expanded:
            self.height_expanded=value
            return
        self.height_collapsed=value

    #- Attributes ----
    def addAttr(self, name, value=None, input=True, **kwargs):
        """
        Add attributes to the current node.
        """
        from SceneGraph.core import Attribute
        # TODO: need a way to protect core values
        attr = Attribute(name, value=value, input=input, **kwargs)
        attr._node = self
        self.update(**attr.copy())
        #self.__setattr__(name, attr)
        return attr

    def getAttr(self, attr):
        """
        Query any attribute from the node, returning
        an Attribute object if the attr is a dict.
        """
        from SceneGraph.core import Attribute
        value = self.get(attr, None)
        if type(value) is dict:
            if 'type' in value:
                value = Attribute(attr, **value)
                value._node = self
        return value

    def getAttrs(self):
        return self.keys()

    def deleteAttr(self, attr):
        """
        Remove the attribute.

        If the attribute is an Attribute, disconnect it.
        """
        data = self.getAttr(attr)
        if hasattr(data, '_node'):
            data._node = None
        return self.pop(attr)

    #- Connections ----
    def getConnections(self):
        """
        Return all connection nodes.

        returns:
            (dict) - dictionary of connection name/Connection nodes.
        """
        connections = dict()
        for k, v in self._inputs.iteritems():
            if v is not None:
                connections[k] = v
        for k, v in self._outputs.iteritems():
            if v is not None:
                connections[k] = v
        return connections

    def inputConnectionNames(self):
        return self._inputs.keys()

    def inputConnection(self, name='input'):
        """
        Returns a named connection.

        params:
            name
        """
        if name in self._inputs:
            node = self._inputs.get(name)
            return self._inputs.get(name)
        return

    def outputConnectionNames(self):
        return self._outputs.keys()

    def outputConnection(self, name='output'):
        if name in self._outputs:
            return self._outputs.get(name)
        return

    def inputNodes(self):
        return self._inputs.values()

    def outputNodes(self):
        return self._outputs.values()

    def addConnection(self, name, input=True):
        """
        Add a connection.

        Default is input
        """
        conn =  self.inputConnectionNames()
        if not input:
            conn = self.outputConnectionNames()

        # return if the connection exists.
        if name in conn:
            ctype = 'input' if input else 'output'
            log.warning('%s connection "%s" already exists.' % (ctype, name))
            return False

        cnode = Connection(self, name=name)
        if input:
            self._inputs.update(**cnode.copy())
        else:
            self._outputs.update(**cnode.copy())
        return True

    def updateGraph(self, msg):
        if hasattr(self.MANAGER, 'updateGraph'):
            self.MANAGER.updateGraph(msg)

    def ParentClasses(self, p=None):
        """
        Return all subclasses.
        """
        base_classes = []
        cl = p if p is not None else self.__class__
        for b in cl.__bases__:
            if b.__name__ != "object":
                base_classes.append(b.__name__)
                base_classes.extend(self.ParentClasses(b))
        return base_classes


class DagEdge(MutableMapping):

    node_class    = "dagedge"
    defaults      = {}
    private       = []
    reserved      = ['_data', '_source', '_dest']
    MANAGER       = None
    """
    Source/dest = Connection nodes.
    """
    def __init__(self, *args, **kwargs):        

        # stash attributes
        self._data              = dict()
        self._source            = dict()
        self._dest              = dict()

        self.src_id             = kwargs.pop('src_id', None)
        self.dest_id            = kwargs.pop('dest_id', None)
        
        self.src_attr           = kwargs.pop('src_attr', 'output')
        self.dest_attr          = kwargs.pop('dest_attr', 'input')

        self.color              = kwargs.pop('color', [180, 180, 180])

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

        if len(args):
            if isinstance(args[0], DagNode):
                dag_src = args[0]
                self.src_id = dag_src.id
                self._source[dag_src.id] = dag_src


            if len(args) > 1:
                if isinstance(args[1], DagNode):
                    dag_dest = args[1]
                    self.dest_id = dag_dest.id
                    self._dest[dag_dest.id] = dag_dest

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

    def __repr__(self):
        return 'DagEdge("%s.%s,%s.%s")' % (self.src_id, self.src_attr, self.dest_id, self.dest_attr)

    def __del__(self):
        """
        Remove the edge instance from any connected connections.
        """
        self.updateGraph('deleting edge: "%s"' % self.id)
        if self._source.keys():
            sconn_name = self._source.keys()[0]
            sconn_node = self._source.get(conn_name)
            sconn_node._edges.pop(self.id)
            self.updateGraph('breaking connection: "%s"' % sconn_name)

        if self._dest.keys():
            dconn_name = self._dest.keys()[0]
            dconn_node = self._source.get(conn_name)
            dconn_node._edges.pop(self.id)
            self.updateGraph('breaking connection: "%s"' % dconn_name)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if key in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        if key in self.reserved:
            super(DagEdge, self).__setattr__(key, value)
        else:
            self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)
    
    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__
    
    @property 
    def data(self):
        data = copy.deepcopy(self._data)
        src_id = self._source.keys()[0]
        dest_id = self._dest.keys()[0]
        return (src_id, dest_id, data)

    def copy(self):
        data = copy.deepcopy(self._data)
        src_id = self._source.keys()[0]
        dest_id = self._dest.keys()[0]
        return (src_id, dest_id, data)
  
    def __deepcopy__(self, *args, **kwargs):
        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad
  
    def update(self, adict={}):
        for (key, value) in list(adict.items()):
            if key in self.private:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(*args, **kwargs):
        """
        Instantiate a new instance from a dictionary.
        """
        self = DagEdge(*args, **kwargs)
        return self

    def updateGraph(self, msg):
        if hasattr(self.MANAGER, 'updateGraph'):
            self.MANAGER.updateGraph(msg)


class Connection(MutableMapping):
    """
    This needs to exlude the node reference (or stash the Node.UUID)

    edges = dict of edge.id, edge node
    """
    node_class    = "connection"
    defaults      = {}
    private       = []
    reserved      = ['_node', '_data', '_edges']

    def __init__(self, node, **kwargs):

        self._node             = node
        self._data             = dict()
        self._edges            = dict()     # connected edges

        self.name              = kwargs.pop('name', 'input')
        self.type              = kwargs.get('type', 'input') 
        self.input_color       = kwargs.pop('input_color', [255,255,51])
        self.output_color      = kwargs.pop('output_color', [0,204,0])
        self.max_connections   = kwargs.pop('max_connections', 1)  # 0 = infinite

        self.update(**kwargs)

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

    def __repr__(self):
        return 'Connection("%s", "%s")' % (self._node.name, self.name)

    def __del__(self):
        """
        When this is deleted, delete the edges that will be orphaned.
        """
        for edge in self._edges.values():
            self.node.updateGraph('deleting connected edge: "%s"' % edge.id)
            del edge

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if key in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        if key in self.reserved:
            super(Connection, self).__setattr__(key, value)
        else:
            self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)

    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__
    
    @property 
    def data(self):
        return {self.name:self._edges.keys()}

    def copy(self):
        #return copy.deepcopy(MutableMapping._data)
        data = copy.deepcopy(self._data)
        name = data.pop('name', 'null')
        return  {name:{ k: data[k] for k in data.keys() if data[k]}}
  
    def __deepcopy__(self, *args, **kwargs):
        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad
  
    def update(self, adict={}):
        for (key, value) in list(adict.items()):
            if key in self.private:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(node, data):
        """
        Instantiate a new instance from a dictionary.
        """
        self = Connection(node, **data)
        return self

    @property
    def color(self):
        if self.type == 'input':
            return self.input_color
        return self.output_color

    @color.setter
    def color(self, value):
        if self.type == 'input':
            self.input_color = value
            return
        self.output_color = val
        return

    @property 
    def node(self):
        """
        Return the parent node object.

        returns:
            (DagNode) - parent node object.
        """
        return self._node

    @property 
    def connection_string(self):
        """
        Returns the connection string.
        """
        return '%s.%s' % (self._node.name, self.name)

    def getEdges(self):
        """
        Returns a list of edge nodes.

        returns:
            (list) - list of DagEdge objects
        """
        return self._edges.values()

    def allEdges(self):
        """
        Returns a list of all edge ids.

        returns:
            (list) - list of edge ids
        """
        return self._edges.keys()

    def addEdge(self, edge, source=True):
        """
        Add and edge to the edges attribute.

        params:
            edge - (DagEdge) edge to add to the connection.

        returns:
            (bool) - edge was added successfully.
        """
        if edge.id in self._edges:
            log.error('edge is already connected.')
            return False

        self._edges[edge.id] = edge

        # if this connection is the source...
        if source:
            edge._source[self.connection_string] = self
        else:
            edge._dest[self.connection_string] = self
        return True



