#!/usr/bin/env python
from collections import MutableMapping
import simplejson as json
import uuid
from SceneGraph import util


__all__  = ['StringAttribute', 'IntegerAttribute', 'FloatAttribute', 'attribute_factory']



class Attribute(MutableMapping):

    node_class    = "attribute"
    ATTR_TYPE     = None
    defaults      = {}
    private       = []

    def __init__(self, name, value, **kwargs):       
        super(Attribute, self).__init__()

        MutableMapping._data   = dict()
        self.name              = name
        self.value             = value
        self.default_value     = kwargs.get('default_value', None)
        self.type              = self.ATTR_TYPE

        self.is_private        = kwargs.get('is_private', False)
        self.is_connectable    = kwargs.get('is_connectable', False)
        self.is_user           = kwargs.get('is_user', False)  

    def __str__(self):
        data = {self.__class__.__name__:self._data}
        return json.dumps(data, indent=4)

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


class StringAttribute(Attribute):

    ATTR_TYPE     = "string"
    parent        = None

    def __init__(self, name, value, node=None, **kwargs):
        super(StringAttribute, self).__init__(name, value, node=node, **kwargs)


class FloatAttribute(Attribute):

    ATTR_TYPE     = "float"
    parent        = None

    def __init__(self, name, value, node=None, **kwargs):
        super(FloatAttribute, self).__init__(name, value, node=node, **kwargs)


class IntegerAttribute(Attribute):

    ATTR_TYPE     = "int"
    parent        = None

    def __init__(self, name, value, node=None, **kwargs):
        super(IntegerAttribute, self).__init__(name, value, node=node, **kwargs)




def attribute_factory(name, value):
    """
    Returns an attribute type based on the
    given value.
    """
    if util.is_number(value):
        if type(value) is float:
            return FloatAttribute(name, value)
        if type(value) is int:
            return IntegerAttribute(name, value)


