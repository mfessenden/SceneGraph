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
            return getattr(self, name)
        raise AttributeError(name)
        
    def __setattr__(self, name, value):
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
        Observable.__setattr__(self, name, value)

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

     #- Plugins ----
    @staticmethod
    def dag_types():
        return DagNode.__subclasses__()