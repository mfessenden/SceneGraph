#!/usr/bin/env python
import os
import uuid
import simplejson as json
from collections import MutableMapping
import copy
import sys
from SceneGraph.core import log
from SceneGraph.options import SCENEGRAPH_PLUGIN_PATH
from . import attributes

"""
Goals:
 - hold basic attributes
 - easily add new attributes
 - query connections easily
 - can be cleanly mapped to and from json & new instances
"""


class Container(MutableMapping):
    """
    Generic mappable container class.

    Mappings can be added as attributes but still functions as a dictionary.
    Private attributes should be added to the "reserved" attribute. In the
    default node types, the mapping is represented by the "_data" attribute.
    """
    reserved = ["_data"]
    def __init__(self, *args, **kwargs):

        self._data             = dict()
        self.update(**kwargs)

    def __str__(self):
        """
        String representation of the object, for printing.
        """
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return 'Container()'

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if key in self.reserved:
            super(Container, self).__setattr__(key, value)
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
        """
        The data attribute is where you build your object's output. This
        should be hashable data so that this object can be serialized.

        In this example, we are *only* returning attributes that have a value,
        to reduce saved file size.
        """
        data = copy.deepcopy(self._data)
        #return data
        return {k: data[k] for k in data.keys() if data[k] or type(data[k]) is bool}

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


class DagNode(MutableMapping):

    reserved      = ['_data', '_graph', '_inputs', '_outputs', '_widget', '_attributes', '_metadata']

    def __init__(self, *args, **kwargs):

        self._data              = dict()
        self._inputs            = dict()
        self._outputs           = dict()
        self._attributes        = dict()
        self._metadata          = kwargs.pop('_metadata', None)
        
        self.name               = kwargs.pop('name', 'node1')
        self.node_type          = kwargs.pop('node_type', 'default')

        # reference to the node widget.
        self._widget            = None  

        self.width              = kwargs.pop('width', 100.0)
        self.height_collapsed   = kwargs.pop('height_collapsed', 15.0)
        self.height_expanded    = kwargs.pop('height_expanded', 175.0)

        self.color              = kwargs.pop('color', [172, 172, 172, 255])
        self.expanded           = kwargs.pop('expanded', False)

        self.pos                = kwargs.pop('pos', (0,0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # connections
        input_connections       = kwargs.pop('_inputs', {'input':{}})
        output_connections      = kwargs.pop('_outputs', {'output':{}})


        if type(input_connections) in [list, tuple]:
            input_connections = {'inputs':{k:None for k in input_connections}}

        if type(output_connections) in [list, tuple]:
            output_connections = {'inputs':{k:None for k in output_connections}}

        # add input & output connections
        for input_name, input_attrs in input_connections.iteritems():
            self.addInput(name=input_name, **input_attrs)

        for output_name, output_attrs in output_connections.iteritems():
            self.addOutput(name=output_name, **output_attrs)

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return self.name

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
            #print 'setting Attribute: ', key
            attr.value = value

        # auto-add attributes
        elif hasattr(value, 'keys'):
            #print '%s type: ' % key, value['type']
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
        data.update(_inputs=self._inputs)
        data.update(_outputs=self._outputs)
        #data.update(_attributes=self._attributes)
        data.update(**self._attributes)
        return {k: data[k] for k in data.keys() if data[k] or type(data[k]) is bool}

    def dumps(self):
        print json.dumps(self.data, default=lambda obj: obj.data, indent=5)

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value
        return self.graph

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

    #- Connections ----
    def addInput(self, **kwargs):
        """
        Add a named input to the node.

        returns:
            (object) - Connection object
        """
        name = kwargs.pop('name', 'input')
        node = Connection(self, **kwargs)
        self._inputs.update({name:node})
        return node

    def getInput(self, name='input'):
        """
        Return a named node input.

        params:
            name (str) - name of input.

        returns:
            (Connection) - connection node.
        """
        if name in self._inputs:
            return self._inputs.get(name)
        return

    def addOutput(self, **kwargs):
        """
        Add a named input to the node.

        returns:
            (object) - Connection object
        """
        name = kwargs.pop('name', 'output')
        ctype = kwargs.pop('type', 'output')
        node = Connection(self, type=ctype, **kwargs)
        self._outputs.update({name:node})
        return node

    def getOutput(self, name='output'):
        """
        Return a named node output.

        params:
            name (str) - name of output.

        returns:
            (Connection) - connection node.
        """
        if name in self._outputs:
            return self._outputs.get(name)
        return

    def getConnection(self, name):
        """
        Returns a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (Connection) - connection object.
        """
        conn = None
        if name in self.inputs:
            conn = self._inputs.get(name)

        if name in self.outputs:
            conn = self._outputs.get(name)
        return conn

    def renameConnection(self, old, new):
        """
        Rename a connection.

        params:
            old (str) - old connection name.
            new (new) - new connection name.

        returns:
            (bool) - rename was successful.
        """
        node = self.getConnection(old)
        if node:
            if node.is_input:
                self._inputs.pop(old)
                self._inputs.update({new:node})
                return True

            if node.is_output:
                self._outputs.pop(old)
                self._outputs.update({new:node})
                return True
        return False

    def removeConnection(self, name):
        """
        Remove a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (bool) - connection was removed.
        """
        conn = self.getConnection(name)
        if conn:
            if conn.is_input:
                self._inputs.pop(name)
            else:
                self._outputs.pop(name)
            del conn

    def allConnections(self):
        """
        Returns a list of connections (input & output)

        returns:
            (list) - list of connection names.
        """
        conn = self.inputs 
        conn.extend(self.outputs)
        return conn

    def isConnected(self, name):
        """
        Returns true if the named connection has 
        a connection.

        params:
            name (str) - name of connection to query.

        returns:
            (bool) - connection status.
        """
        conn = self.getConnection(name)
        if not conn:
            return False
        return not conn.is_connectable

    @property
    def inputs(self):
        return self._inputs.keys()

    @property
    def outputs(self):
        return self._outputs.keys()

    #- Attributes ----
    def userAttributes(self):
        """
        Returns a dictionary of user attributes.

        returns:
            (dict) - key, value pairs of user-added attributes.
        """
        result = dict()
        for k, v in self.data.iteritems():
            if k not in self.reserved:
                if hasattr(v, 'keys'):
                    result[k]=v
        return result

    def addAttr(self, name, value=None, input=True, **kwargs):
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
        # TODO: need a way to protect core values
        attr = attributes.Attribute(name, value=value, input=input, **kwargs)
        attr._node = self
        self._attributes.update({attr.name:attr})
        return attr

    def getAttr(self, name):
        """
        Query any user attribute from the node, returning
        the attribute value.

        params:
            name (str) - attribute name to query.

        returns:
            (n/a) - attribute value.
        """
        if name in self.getAttrs():
            attr = self._attributes.get(name)
            return attr.value
        return

    def getAttrNode(self, name):
        """
        Query any attribute from the node, returning
        an Attribute object if the attr is a dict.

        params:
            name (str) - attribute name to query.

        returns:
            (Attribute) - attribute object.
        """
        if name in self.getAttrs():
            return self._attributes.get(name)
        return

    def setAttr(self, name, value):
        """
        Set a named user attribute.

        params:
            name (str) - attribute name to query.
            value (n/a) - value to set.

        returns:
            (n/a) - attribute value.
        """
        if name in self.getAttrs():
            attr = self._attributes.get(name)
            attr.value = value
            return attr.value
        return

    def getAttrs(self):
        """
        Query all user atttributes.

        returns:
            (list) - list of attribute names.
        """
        return self._attributes.keys()

    def deleteAttr(self, name):
        """
        Remove the attribute.

        params:
            name (str) - attribute name to remove.
        
        returns:
            (bool) - attribute was removed.
        """
        attr = self.getAttr(name)
        attr._node = None
        return self._attributes.pop(name)

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


class DagEdge(MutableMapping):
    """
    Notes:
        - needs a reference to source node, dest node.
        - needs to be able to query either at any time.
    """

    reserved = ["_data", "_source", "_dest"]
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
                source_node = args[0]
                self.src_id = source_node.id
                self._source[source_node.id] = source_node

            if len(args) > 1:
                if isinstance(args[1], DagNode):
                    dest_node = args[1]
                    self.dest_id = dest_node.id
                    self._dest[dest_node.id] = dest_node

    def __str__(self):
        """printed"""
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return self.id

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            return default

    def __setitem__(self, key, value):
        if key in self.reserved:
            super(DagEdge, self).__setattr__(key, value)
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
    def data(self):
        data = copy.deepcopy(self._data)
        src_id = self._source.keys()[0]
        dest_id = self._dest.keys()[0]
        #return {k: data[k] for k in data.keys() if data[k] or type(data[k]) is bool}
        return (src_id, dest_id, data)        

    def dumps(self):
        print json.dumps(self.data, default=lambda obj: obj.data, indent=5)

    def updateGraph(self, msg):
        if hasattr(self.MANAGER, 'updateGraph'):
            self.MANAGER.updateGraph(msg)


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
        return 'Connection("%s.%s")' %  (self.node.name, self.type)

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

    def addEdge(self, edge):
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

