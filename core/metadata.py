#!/usr/bin/env python
import os
from copy import deepcopy
from collections import OrderedDict as dict
import simplejson as json
import re

from SceneGraph.core import log


regex = dict(
     section        = re.compile(r"^\[[^\]\r\n]+]"),
     section_value  = re.compile(r"\[(?P<attr>[\w]*?) (?P<value>[\w\s]*?)\]$"),
     properties     = re.compile("(?P<name>[\.\w]*)\s*(?P<type>\w*)\s*(?P<value>.*)$"),
     )


PROPERTIES = dict(
    min         = 'minimum value',
    max         = 'maximum value',
    default     = 'default value',
    label       = 'node label',
    private     = 'attribute is private (hidden)',
    desc        = 'attribute description,'
)


class MetadataParser(object):
    """
    class MetadataParser:

        DESCRIPTION:
            read and parse node metadata (.mtd) files to build a 
            template for the AttributeEditor widget.

            Metadata is stored as:

            [section $name]

                [attr $attr_name]
                    $property_name      $property_type      $property_value

    """
    def __init__(self, filename=None, **kwargs):

        self._template      = filename
        self._data          = dict()
        self._initialized   = False

        if filename:
            self._data = self.parse(filename)
            self._initialized = True

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

    def parse(self, filename):
        """
        Parses a single template file. Data is structured into groups
        of attributes (ie: 'Transform', 'Attributes')

        params:
            filename (str) - file on disk to read.
        """
        if self._initialized:
            self.initialize()

        log.info('reading metadata file: "%s"' % filename)
        data = dict()
        if filename is not None:
            if os.path.exists(filename):

                parent = data
                attr_name = None  

                for line in open(filename,'r'):
                    
                    #remove newlines
                    line = line.rstrip('\n')
                    if not line.startswith("#") and not line.startswith(';') and line.strip() != "":
                        # parse sections
                        # remove leading spaces
                        rline = line.lstrip(' ')

                        # section/attribute header match
                        if re.match(regex.get("section"), rline):                            
                              
                            section_obj = re.search(regex.get("section_value"), rline)

                            if section_obj:
                                section_type = section_obj.group('attr')
                                section_value = section_obj.group('value')

                                # parse groups
                                if section_type == 'group':
                                    if section_value not in parent:
                                        parent = data
                                        group_data = dict()
                                        # set the current parent
                                        parent[section_value] = group_data
                                        parent = parent[section_value]
                                        #print '\nGroup: ', section_value

                                if section_type == 'attr':            
                                    attr_data = dict()
                                    parent[section_value] = attr_data
                                    attr_name = section_value
                                    #print '   Attribute: ', attr_name

                                if section_type in ['input', 'output']:            
                                    conn_data = dict()
                                    conn_data.update(connectable=True)
                                    conn_data.update(connection_type=section_type)
                                    parent[section_value] = conn_data
                                    attr_name = section_value
                                    #print '   Attribute: ', attr_name

                        else:
                            prop_obj = re.search(regex.get("properties"), rline)

                            if prop_obj:
                                pname = prop_obj.group('name')
                                ptype = prop_obj.group('type')
                                pvalu = prop_obj.group('value')

                                value = pvalu
                                if ptype in ['BOOL', 'INPUT', 'OUTPUT']:
                                    if ptype == 'BOOL':
                                        value = True if pvalu == 'true' else False

                                    # return connection types
                                    if ptype in ['INPUT', 'OUTPUT']:

                                        # data type: pvalu = FILE, DIRECTORY, ETC.
                                        value = pvalu.lower()

                                # try and get the actual value
                                else:
                                    try:
                                        value = eval(pvalu)
                                    except:
                                        log.warning('cannot parse default value of "%s.%s": "%s" (%s)' % (attr_name, pname, pvalu, filename))
                                #print '     property: %s (%s)' % (prop_obj.group('name'), attr_name)
                                properties = {pname: {'type':ptype, 'value':value}}
                                parent[attr_name].update(properties)

        return data



