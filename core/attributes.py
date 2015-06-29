#!/usr/bin/env python
from collections import MutableMapping
import simplejson as json
import uuid
import copy
from SceneGraph import util



class Attribute(MutableMapping):
    """
    Generic attribute container.

    Mappings can be added as attributes but still functions as a dictionary.
    Private attributes should be added to the "reserved" attribute. In the
    default node types, the mapping is represented by the "_data" attribute.
    """
    reserved = ["_data", "_node", "_name"]
    def __init__(self, *args, **kwargs):

        # attributes dictionary
        self._data             = dict()
        self._node             = None

        self._name             = args[0] if args else None
        self.default_value     = kwargs.get('default_value', None)
        self.value             = kwargs.get('value', None)
        self.type              = util.attr_type(self.value)
        
        # globals
        self.is_private        = kwargs.get('is_private', False)  # hidden
        self.is_connectable    = kwargs.get('is_connectable', False)
        self.is_user           = kwargs.get('is_user', False)
        self.is_locked         = kwargs.get('is_locked', False)  

    def __str__(self):
        """
        String representation of the object, for printing.
        """
        tmp = self.data
        data = {self.name:tmp}
        return json.dumps(data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        if self.node:
            return 'Attribute("%s.%s")' % (self.node.name, str(self._name))
        return 'Attribute("None.%s")' % str(self._name)

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
                            self._node._attributes.pop(self.name)
                            self._name = value
                            self._node._attributes.update({value:self})
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
    def data(self):
        """
        The data attribute is where you build your object's output. This
        should be hashable data so that this object can be serialized.

        In this example, we are *only* returning attributes that have a value,
        to reduce saved file size.
        """
        data = copy.deepcopy(self._data)
        return { k: data[k] for k in data.keys() if data[k]}

    @property
    def value(self):
        if self._data.get('value') is None:
            return self.default_value
        return self._data.get('value')

    @property 
    def type(self):
        return util.attr_type(self.value)

    @property 
    def node(self):
        return self._node

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

