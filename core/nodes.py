#!/usr/bin/env python
import os
import uuid
import simplejson as json
from collections import MutableMapping
from collections import OrderedDict as dict
import copy
import sys
from SceneGraph.core import log
from SceneGraph.options import SCENEGRAPH_PLUGIN_PATH
from SceneGraph import util


"""
from SceneGraph import core
g=core.Graph('/Users/michael/graphs/connections.json')
n2=g.get_node('node2')[0]
"""


class DagNode(MutableMapping):

    reserved      = ['_data', '_graph', '_widget', '_attributes', '_metadata', '_command']
    default_color = [172, 172, 172, 255]

    def __init__(self, *args, **kwargs):

        # special attributes
        self._data              = dict()
        self._attributes        = dict()
        self._metadata          = kwargs.pop('_metadata', None)
        self.color              = kwargs.pop('color', self.default_color)

        self.default_name       = 'dag'
        self.name               = kwargs.pop('name', self.default_name)
        self.node_type          = kwargs.pop('node_type', 'default')

        self.width              = kwargs.pop('width', 100.0)
        self.base_height        = kwargs.pop('base_height', 15.0)

        self.pos                = kwargs.pop('pos', (0,0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # SUBCLASS
        # reference to the node widget.
        self._widget            = None  

        # connections
        input_connections       = kwargs.pop('inputs', {'input':{}})
        output_connections      = kwargs.pop('outputs', {'output':{}})


        if type(input_connections) in [list, tuple]:
            input_connections = {'inputs':{k:None for k in input_connections}}

        if type(output_connections) in [list, tuple]:
            output_connections = {'inputs':{k:None for k in output_connections}}

        # add input & output connections
        for input_name, input_attrs in input_connections.iteritems():
            self.add_input(name=input_name, **input_attrs)

        for output_name, output_attrs in output_connections.iteritems():
            self.add_output(name=output_name, **output_attrs)

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return '%s : %s' % (self.node_type, self.name)

    def __getitem__(self, key, default=None):
        try:
            if key in self._attributes:
                attr = self._attributes.get(key)
                return attr.value

            return self._data[key]
        except KeyError, e:
            return default

    def __setitem__(self, key, value):
        if key in self.reserved:
            super(DagNode, self).__setattr__(key, value)

        elif key in self._attributes:
            attr = self._attributes.get(key)
            attr.value = value

        # auto-add attributes
        elif hasattr(value, 'keys'):
            self.addAttr(key, **value)
        else:
            self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    def __contains__(self, key):
        return key in self._data

    __setattr__ = __setitem__
    __delattr__ = __delitem__

    def evaluate(self):
        """
        Virtual method.
        """
        return False

    @property
    def data(self):
        data = copy.deepcopy(self._data)
        #data.update(_attributes=self._attributes)
        data.update(**self._attributes)
        return {k: data[k] for k in data.keys() if data[k] or type(data[k]) is bool}

    def dumps(self):
        data = copy.deepcopy(self)
        data._graph = 'SceneGraph.core.Graph'
        data._widget = ""
        print json.dumps(data, indent=5)

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value
        return self.graph

    @property
    def expanded(self):
        height = max(len(self.inputs), len(self.outputs))
        return height > 1

    @property
    def height(self):
        btm_buffer = 0
        height = max(len(self.inputs), len(self.outputs))
        if height > 1:
            height+=1
            btm_buffer = self.base_height/2
        return (height * self.base_height) + btm_buffer

    @height.setter
    def height(self, value):
        self.base_height=value

    #- Connections ----
    def add_input(self, **kwargs):
        """
        Add a named input to the node.

        returns:
            (object) - Attribute object
        """
        name = kwargs.pop('name', 'input')
        connection_type = kwargs.pop('connection_type', 'input')
        is_connectable = kwargs.pop('is_connectable', True)
        return self.addAttr(name, is_connectable=is_connectable, connection_type=connection_type, **kwargs)

    def get_input(self, name='input'):
        """
        Return a named node input.

        params:
            name (str) - name of input.

        returns:
            (Connection) - connection node.
        """
        if not name in self._attributes:
            return

        attr_data = self._attributes.get(attr_name)
        if attr_data.get('is_connectable') and attr_data.get('connection_type') == 'input':
            return self._attributes.get(attr_name)
        return

    def add_output(self, **kwargs):
        """
        Add a named output to the node.

        returns:
            (object) - Attribute object
        """
        name = kwargs.pop('name', 'output')
        connection_type = kwargs.pop('connection_type', 'output')
        is_connectable = kwargs.pop('is_connectable', True)
        return self.addAttr(name, is_connectable=is_connectable, connection_type=connection_type, **kwargs)

    def get_output(self, name='input'):
        """
        Return a named node input.

        params:
            name (str) - name of input.

        returns:
            (Connection) - connection node.
        """
        if not name in self._attributes:
            return

        attr_data = self._attributes.get(attr_name)
        if attr_data.get('is_connectable') and attr_data.get('connection_type') == 'output':
            return self._attributes.get(attr_name)
        return

    def input_connections(self):
        """
        Returns a list of connected DagNodes.

        returns:
            (list) - list of DagNode objects.
        """
        connected_nodes = []
        for edge in self.graph.network.edges(data=True):
            # edge = (id, id, {atttributes})
            srcid, destid, attrs = edge
            if destid == self.id:
                if srcid in self.graph.dagnodes:
                    connected_nodes.append(self.graph.dagnodes.get(srcid))
        return connected_nodes

    def output_connections(self):
        """
        Returns a list of connected DagNodes.

        returns:
            (list) - list of DagNode objects.
        """
        connected_nodes = []
        for edge in self.graph.network.edges(data=True):
            # edge = (id, id, {atttributes})
            srcid, destid, attrs = edge
            if srcid == self.id:
                if destid in self.graph.dagnodes:
                    connected_nodes.append(self.graph.dagnodes.get(destid))
        return connected_nodes

    @property
    def is_input_connection(self):
        """
        Returns true if the node is an input connection.
        """
        return bool(self.output_connections())
 
    @property
    def is_output_connection(self):
        """
        Returns true if the node is an output connection.
        """
        return bool(self.input_connections())   

    def get_connection(self, name):
        """
        Returns a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (Attribute) - connection object.
        """
        conn = None
        if name not in self._attributes:
            return 

        attr_data = self._attributes.get(name)
        if attr_data.get('is_connectable'):
            return self._attributes.get(name)
        return

    def rename_connection(self, old, new):
        """
        Rename a connection.

        params:
            old (str) - old connection name.
            new (new) - new connection name.

        returns:
            (bool) - rename was successful.
        """
        conn = self.get_connection(old)
        if conn:
            conn.name = new
            return True
        return False

    def remove_connection(self, name):
        """
        Remove a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (bool) - connection was removed.
        """
        if name in self._attributes:
            if self._attributes.get(name).get('is_connectable'):
                conn = self._attributes.pop(name)
                del conn 
                return True 
        return False

    @property
    def connections(self):
        """
        Returns a list of connections (input & output)

        returns:
            (list) - list of connection names.
        """
        conn_names = []
        for name in self._attributes:
            if self._attributes.get(name).get('is_connectable'):
                conn_names.append(name)
        return conn_names

    def is_connected(self, name):
        """
        Returns true if the named connection has 
        a connection.

        params:
            name (str) - name of connection to query.

        returns:
            (bool) - connection status.
        """
        conn = self.get_connection(name)
        if not conn:
            return False
        return not conn.is_connectable

    @property
    def inputs(self):
        """
        Returns a list of input connection names.
        """
        input_names = []
        for attr_name in self._attributes:
            attr_data = self._attributes.get(attr_name)
            if attr_data.get('is_connectable') and attr_data.get('connection_type') == 'input':
                input_names.append(attr_name)
        return input_names

    @property
    def outputs(self):
        """
        Returns a list of output connection names.
        """
        input_names = []
        for attr_name in self._attributes:
            attr_data = self._attributes.get(attr_name)
            if attr_data.get('is_connectable') and attr_data.get('connection_type') == 'output':
                input_names.append(attr_name)
        return input_names

    #- Attributes ----
    def attributes(self, *args):
        """
        Returns a dictionary of connections attributes.

        returns:
            (dict) - { connection name: Attribute }
        """
        if not args:
            return self._attributes.values()
        else:
            attrs = [x for x in self._attributes.values() if x.name in args]
            if attrs and len(attrs) == 1:
                return attrs[0]
            return attrs

    def addAttr(self, name, value=None, is_connectable=False, **kwargs):
        """
        Add attributes to the current node.

         *todo: need a way to protect default attributes.

        params:
            name  (str)  - attribute name to add.
            value (n/a)  - value
            input (bool) - attribute represents an input connection.

        returns:
            (Attribute) - attribute object.
        """
        attr = Attribute(name, value=value, is_connectable=is_connectable, **kwargs)
        attr._node = self
        self._attributes.update({attr.name:attr})
        return attr

    @classmethod
    def ParentClasses(cls, p=None):
        """
        Return all subclasses.
        """
        base_classes = []
        cl = p if p is not None else cls.__class__
        for b in cl.__bases__:
            if b.__name__ != "object":
                base_classes.append(b.__name__)
                base_classes.extend(cls.ParentClasses(b))
        return base_classes


'''
class Connection(MutableMapping):
    
    reserved = ["_data", "_edges", "_node"]
    def __init__(self, *args, **kwargs):

        self._data             = dict()
        self._edges            = []        # connected edges

        self._node             = None
        self.type              = kwargs.get('type', 'input') 
        self.input_color       = kwargs.pop('input_color', [255, 255, 51])
        self.output_color      = kwargs.pop('output_color', [0, 204, 0])
        self.max_connections   = kwargs.pop('max_connections', 1)  # 0 = infinite
        self.is_input          = True if self.type == 'input' else False

        # input nodes can have only one connection
        if self.type == 'input':
            self.max_connections = 1

        for arg in args:
            if isinstance(arg, DagNode):
                self._node = arg

        self.update(**kwargs)

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)
'''

class Attribute(MutableMapping):
    """
    Generic attribute container.

    Mappings can be added as attributes but still functions as a dictionary.
    Private attributes should be added to the "reserved" attribute. In the
    default node types, the mapping is represented by the "_data" attribute.
    
    Need to add:
    """
    reserved = ["_data", "_node", "_name", "_type"]
    def __init__(self, *args, **kwargs):

        # attributes dictionary
        self._data             = dict()
        self._node             = None

        self._name             = args[0] if args else None
        self.default_value     = kwargs.get('default_value', "")
        self.value             = kwargs.get('value', "")

        # stash argument passed to 'type' - overrides auto-type mechanism.
        self._type             = kwargs.get('type', None)

        # globals
        self.is_private        = kwargs.get('is_private', False)  # hidden
        self.is_connectable    = kwargs.get('is_connectable', False)
        self.is_user           = kwargs.get('is_user', False)
        self.is_locked         = kwargs.get('is_locked', False)
        self.is_required       = kwargs.get('is_required', False)

        # connection
        self.connection_type   = kwargs.get('connection_type', 'input')
        self.max_connections   = kwargs.pop('max_connections', 1)  # 0 = infinite

        if self.is_input:
            self.max_connections = 1

    def dumps(self):
        dstr = "\"%s\"" % self.name
        dstr += json.dumps(self.data, default=lambda obj: obj.data, indent=5)
        print dstr

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return (self.name) == (other.name)

    def __str__(self):
        """
        String representation of the object, for printing.
        """
        data = self.data
        #data = {self.name:data}
        return json.dumps(data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        valstr = '"%s"' % self.value
        if self.type in ['float2', 'int2', 'float3', 'int3']:
            valstr = str(self.value)
        return '{"value":%s, "type":"%s"}' % (valstr, self.type)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if key in self.reserved:
            super(Attribute, self).__setattr__(key, value)
        else:
            if key == 'value':
                valtyp = util.attr_type(value)
                if self.type != valtyp:
                    self.type = valtyp

            if key == 'name':
                if self.node:
                    if self._name:
                        if self._name != value:
                            old_name = self._name
                            self.node._attributes.pop(self._name)
                            self._name = value
                            self.node._attributes.update({value:self})

                            #update the network graph
                            self.node.graph.rename_connection(self.node.id, old_name, value)
                            return

            self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    __setattr__ = __setitem__
    __delattr__ = __delitem__
    
    @property 
    def node(self):
        return self._node

    @property
    def name(self):
        return self._name

    @property
    def is_input(self):
        return self.connection_type == 'input'

    @property
    def is_output(self):
        return self.connection_type == 'output'

    @property
    def data(self):
        """
        The data attribute is where you build your object's output. This
        should be hashable data so that this object can be serialized.

        In this example, we are *only* returning attributes that have a value,
        to reduce saved file size.
        """
        data = copy.deepcopy(self._data)
        data.update(type=self.type)
        return {k: data[k] for k in data.keys() if data[k] or k in ['value']}

    @property
    def value(self):
        if self._data.get('value') is None:
            return self.default_value
        return self._data.get('value')

    @property 
    def type(self):
        """
        If the attribute type was passed in the contstructor,
        use that instead of the auto-parsed type.
        """
        if self.is_user:
            if self._type is not None:
                return self._type
        return util.attr_type(self.value)

    @type.setter 
    def type(self, val):
        self._type = val
        return self.type

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


class Connection(MutableMapping):
    
    reserved = ["_data", "_edges", "_node"]

    def __init__(self, *args, **kwargs):

        self._data             = dict()
        self._edges            = []        # connected edges

        self._node             = None
        self.type              = kwargs.get('type', 'input') 
        self.input_color       = kwargs.pop('input_color', [255, 255, 51])
        self.output_color      = kwargs.pop('output_color', [0, 204, 0])
        self.max_connections   = kwargs.pop('max_connections', 1)  # 0 = infinite
        self.is_input          = True if self.type == 'input' else False

        # input nodes can have only one connection
        if self.type == 'input':
            self.max_connections = 1

        for arg in args:
            if isinstance(arg, DagNode):
                self._node = arg

        self.update(**kwargs)

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return '"%s.%s"' %  (self.node.name, self.type)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if key in self.reserved:
            super(Connection, self).__setattr__(key, value)
        else:
            self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, key, default=None):
        try:
            return self.__getitem__(key, default)
        except KeyError as e:
            raise AttributeError(e.args[0])

    def __contains__(self, key):
        return key in self._data

    __setattr__ = __setitem__
    __delattr__ = __delitem__

    @property
    def node(self):
        return self._node

    @property
    def data(self):
        data = copy.deepcopy(self._data)
        # breakage here, no doubt
        data.update(_edges=self._edges)
        return data

    #- Connection Attributes ---
    @property
    def is_connectable(self):
        """
        Returns true if the connection is able to be 
        connected to an edge.

        returns:
            (bool) - edge can be connected.
        """
        if self.max_connections == 0:
            return True
        return len(self._edges) < self.max_connections

    def connectedEdges(self):
        """
        Returns a list of connected edge ids.

        returns:
            (list) - list of edge ids.
        """
        if not self._edges:
            return []
        return [edge.id for edge in self._edges]

    def add_edge(self, edge):
        """
        Add an edge to the connection.

        params:
            edge (DagEdge) - edge node.

        returns:
            (bool) - connection was successful.
        """
        if edge.id not in self.connectedEdges():
            self._edges.append(edge.id)
            return True
        return False

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
            return self.color
        self.output_color = val
        return self.color

    @property 
    def node(self):
        """
        Return the parent node object.

        returns:
            (DagNode) - parent node object.
        """
        return self._node


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)

