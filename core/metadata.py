#!/usr/bin/env python
import os
from collections import OrderedDict as dict
import simplejson as json
import re
from SceneGraph.core import log


DATA_EXPRS = dict(
     group_name = re.compile("\[(?P<group_name>\w+)\]"),
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
                if val:
                    if type(val) == str:
                        current_category = val
                        if current_category not in self._data:
                            self._data[current_category]=dict()

                    if type(val) in [dict]:
                        self._data.get(current_category).update(val)


    def _parse_line(self, l):
        """
        parse a line of data.
        """
        result = None
        if ":" in l:
            l.replace(" ", "")
            values = l.split(":")

            if values:
                if len(values) >= 3:
                    attr_name = values[0]
                    attr_type = values[1]
                    default_value = None
                    attributes = []

                    # in the event there is no default value
                    if not '-' in values[2]:
                        default_value = values[2]
                    else:
                        attributes = values[2].split('-')

                    if len(values) >= 4:
                        attributes = values[3].split('-')

                    result = dict()
                    result[attr_name] = dict(type=attr_type, default_value=default_value)

                    # parse attributes
                    if attributes:
                        for a in attributes:
                            if a:
                                if a == 'p;':
                                    result.get(attr_name).update(private=True)

        if '[' in l:
            data = re.search(DATA_EXPRS.get('group_name'), l)
            if data:
                result = data.group('group_name')
        return result