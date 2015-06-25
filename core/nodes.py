#!/usr/bin/env python
import os
import uuid
import simplejson as json
from collections import MutableMapping
import copy

"""
Goals:
 - hold basic attributes
 - easily add new attributes
 - query connections easily
 - can be cleanly mapped to and from json & new instances
"""


class DagNode(MutableMapping):

    CLASS_KEY     = "dagnode"
    defaults      = {}
    private       = []  
    _data         = {}

    def __init__(self, nodetype, **kwargs):        

        # stash attributes
        self._inputs            = dict()
        self._outputs           = dict()


        self.node_type          = nodetype
        self.name               = kwargs.pop('name', 'node1')
        self.color              = kwargs.pop('color', [180, 180, 180])
        self.expanded           = kwargs.pop('expanded', False)
        self.width              = kwargs.pop('width', 100)
        self.height_collapsed   = kwargs.pop('height_collapsed', 15)
        self.height_expanded    = kwargs.pop('height_expanded', 175)
        self.pos                = kwargs.pop('pos', (0,0))
        self.enabled            = kwargs.pop('enabled', True)

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if name in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)
    
    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__
  
    def copy(self):
        return copy.deepcopy(self._data)
  
    def __deepcopy__(self, *args, **kwargs):
        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad
  
    def update(self, adict={}):
        for (key, value) in list(adict.items()):
            if key in self.readonly:
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

    def listConnections(self):
        """
        List all connectionsself.
        """
        connections = dict()
        for k, v in self._inputs.iteritems():
            if v is not None:
                connections[k] = v
        for k, v in self._outputs.iteritems():
            if v is not None:
                connections[k] = v
        return connections

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


class Attribute(MutableMapping):

    node_class    = "attribute"
    ATTR_TYPE     = "string"
    defaults      = {}
    private       = []
    _data         = {}

    def __init__(self, name, value, **kwargs):       
        super(Attribute, self).__init__()

        self._data          = dict()
        self.name           = name
        self.value          = value
        self.default_value  = kwargs.get('default_value', None)
        self.type           = self.ATTR_TYPE

        self.is_private     = kwargs.get('is_private', False)
        self.is_connectable = kwargs.get('is_connectable', False)
        self.is_user           = kwargs.get('is_user', False)  

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if name in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)
    
    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__
  
    def copy(self):
        return copy.deepcopy(self._data)
  
    def __deepcopy__(self, *args, **kwargs):
        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad
  
    def update(self, adict={}):
        for (key, value) in list(adict.items()):
            if key in self.readonly:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(name, value, data):
        """
        Instantiate a new instance from a dictionary.
        """
        self = Attribute(name, value, **data)
        return self

    @property
    def value(self):
        if self._data.get('value') is None:
            return self.default_value
        return self._data.get('value')

    @value.setter
    def value(self, value):
        if value is not None:
            self.default_value = None
        return self._data.update(value=value)


class Connection(Attribute):
    """
    This needs to exlude the node reference (or stash the Node.UUID)
    """
    node_class    = "connection"
    parent        = None

    def __init__(self, name, value, node=None, **kwargs):
        super(Connection, self).__init__(name, value, node=node, **kwargs)

        self.parent         = node
        self.node           = node.UUID if hasattr(node, 'UUID') else None

        self.input_color    = kwargs.pop('input_color', [255,255,51])
        self.output_color   = kwargs.pop('output_color', [0,204,0])

        self.update(**kwargs)

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


class DagEdge(MutableMapping):

    node_class    = "dagedge"
    defaults      = {}
    private       = []
    _data         = {}  

    def __init__(self, source, dest, **kwargs):        
        super(DagEdge, self).__init__()

        # stash attributes
        self._source            = dict()
        self._dest              = dict()

        self.source             = source
        seld.dest               = dest
        self.color              = kwargs.pop('color', [180, 180, 180])

        # node unique ID
        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self.update(**kwargs)

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

    def __getitem__(self, key, default=None):
        try:
            return self._data[key]
        except KeyError:
            if name in self.defaults:
                return self.defaults[key]
            if default is None:
                raise
            return default
  
    def __setitem__(self, key, value):
        if key in self.private:
            msg = 'Attribute "%s" in %s object is read only!'
            raise AttributeError(msg % (key, self.__class__.__name__))
        self._data[key] = value
  
    def __delitem__(self, key):
        del self._data[key]
  
    def __getstate__(self):
        return self._data
  
    def __setstate__(self, state):
        self._data.update(self.defaults)
        # update with pickled
        self.update(state)
    
    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__
  
    def copy(self):
        return copy.deepcopy(self._data)
  
    def __deepcopy__(self, *args, **kwargs):
        ad = self.__class__()
        ad.update(copy.deepcopy(self.__dict__))
        return ad
  
    def update(self, adict={}):
        for (key, value) in list(adict.items()):
            if key in self.readonly:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(source, dest, data):
        """
        Instantiate a new instance from a dictionary.
        """
        self = DagEdge(source, dest, **data)
        return self
