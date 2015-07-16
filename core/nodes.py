#!/usr/bin/env python
import os
import sys
import uuid
import simplejson as json
from collections import OrderedDict as dict

from SceneGraph.core import log, Attribute, Observable
from SceneGraph.options import SCENEGRAPH_PLUGIN_PATH
from SceneGraph import util


class DagNode(Observable):

    default_name  = 'node'
    default_color = [172, 172, 172, 255]
    node_type     = 'dagnode'
    PRIVATE       = ['node_type']
    def __init__(self, name=None, **kwargs):        
        super(DagNode, self).__init__()

        self.__dict__['_attributes'] = dict()
        self._metadata          = kwargs.pop('_metadata', None)

        # basic node attributes        
        self.name               = name if name else self.default_name
        self.color              = kwargs.pop('color', self.default_color)

        self.width              = kwargs.pop('width', 100.0)
        self.base_height        = kwargs.pop('base_height', 15.0)

        self.pos                = kwargs.pop('pos', (0.0, 0.0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # ui
        self._widget            = None  

        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __getattr__(self, name):
        if hasattr(self, '_attributes'):
            if name in self._attributes:
                attribute = self._attributes.get(name)
                return attribute.value
            return super(DagNode, self).__getattr__(name)
        raise AttributeError(name)
        
    def __setattr__(self, name, value):
        if name in self.PRIVATE:
            raise AttributeError('"%s" is a private attribute and cannot be modified.' % name)

        if hasattr(self, '_attributes'):
            if name in self._attributes:
                attribute = self._attributes.get(name)
                if value != attribte.value:
                    attribute.value = value
                return

        # auto-add attributes
        if issubclass(type(value), Attribute):
            self.add_attr(name, **value)
            return

        #setattr(self, name, value)
        super(DagNode, self).__setattr__(name, value)

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in ['name', 'node_type', 'id', 'color', 'width', 'base_height', 'pos', 'enabled', 'orientation']:
            if hasattr(self, attr):
                data[attr] = getattr(self, attr)
        data.update(**self._attributes)
        return data

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value
        return self.graph

    #- Virtual ----
    def evaluate(self):
        """
        Evalutate the node.
        """
        return True

    #- Transform ----
    @property
    def expanded(self):
        height = max(len(self.inputs), len(self.outputs))
        return height > 1

    @property
    def height(self):
        """
        Returns the height of the node (height is determined 
        as base height * max number of connectable attributes)

        returns:
            (float) - total height of the node.
        """
        btm_buffer = 0
        max_conn = max(len(self.inputs), len(self.outputs))
        height = max_conn if max_conn else 1
        if height > 1:
            height+=1
            btm_buffer = self.base_height/2
        return (height * self.base_height) + btm_buffer

    @height.setter
    def height(self, value):
        """
        Set the base height value.

        params:
            value (float) = base height.
        """
        self.base_height=value

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

    def add_attr(self, name, value=None, **kwargs):
        """
        Add an attribute.

         * todo: add attribute type mapper.
        """
        attr = Attribute(name, value, dagnode=self, **kwargs)
        self._attributes.update({attr.name:attr})
        return attr

    def get_attr(self, name):
        """
        Return a named attribute.

        params:
            name (str) - name of attribute.
        """
        if name not in self._attributes:
            self.add_attr(name)
        return self._attributes.get(name)

    def rename_attr(self, name, new_name):
        """
        Rename an attribute.

        params:
            name     (str) - name of attribute.
            new_name (str) - new name.
        """
        if name not in self._attributes:
            raise AttributeError(name)

        if hasattr(self, new_name):
            raise AttributeError('attribute "%s" already exists.' % new_name)

        attr = self._attributes.pop(name)
        attr.name = new_name
        self._attributes.update({attr.name:attr})

    #- Connections ----
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

    @property
    def inputs(self):
        """
        Returns a list of input connection names.

        returns:
            (list) - list of input connection names.
        """
        inputs = []
        for name in self._attributes:
            data = self._attributes.get(name)
            if data.get('connectable') and data.get('connection_type') == 'input':
                inputs.append(name)
        return inputs

    @property
    def outputs(self):
        """
        Returns a list of output connection names.

        returns:
            (list) - list of output connection names.
        """
        inputs = []
        for name in self._attributes:
            data = self._attributes.get(name)
            if data.get('connectable') and data.get('connection_type') == 'output':
                inputs.append(name)
        return inputs

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

        data = self._attributes.get(name)
        if data.get('is_connectable') and data.get('connection_type') == 'input':
            return self._attributes.get(name)
        return

    def get_output(self, name='output'):
        """
        Return a named node output.

        params:
            name (str) - name of output.

        returns:
            (Connection) - connection node.
        """
        if not name in self._attributes:
            return

        data = self._attributes.get(name)
        if data.get('is_connectable') and data.get('connection_type') == 'output':
            return self._attributes.get(name)
        return

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

        data = self._attributes.get(name)
        if data.get('is_connectable'):
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

    #- Plugins/Metadata ----
    @property
    def is_builtin(self):
        """
        Returns true if the node is a member for the is_builtin 
        plugins.

        returns:
            (bool)  - plugin is a builtin.
        """
        import inspect
        plugin_fn = inspect.getfile(self.__class__)
        return SCENEGRAPH_PLUGIN_PATH in plugin_fn

    def Class(self):
        return self.__class__.__name__

    def dag_types(self):
        return [c.__name__ for c in DagNode.__subclasses__()]

    def ParentClasses(self, p=None):
        """
        Returns all of this objects' parent classes.

        params:
            p (obj) - parent object.

        returns:
            (list) - list of parent class names.
        """
        base_classes = []
        cl = p if p is not None else self.__class__
        for b in cl.__bases__:
            if b.__name__ != "object":
                base_classes.append(b.__name__)
                base_classes.extend(self.ParentClasses(b))
        return base_classes