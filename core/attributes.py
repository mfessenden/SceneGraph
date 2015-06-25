#!/usr/bin/env python
from collections import MutableMapping
import simplejson as json
import uuid
import copy
from SceneGraph import util


__all__  = ['Attribute', 'StringAttribute', 'IntegerAttribute', 'FloatAttribute', 'attribute_factory']



class Attribute(MutableMapping):

    node_class    = "attribute"
    defaults      = {}
    private       = []

    def __init__(self, *args, **kwargs):       

        # attributes dictionary
        self._data             = dict()

        self.name              = args[0] if args else None
        self.default_value     = kwargs.get('default_value', None)
        self.value             = kwargs.get('value', None)
        self.type              = type(self.value) if self.value else 'null'
        
        # globals
        self.is_private        = kwargs.get('is_private', False)  # hidden
        self.is_connectable    = kwargs.get('is_connectable', False)
        self.is_user           = kwargs.get('is_user', False)
        self.is_locked         = kwargs.get('is_locked', False)   

    def __str__(self):
        data = self.copy()
        return json.dumps(data, indent=4)

    def __repr__(self):
        return json.dumps(self.__dict__(), indent=5)

    def __dict__(self):
        """
        Filter the current dictionary to only return set values.
        """
        data = self.copy()
        name = data.keys()[0]
        new_data = data.get(name)
        return  {name:{ k: new_data[k] for k in new_data.keys() if new_data[k]}}

    def __getitem__(self, key, default=None):
        try:
            if key in self._data:
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

        if key == '_data':
            super(Attribute, self).__setattr__(key, value)
        else:
            self._data[key] = value
            if key == 'value':
                valtyp = util.attr_type(value)
                if self.type != valtyp:
                    self.type = valtyp

  
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
        #return copy.deepcopy(MutableMapping._data)
        data = copy.deepcopy(self._data)
        name = data.pop('name', 'null')
        return {name:data}

    def __deepcopy__(self, *args, **kwargs):
        """
        Defines the result of a deepcopy operation.
        """
        data = copy.deepcopy(self._data)
        name = data.pop('name', None)
        ad = self.__class__(name, **data)
        #ad.update(**copy.deepcopy(self._data)) # works, but returns empty object
        return ad
  
    def update(self, **kwargs):
        for (key, value) in list(kwargs.items()):
            if key in self.private:
                continue
            self.__setitem__(key, value)

    def __iter__(self):
        return iter(self._data)
  
    def __len__(self):
        return len(self._data)

    @classmethod
    def node_from_meta(name, data):
        """
        Instantiate a new instance from a dictionary.
        """
        self = Attribute(name, **data)
        return self

    @property
    def value(self):
        if self._data.get('value') is None:
            return self.default_value
        return self._data.get('value')



class StringAttribute(Attribute):

    ATTR_TYPE     = "string"
    parent        = None

    def __init__(self, name, **kwargs):
        super(StringAttribute, self).__init__(name, **kwargs)


class FloatAttribute(Attribute):

    ATTR_TYPE     = "float"
    parent        = None

    def __init__(self, name, **kwargs):
        super(FloatAttribute, self).__init__(name, **kwargs)


class IntegerAttribute(Attribute):

    ATTR_TYPE     = "int"
    parent        = None

    def __init__(self, name, **kwargs):
        super(IntegerAttribute, self).__init__(name, **kwargs)



def attribute_factory(name, value, **kwargs):
    """
    Returns an attribute type based on the
    given value.
    """
    if util.is_number(value):
        if type(value) is float:
            return FloatAttribute(name, value=value, **kwargs)
        if type(value) is int:
            return IntegerAttribute(name, value=value, **kwargs)
    elif util.is_string(value):
        return StringAttribute(name, value=value, **kwargs)

    else:
        print '# Attribute error: ', value
        return 

