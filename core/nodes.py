#!/usr/bin/env python
import os
import sys
import uuid
import simplejson as json
from collections import OrderedDict as dict
from SceneGraph.core import log, Attribute, Signal, Event
from SceneGraph.options import SCENEGRAPH_PATH, SCENEGRAPH_PLUGIN_PATH, SCENEGRAPH_METADATA_PATH
from SceneGraph import util


PROPERTY_TYPES = dict(
    simple              = ['FLOAT', 'STRING', 'BOOL', 'INT'],
    arrays              = ['FLOAT2', 'FLOAT3', 'INT2', 'INT3', 'COLOR'],
    data_types          = ['FILE', 'MULTI', 'MERGE', 'NODE', 'DIR'],   
    )


class Node(object):

    nodeNameChanged     = Event('nodeNameChanged')
    nodePositionChanged  = Event('nodePositionChanged')
    nodeAttributeUpdated = Event('nodeAttributeUpdated')

    default_color = [172, 172, 172, 255]
    PRIVATE       = ['node_type']
    REQUIRED      = ['name', 'node_type', 'id', 'color', 'docstring', 'width', 
                      'base_height', 'force_expand', 'pos', 'enabled', 'orientation']

    def __init__(self, name=None, **kwargs):

        self._attributes        = dict()
        self._metadata          = Metadata(self)

        # basic node attributes        
        self.name               = name if name else self.default_name
        self.color              = kwargs.pop('color', self.default_color)
        self.docstring          = ""
        self._graph             = kwargs.pop('_graph', None)

        self.width              = kwargs.pop('width', 100.0)
        self.base_height        = kwargs.pop('base_height', 15.0)
        self.force_expand       = kwargs.pop('force_expand', False)

        self.pos                = kwargs.pop('pos', (0.0, 0.0))
        self.enabled            = kwargs.pop('enabled', True)
        self.orientation        = kwargs.pop('orientation', 'horizontal')

        # metadata
        metadata                = kwargs.pop('metadata', dict())
        attributes              = kwargs.pop('attributes', dict())

        # if the node metadata isn't passed from another class, 
        # read it from disk
        if not metadata:
            metadata = self.read_metadata()

        # ui
        self._widget            = None  

        UUID = kwargs.pop('id', None)
        self.id = UUID if UUID else str(uuid.uuid4())
        self._metadata.update(metadata)

        # update attributes (if reading from scene)
        if attributes:
            for attr_name, properties in attributes.iteritems():
                if attr_name in self._attributes:
                    self._attributes.get(attr_name).update(**properties)
                else:
                    self.add_attr(attr_name, **properties)


    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)
    
    def __getattr__(self, name):
        if name in self._attributes:
            attribute = self._attributes.get(name)
            return attribute.value

        elif hasattr(self, name):
            return getattr(self, name)

        raise AttributeError('no attribute exists "%s"' % name)

    def __setattr__(self, name, value):
        if name in ['_attributes', '_changed', '_widget', '_metadata']:
            super(Node, self).__setattr__(name, value)

        elif name in self._attributes:            
            attribute = self._attributes.get(name)

            if value != attribute.value:
                attribute.value = value
                self.nodeAttributeUpdated(self.name, name, value)
        else:
            if name == 'name':
                self.nodeNameChanged(self, value)
                if hasattr(self.nodeNameChanged, 'new_name'):
                    if getattr(self.nodeNameChanged.new_name):
                        value = self.nodeNameChanged.new_name
                        del self.nodeNameChanged.new_name

            elif name == 'pos':
                self.nodePositionChanged(self, value)

            else:
                self.nodeAttributeUpdated(self, name, value)

            super(Node, self).__setattr__(name, value)

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in self.REQUIRED:
            if hasattr(self, attr):
                data[attr] = getattr(self, attr)
        data.update(**self._attributes)
        return data

    def connect_widget(self, widget):
        """
        Connect a widget to the dag.

        :param SceneGraph.ui.NodeWidget widget: widget object.
        """
        if not self._widget:
            self._widget = widget
            return True
        return False

    @property
    def metadata(self):
        """
        Output metadata object.
        """
        return self._metadata

    @property 
    def template(self):
        print json.dumps(self._metadata._template_data, indent=5)

    @property
    def graph(self):
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value
        return self.graph

    @property
    def expanded(self):
        return True

    def evaluate(self):
        """
        Evalutate the node.
        """
        return True 

    #- Virtual ----
    @property
    def height(self):
        """
        Returns the base height of the node.

        :returns: total height of the node.
        :rtype: float
        """
        return self.base_height

    @height.setter
    def height(self, value):
        """
        Set the base height value.

        :param float value: base height.
        """
        self.base_height=value

    #- Attributes ----
    def attributes(self, *args):
        """
        Returns a dictionary of connections attributes.

        :returns: dictionary of {connection name : Attribute } 
        :rtype: dict
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

        :param str name: name of attribute.
        
        :returns: named attribute
        :rtype: Attribute
        """
        if name not in self._attributes:
            self.add_attr(name)
        return self._attributes.get(name)

    def rename_attr(self, name, new_name):
        """
        Rename an attribute.

        :param str name: name of attribute.
        :param str new_name: new name.
        """
        if name not in self._attributes:
            raise AttributeError(name)

        if hasattr(self, new_name):
            raise AttributeError('attribute "%s" already exists.' % new_name)

        attr = self._attributes.pop(name)
        attr.name = new_name
        self._attributes.update({attr.name:attr})

    #- Plugins/Metadata ----
    @property
    def plugin_file(self):
        """
        Returns the plugin file associated with this node type.

        :returns: plugin filename.
        :rtype: str
        """
        import inspect
        src_file = inspect.getfile(self.__class__)
        if os.path.exists(src_file.rstrip('c')):
            plugin_file = src_file.rstrip('c')
        return plugin_file
    
    @property
    def is_builtin(self):
        """
        Returns true if the node is a member for the is_builtin 
        plugins.

        :returns: plugin is a builtin.
        :rtype: bool
        """
        return SCENEGRAPH_PLUGIN_PATH in self.plugin_file

    def read_metadata(self, verbose=True):
        """
        Initialize node metadata from metadata files on disk.
        Metadata is parsed by looking at the __bases__ of each node
        class (ie: all DagNode subclasses will inherit all of the default
        DagNode attributes).
        """
        import inspect
        from . import metadata
        parser = metadata.MetadataParser()

        node_metadata = dict()

        # query the base classes
        result = [self.__class__,]
        for pc in self.ParentClasses():
            result.append(pc)
        
        sg_core_path = os.path.join(SCENEGRAPH_PATH, 'core', 'nodes.py')

        for cls in reversed(result):
            cname = cls.__name__
            src_file = inspect.getfile(cls)
            py_src = src_file.rstrip('c')

            dirname = os.path.dirname(src_file)
            basename = os.path.splitext(os.path.basename(src_file))[0]
            
            # return the source .py file if it exists
            if os.path.exists(py_src):
                src_file = py_src

            metadata_filename = os.path.join(dirname, '%s.mtd' % basename)

            # default DagNode type is special.
            if py_src == sg_core_path:
                metadata_filename = os.path.join(SCENEGRAPH_METADATA_PATH, 'dagnode.mtd')
            
            if not os.path.exists(metadata_filename):
                log.warning('plugin description file "%s" does not exist.' % metadata_filename)
                continue

            log.debug('reading plugin metadata file: "%s".' % metadata_filename)
            # parse the metadata 
            parsed = parser.parse(metadata_filename)

            for section in parsed:
                if section not in node_metadata:
                    node_metadata[section] = dict()

                attributes = parsed.get(section)
                

                # parse out input/output here?
                for attr in attributes:
                    if attr not in node_metadata[section]:
                        node_metadata.get(section)[attr] = dict()

                    attr_properties = attributes.get(attr)
                    node_metadata.get(section).get(attr).update(attr_properties)

        return node_metadata
    
    def Class(self):
        return self.__class__.__name__

    def dag_types(self):
        return [c.__name__ for c in Node.__subclasses__()]

    def ParentClasses(self, p=None):
        """
        Returns all of this objects' parent classes.

        :param obj p: parent class.

        :returns: list of parent class names.
        :rtype: list
        """
        base_classes = []
        cl = p if p is not None else self.__class__
        for b in cl.__bases__:
            if b.__name__ not in ["object"]:
                base_classes.append(b)
                base_classes.extend(self.ParentClasses(b))
        return base_classes



class DagNode(Node):

    default_color = [172, 172, 172, 255]
    PRIVATE       = ['node_type']
    REQUIRED      = ['name', 'node_type', 'id', 'color', 'docstring', 'width', 
                      'base_height', 'force_expand', 'pos', 'enabled', 'orientation']

    def __init__(self, name=None, **kwargs):
        attributes = kwargs.pop('attributes', {})
        super(DagNode, self).__init__(name=name, **kwargs)

        # attributes
        self.buildAttributes()

        # update attributes (if reading from scene)
        if attributes:
            for attr_name, properties in attributes.iteritems():
                if attr_name in self._attributes:
                    self._attributes.get(attr_name).update(**properties)
                else:
                    self.add_attr(attr_name, **properties)

    #- Transform ----
    @property
    def expanded(self):
        if self.force_expand:
            return True
        height = max(len(self.inputs), len(self.outputs))
        return height > 1

    def evaluate(self):
        """
        Evalutate the node.
        """
        return True 

    @property
    def height(self):
        """
        Returns the height of the node (height is determined 
        as base height * max number of connectable attributes)

        :returns: total height of the node.
        :rtype: float
        """
        btm_buffer = 0
        max_conn = max(len(self.inputs), len(self.outputs))
        height = max_conn if max_conn else 1
        if height > 1 or self.force_expand:
            height+=1
            btm_buffer = self.base_height/2
        return (height * self.base_height) + btm_buffer

    #- Connections ----

    def buildAttributes(self, verbose=False):
        """
        Parse and build attributes from the Metadata object.
        """
        if verbose:
            print '\n# %s:"%s":' % (self.Class(), self.name)

        for section in self._metadata.data:
            if verbose:
                print '   Section: "%s":' % ( section)

            attributes = self._metadata.data.get(section)

            for attr_name in attributes:                
                # parse connections
                properties = attributes.get(attr_name)
                attr_label = 'Attribute'

                is_connection = False
                conn_type = None
                required  = False
                attr_type = None

                #print 'buildAttributes: properties:  ', properties.keys()

                if 'connectable' in properties:
                    if 'connection_type' in properties:
                        if properties.get('connectable'):
                            is_connection = True
                            conn_type = properties.get('connection_type')
                            #print '  -> connection "%s" type: %s' % (attr_name, conn_type)
                            if conn_type == 'input':
                                attr_label = "Input"

                            if conn_type == 'output':
                                attr_label = "Output"


                # parse defaults (type, value)
                if 'default' in properties:                    
                    defaults = properties.get('default')
                    attr_type = defaults.get('type')

                # parse required
                if 'required' in properties:
                    required = properties.get('required', False)

                if required:
                    attr_label = '*%s' % attr_label

                if verbose:
                    print '      "%s: %s"' % (attr_label, attr_name)
                    print '       "attr_type": "%s"' % attr_type

                # build connections
                if is_connection:                    
                    attr_node = self.map(attr_name, properties, connection_type=conn_type)
                    if not attr_node:
                        if verbose:
                            print 'no node...'
                        continue

                # parse properties of attribute/connection
                # MAPPING:
                # name    -> name
                # type    -> attr_type (lower)
                # default -> default_value
                # label   -> label
                mapping = dict()
                for pname in properties:
                    if verbose:
                        print '        "%s:"' % pname
                    pvalue = properties.get(pname)

                    if not util.is_dict(pvalue):
                        #print '        bool attribute: "%s.%s"' % (attr_name, pname)
                        continue 

                    for pattr in pvalue:
                        pval = pvalue.get(pattr)
                        if verbose:
                            if pval:
                                print '          "%s": %s' % ( pattr, pval)

            if verbose:
                print '\n'

    def map(self, name, properties, connection_type='input', verbose=False):
        """
        Maps data dictionary to an Attribute.

        :param str name: attribute name.
        :param dict properties: attribute dictionary.
        :param str connection_type: connection type (input or output).

        :returns: Attribute object.
        :rtype: :py:class:`SceneGraph.core.Attribute`
        """
        # connection properties
        max_connections = properties.pop('max_connections', 1) 

        pdict = dict()
        # attribute properties (ie 'label', 'desc', 'connection_type')
        for property_name in properties:

            pattrs = properties.get(property_name)
            if not util.is_dict(pattrs):
                continue

            property_value = pattrs.get('value')
            property_type  = pattrs.get('type')

            attr_type      = None

            if property_value:
                if type(property_value) in [str, unicode]:
                    if property_type.isupper():
                        if property_type not in PROPERTY_TYPES.get('data_types'): 
                                attr_type = property_type.lower()
                        else:
                            # data type (ie 'FILE')
                            attr_type = property_type.lower()

            # {'label': 'Name'}
            pdict[property_name] = property_value
            pdict['attr_type'] = attr_type

        #print '%s attrs: ' % name, pdict
        return self.add_attr(name, connectable=True, connection_type=connection_type, max_connections=max_connections, user=False, **pdict)


    @property
    def connections(self):
        """
        Returns a list of connections (input & output)

        returns:
            (list) - list of connection names.
        """
        conn_names = []
        for name in self._attributes:
            if self._attributes.get(name).connectable:
                conn_names.append(name)
        return conn_names

    @property
    def inputs(self):
        """
        Returns a list of input connection names.

        :returns: list of input connection names.
        :rtype: list
        """
        connections = []
        for name in self._attributes:
            data = self._attributes.get(name)
            #if data.get('connectable') and data.get('connection_type') == 'output':
            if data.connectable and data.connection_type == 'input':
                connections.append(name)
        return connections

    @property
    def outputs(self):
        """
        Returns a list of output connection names.

        :returns: list of output connection names.
        :rtype: list
        """
        connections = []
        for name in self._attributes:
            data = self._attributes.get(name)
            #if data.get('connectable') and data.get('connection_type') == 'output':
            if data.connectable and data.connection_type == 'output':
                connections.append(name)
        return connections

    def get_input(self, name='input'):
        """
        Return a named node input.

        :param str name: name of input.

        :returns: connection node.
        :rtype: Connection
        """
        if not name in self._attributes:
            return

        data = self._attributes.get(name)
        if data.connectable and data.connection_type == 'input':
            return self._attributes.get(name)
        return

    def get_output(self, name='output'):
        """
        Return a named node output.

        :param str name: name of input.

        :returns: connection node.
        :rtype: Connection
        """
        if not name in self._attributes:
            return

        data = self._attributes.get(name)
        if data.connectable and data.connection_type == 'output':
            return self._attributes.get(name)
        return

    def is_connected(self, name):
        """
        Returns true if the named connection has 
        a connection.

        :param str name: name of connection to query.

        :returns: connection status.
        :rtype: bool
        """
        conn = self.get_connection(name)
        if not conn:
            return False
        return not conn.connectable

    def input_connections(self):
        """
        Returns a list of connected DagNodes.

        :returns: list of DagNode objects.
        :rtype: list
        """
        connected_nodes = []
        for edge in self.graph.network.edges(data=True):
            # edge = (id, id, {atttributes})
            srcid, destid, attrs = edge
            if destid == self.id:
                if srcid in self.graph.dagnodes:
                    connected_nodes.append(self.graph.dagnodes.get(srcid))
        return connected_nodes

    def output_connections(self):
        """
        Returns a list of connected DagNodes.

        :returns: list of DagNode objects.
        :rtype: list
        """
        connected_nodes = []
        for edge in self.graph.network.edges(data=True):
            # edge = (id, id, {atttributes})
            srcid, destid, attrs = edge
            if srcid == self.id:
                if destid in self.graph.dagnodes:
                    connected_nodes.append(self.graph.dagnodes.get(destid))
        return connected_nodes

    @property
    def is_input_connection(self):
        """
        Returns true if the node is an input connection.

        :returns: node has input connections.
        :rtype: bool
        """
        return bool(self.output_connections())
 
    @property
    def is_output_connection(self):
        """
        Returns true if the node is an output connection.

        :returns: node has output connections.
        :rtype: bool
        """
        return bool(self.input_connections())   

    def get_connection(self, name):
        """
        Returns a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (Attribute) - connection object.
        """
        conn = None
        if name not in self._attributes:
            return 

        data = self._attributes.get(name)
        if data.connectable:
            return data
        return

    def rename_connection(self, old, new):
        """
        Rename a connection.

        params:
            old (str) - old connection name.
            new (new) - new connection name.

        returns:
            (bool) - rename was successful.
        """
        conn = self.get_connection(old)
        if conn:
            conn.name = new
            return True
        return False

    def remove_connection(self, name):
        """
        Remove a named connection (input or output).

        params:
            name (str) - name of connection to query.

        returns:
            (bool) - connection was removed.
        """
        conn = self.get_connection(name)
        if conn:
            self._attributes.pop(name)
            del conn 
            return True 
        return False


#- Builtins ----

class DefaultNode(DagNode):

    node_type     = 'default'
    default_name  = 'default'
    default_color = [172, 172, 172, 255]    

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)


class DotNode(DagNode):

    default_name  = 'dot'
    default_color = [172, 172, 172, 255]
    node_type     = 'dot'

    def __init__(self, name=None, **kwargs):
        DagNode.__init__(self, name, **kwargs)

        self.radius             = 8.0
        self.orientation        = 'dot'
        self.force_expand       = False

        self.add_attr('input', connectable=True, connection_type='input', attr_type='node')

    @property
    def base_height(self):
        return self.radius
    
    @base_height.setter
    def base_height(self, value):
        """
        Set the base width value.

        params:
            value (float) - radius.
        """
        self.radius=value

    @property
    def width(self):
        return self.radius
    
    @width.setter
    def width(self, value):
        """
        Set the base width value.

        params:
            value (float) - radius.
        """
        self.radius=value

    @property
    def height(self):
        return self.radius
    
    @height.setter
    def height(self, value):
        """
        Set the radius value.

        params:
            value (float) - radius.
        """
        self.radius=value


class NoteNode(Node):

    node_type     = 'note'
    default_name  = 'note'
    default_color = [255, 239, 62, 255]    

    def __init__(self, name=None, **kwargs):
        Node.__init__(self, name, **kwargs)

        self.corner_loc     = 'top'   
        self.base_height    = 75
        self.font_size      = 6
        self.show_name      = kwargs.get('show_name', False)
        self.doc_text       = kwargs.get('doc_text', "Sample note text.")        

    @property
    def data(self):
        """
        Output data for writing.
        """
        data = dict()
        for attr in self.REQUIRED:
            if hasattr(self, attr):
                data[attr] = getattr(self, attr)
        data.update(doc_text=self.doc_text, corner_loc=self.corner_loc, font_size=self.font_size, show_name=self.show_name)
        return data



#- Metadata -----

class Metadata(object):

    def __init__(self, parent=None, **kwargs):

        self._parent         = parent
        self._data           = dict()
        self._default_xform  = "Node Transform"
        self._default_attrs  = "Node Attributes" 
        self._template_data  = dict()               # dictionary to hold parsed data

        self._data.update(**kwargs)

    def __str__(self):
        return json.dumps(self.data, default=lambda obj: obj.data, indent=4)

    def __repr__(self):
        pc = self._parent.ParentClasses()
        parents = [x.__name__ for x in pc]
        parents.append(self._parent.Class())
        return 'Metadata: [%s]' % ', '.join(parents)

    def update(self, data):
        """
        Update the data dictionary.

        * todo: can't pass as **kwargs else we lose the order (why is that?)
        """
        if data:
            self._template_data = data
            for k, v in data.iteritems():
                if k in self._data:
                    self._data.get(k).update(**v)
                else:
                    self._data.update({k:v})

    @property
    def data(self):
        return self._data

    def parentItem(self):
        """
        Returns the parent DagNode.

        returns:
            (DagNode) - parent DagNode.
        """
        return self._parent

    def clear(self):
        """
        Clears the parsed metadata.
        """
        self._data = dict()

    def sections(self):
        """
        Returns the metadata "sections" (top-level groups).

        returns:
            (list) - list of metadata group sections.
        """
        return self._data.keys()

    def attributes(self, section):
        """
        Returns the metadata attributes in a given section.

        returns:
            (list) - list of metadata attribute names.
        """
        if section in self.sections():
            return self._data.get(section).keys()
        return []

    def properties(self, section, attribute):
        """
        Return properties for a given section/attribute.

        params:
            section   (str)  - section name.
            attribute (str)  - attribute name.

        returns:
            (list) - list of properties.
        """
        if self.getAttr(section, attribute):
            return self.getAttr(section, attribute).keys()
        return []

    def getAttr(self, section, attribute):
        """
        Returns a metadata attribute.

        returns:
            (dict) - attribute dictionary.
        """
        if attribute in self.attributes(section):
            return self._data.get(section).get(attribute)
        return dict()

    def property(self, section, attribute, property_name):
        return self._data.get(section).get(attribute).get(property_name, None)

    def defaults(self):
        """
        Returns default node attributes.

        returns:
            (dict) - attributes dictionary.
        """
        if self._default_attrs is None:
            return dict()

        if self._default_attrs in self._data.keys():
            return self._data.get(self._default_attrs)
        return dict()

    def transformAttrs(self):
        """
        Returns default transform attributes.

        returns:
            (dict) - attributes dictionary.
        """
        if self._default_xform is None:
            return {}
        if self._default_xform in self._data.keys():
            return self._data.get(self._default_xform)
        return dict()

    def get_connection(self, name):
        return dict()

    def input_connections(self):
        """
        Parse the metadata and return input connections.

        returns:
            (list) - list of connection dictionaries.
                     * todo: should we return an attribute object here?
        """
        connections = []
        for section in self.sections():
            for attribute in self.attributes(section):
                attr_data = self.getAttr(section, attribute)
                print '"%s"' % attribute, attr_data
                if 'connection_type' in attr_data:
                    connectable = attr_data.get('connectable')
                    conn_type = attr_data.get('connection_type')

                    if conn_type == 'INPUT':
                        if connectable:
                            #connections.append({attribute:{'type':conn_type}})
                            connections.append({attribute:attr_data})
        return connections

    def output_connections(self):
        """
        Parse the metadata and return output connections.

        returns:
            (list) - list of connection dictionaries.
                     * todo: should we return an attribute object here?
        """
        connections = []
        for section in self.sections():
            for attribute in self.attributes(section):
                attr_data = self.getAttr(section, attribute)

                if 'connection_type' in attr_data:
                    connectable = attr_data.get('connectable')
                    conn_type = attr_data.get('connection_type')
                    
                    if conn_type == 'OUTPUT':
                        if connectable:
                            #connections.append({attribute:{'type':conn_type}})
                            connections.append({attribute:attr_data})
        return connections
