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
        #self.__dict__['_attributes'] = dict()
        self._attributes        = dict()
        self._metadata          = kwargs.pop('_metadata', None)

        # basic node attributes        
        self.name               = name if name else self.default_name
        self.color              = kwargs.pop('color', self.default_color)

        self.width              = kwargs.pop('width', 100.0)
        self.base_height        = kwargs.pop('base_height', 15.0)

        self.pos                = kwargs.pop('pos', (0,0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # ui
        self._widget            = None  

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __getattr__(self, attr):
        if hasattr(self, '_attributes'):
            if attr in self._attributes:
                attribute = self._attributes.get(attr)
                return attribute.value
            return getattr(self, attr)
        raise AttributeError(attr)
        
    def __setattr__(self, attr, value):
        if hasattr(self, '_attributes'):
            if attr in self._attributes:
                attribute = self._attributes.get(attr)
                if value != attribte.value:
                    attribute.value = value
                return

        # auto-add attributes
        if issubclass(type(value), Attribute):
            self.add_attr(attr, **value)
            return

        Observable.__setattr__(self, attr, value)

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in ['name', 'node_type', 'color', 'width', 'base_height', 'pos', 'enabled', 'orientation']:
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
        attr = Attribute(name, value, node=self, **kwargs)
        self._attributes.update({attr.name:attr})
        return attr

     #- Connections ----