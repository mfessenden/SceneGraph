#!/usr/bin/env python
import simplejson as json
import weakref
from collections import OrderedDict as dict
from SceneGraph import util


class Attribute(object):
    """
    Generic Attribute class.
    """
    def __init__(self, name, value, dagnode=None, **kwargs):

        # private attributes
        self._dag              = weakref.ref(dagnode) if dagnode else None

        self.name              = name
        self.default_value     = kwargs.get('default_value', "")
        self.value             = value

        # stash argument passed to 'type' - overrides auto-type mechanism.
        self._type             = kwargs.get('type', None)           # 

        # globals
        self.private        = kwargs.get('private', False)  # hidden
        self.hidden         = kwargs.get('hidden', False) 
        self.connectable    = kwargs.get('connectable', False)
        self.locked         = kwargs.get('locked', False)
        self.required       = kwargs.get('required', False)

        # connection
        self.connection_type   = kwargs.get('connection_type', 'input')
        self.max_connections   = kwargs.get('max_connections', 1)  # 0 = infinite

    def __str__(self):
        d = self.data
        name = d.pop('name')
        return json.dumps({name:d}, indent=4)

    def __repr__(self):
        d = self.data
        name = d.pop('name')
        return json.dumps({name:d}, indent=4)

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in ['name', 'value', 'attr_type', 'private', 'hidden', 'connectable', 'locked', 'required']:
            if hasattr(self, attr):
                data[attr] = getattr(self, attr)
        return data

    @property
    def dagnode(self):
        return self._dag()

    @property
    def attr_type(self):
        if self._type is not None:
            return self._type
        return util.attr_type(self.value)

    def rename(self, name):
        """
        Rename the attribute.
        """
        old_name = self.name
        self.name = name
