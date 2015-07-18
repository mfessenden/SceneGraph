#!/usr/bin/env python
import simplejson as json
import weakref
from collections import OrderedDict as dict
from SceneGraph import util


class Attribute(object):
    """
    Generic Attribute class.
    """
    attribute_type = 'generic'
    REQUIRED       = ['name', 'attr_type', 'value', '_edges'] 

    def __init__(self, name, value, dagnode=None, user=True, **kwargs):

        # private attributes
        self._dag              = weakref.ref(dagnode) if dagnode else None

        self.name              = name
        self.label             = kwargs.get('label', "") 
        self.default_value     = kwargs.get('default_value', "")
        self.value             = value
        self.user              = user

        # stash argument passed to 'type' - overrides auto-type mechanism.
        # * this will become data_type
        self._type             = kwargs.get('type', None)           # 
        self._edges            = kwargs.get('edges', [])

        # globals
        self.private           = kwargs.get('private', False)  # hidden
        self.hidden            = kwargs.get('hidden', False) 
        self.connectable       = kwargs.get('connectable', False)
        self.locked            = kwargs.get('locked', False)
        self.required          = kwargs.get('required', False)

        # connection
        self.connection_type   = kwargs.get('connection_type', 'input')
        self.max_connections   = kwargs.get('max_connections', 1)  # 0 = infinite

    def __str__(self):
        return json.dumps({self.name:self.data}, indent=4)

    def __repr__(self):
        return json.dumps({self.name:self.data}, indent=4)

    def update(self, **kwargs):
        """
        Update the data dictionary.

        * todo: can't pass as **kwargs else we lose the order (why is that?)
        """
        for name, value in kwargs.iteritems():
            #print '# adding attribute: "%s"' % name
            setattr(self, name, value)

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in ['label', 'value', 'attr_type', 'private', 'hidden', 'connectable', 'locked', 'required', 'user']:
            if hasattr(self, attr):
                value = getattr(self, attr)
                #if value or attr in self.REQUIRED:
                data[attr] = value
        return data

    @property
    def dagnode(self):
        return self._dag()

    @property
    def attr_type(self):
        if self._type is not None:
            return self._type
        return util.attr_type(self.value)

    @attr_type.setter
    def attr_type(self, val):
        self._type = val

    @property
    def is_input(self):
        if not self.connectable:
            return False
        return self.connection_type == 'input'

    @property
    def is_output(self):
        if not self.connectable:
            return False
        return self.connection_type == 'output'

    def rename(self, name):
        """
        Rename the attribute.
        """
        old_name = self.name
        self.name = name
