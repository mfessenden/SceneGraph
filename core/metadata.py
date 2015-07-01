#!/usr/bin/env python
import os
from copy import deepcopy
from collections import OrderedDict as dict
import simplejson as json
import re

from SceneGraph.core import log


DATA_EXPRS = dict(
     group_name = re.compile("\[(?P<group_name>\w+)\]"),
     attribute  = re.compile("^(?P<attr_name>\w+):\s?(?P<attr_type>\w+):?\s?(?P<tail>.+);$"),
     )


DATA_PARAMS = dict(
    p = 'private',
    h = 'hidden',
    u = 'user',
    )


class DataParser(object):
    """
    Node metadata template parser
    """
    def __init__(self, filename=None, **kwargs):

        self._template  = filename
        self._data      = dict()

    def initialize(self):
        """
        Initialize the object.
        """
        self._template = None
        self._data = dict()

    @property
    def data(self):
        import simplejson as json
        return json.dumps(self._data, indent=4)

    def read(self, filename):
        """
        Read a template file.
        """
        if os.path.exists(filename):
            data = open(filename).read()
            log.debug('reading metadata file "%s".' % filename)
            current_category = None
            for line in data.split('\n'):
                val = self._parse_line(line)
                #print json.dumps(val, indent=5)
                if val:
                    if 'group_name' in val:
                        current_category = val.get('group_name')
                        if current_category not in self._data:
                            self._data[current_category]=dict()
                    else:
                        self._data.get(current_category).update(val)

    def _parse_line(self, l):
        """
        parse a line of data.

        params:
            l (str) - line from a data file.

        returns:
            (dict) - current line parsed.
        """
        result = dict()
        for ftyp, fexpr in DATA_EXPRS.items():
            attr_match = re.search(fexpr, l)
            if attr_match:
                data = attr_match.groupdict()
                if 'attr_name' in data:
                    attr_name = data.pop('attr_name')
                    result[attr_name] = dict()
                    if 'tail' in data:
                        tail_data = data.pop('tail')
                        attrs = self._parse_tail(tail_data)
                        if attrs:
                            result.get(attr_name).update(**attrs)
                    result.get(attr_name).update(**data)
                else:
                    result.update(data)
        return result

    def _parse_tail(self, l):
        """
        Parse attributes from a line of data.
        """
        attributes = dict()
        l=l.replace(" ", "")
        values = l.split(':')
        if values:
            for v in values:
                if '-' in v:
                    attrs = [x for x in list(v) if x!="-"]
                    if attrs:
                        for attr in attrs:
                            if attr in DATA_PARAMS:
                                attributes[DATA_PARAMS[attr]] = True
                else:
                    attributes.update(default_value=v)
        return attributes