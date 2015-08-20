#!/usr/bin/env python
import os
import re
import sys
import pkgutil
import inspect
import time
import simplejson as json

from SceneGraph.core import log
from SceneGraph.options import SCENEGRAPH_PATH, SCENEGRAPH_CORE, SCENEGRAPH_PLUGIN_PATH, SCENEGRAPH_ICON_PATH, SCENEGRAPH_METADATA_PATH



class PluginManager(object):
    """
    Class to manage loading and unloading of plugins.

    Paths will be scanned automatically. To override external plugin paths, 
    pass the paths you want to use with the 'paths' argument, else the 
    PluginManager will scan for directories on the PYTHONPATH.

    run with PluginManager.load_plugins()
    """
    def __init__(self, paths=[], **kwargs):

        # storage for plugin data
        self._node_data              = dict()    

        # plugin paths & module data
        self._core_plugin_path       = SCENEGRAPH_CORE
        self._builtin_plugin_path    = SCENEGRAPH_PLUGIN_PATH
        self._default_plugin_path    = SCENEGRAPH_PLUGIN_PATH
        self._default_modules        = get_modules(self._default_plugin_path)

        # external paths & module
        self._external_plugin_paths  = paths
        self._external_modules       = []

        # load core nodes
        self.load_core()

        # auto-load default plugins
        self.load_plugins(self._default_plugin_path)
        self.load_widgets(self._default_plugin_path)

        # setup external paths
        if not self._external_plugin_paths:
            self._external_plugin_paths = self.initializeExternalPaths()

    def initializeExternalPaths(self):
        """
        Builds a list of external plugins paths. 

        :returns: plugin scan paths.
        :rtype: tuple 
        """
        result = ()
        ext_pp = os.getenv('SCENEGRAPH_PLUGIN_PATH')
        if ext_pp:
            for path in ext_pp.split(':'):
                result = result + (path,)
        return list(result)

    def plugin_paths(self):
        """
        Returns a list of all plugin paths, starting with builtin.

        :returns: plugin scan paths.
        :rtype: tuple 
        """
        result = (self._default_plugin_path,)
        if self._external_plugin_paths:
            for path in self._external_plugin_paths:
                result = result + (path,)
        return result

    @property
    def globals(self):
        return globals()

    def query(self):
        """
        Query globals for loaded plugins.

        :returns: dictionay of class name, filename.
        :rtype: dict 
        """
        plugin_data = dict()
        for k, v in globals().iteritems():
            if inspect.isclass(v):
                
                filename = inspect.getsourcefile(v)
                module = inspect.getmodule(v)

                print 'class: ', v
                plugin_name = None
                widget_name = None

                if plugin_name or widget_name:
                    plugin_data[k] = dict()
                    plugin_data.get(k).update(filename=filename)

                    if plugin_name:
                        plugin_data.get(k).update(type='plugin')
                        mtd_file = self._node_data.get(plugin_name).get('metadata', None)
                        if mtd_file:
                            plugin_data.get(k).update(metadata=mtd_file)
                    if widget_name:
                        plugin_data.get(k).update(type='widget')

        return plugin_data

    def pprint(self):
        print json.dumps(self.query(), indent=5, sort_keys=True)

    def setLogLevel(self, level):
        """
         * debugging.
        """
        log.level = level

    #- Attributes ----
    def node_types(self, plugins=[], disabled=False):
        """
        Return a list of loaded node types.

        :param list plugins: plugins to filter.
        :param bool disabled: return disabled plugins.

        :returns: list of node types (strings).
        :rtype: list
        """
        return self.get_plugins(plugins=plugins, disabled=disabled) 

    @property
    def node_categories(self):
        """
        Returns a list of node categories.

        :returns: node categories.
        :rtype: list
        """
        node_categories = []

        for node_type, node_attrs in data.iteritems():
            category = node_attrs.get('category', None)
            
            if category and category not in node_categories:
                node_categories.append(category)

        return sorted(node_categories)   

    @property
    def node_classes(self):
        """
        Returns a list of node classes.

        :returns: node classes.
        :rtype: list
        """
        node_classes = []
        for node_type, node_attrs in data.iteritems():
            node_class = node_attrs.get('class', None)
            
            if node_class and node_class not in node_classes:
                node_classes.append(node_class)
        return sorted(node_classes)   

    @property
    def default_plugin_path(self):
        """
        Return the default plugin path.

        :returns: current default plugin path.
        :rtype: str
        """
        return self._default_plugin_path

    @default_plugin_path.setter
    def default_plugin_path(self, path):
        """
        Set the default plugin path.

        :param str path: directory path.

        :returns: current default plugin path.
        :rtype: str
        """
        if path != self._default_plugin_path:
            self.flush()
            self._default_plugin_path = path
        return self.default_plugin_path

    @property
    def default_modules(self):
        """
        Returns the default plugin modules.

        :returns: list of default plugin module names.
        :rtype: list
        """
        return self._default_modules

    @property
    def external_plugin_paths(self):
        """
        Returns a list of external plugin paths.

        :returns: list of external plugin paths.
        :rtype: list
        """
        return self._external_plugin_paths    

    @property
    def external_modules(self):
        """
        Returns a list of external plugin module names.

        :returns: list of external plugin module names.
        :rtype: list
        """
        return self._external_modules  

    #- Loading ----

    def load_core(self, plugins=[]):
        """
        Load core node types.

        :param list plugins: plugin names to filter.
        """
        log.info('loading plugins...')

        core_path = SCENEGRAPH_CORE
        widget_path = os.path.join(SCENEGRAPH_PATH, 'ui')

        builtins = self._load_core(core_path, plugins=plugins)
        #print '# DEBUG: core nodes loaded: ', builtins
        self.load_widgets(widget_path, plugins=builtins)

    def _load_core(self, path, plugins=[]):
        """
        Dynamically load all submodules/asset classes
        in this package.

        :param str path: path to scan.
        :param list plugins: plugin names to filter.

        :returns: list of loaded plugin names.
        :rtype: list
        """
        imported = []
        fexpr = re.compile(r"(?P<basename>.+?)(?P<fext>\.[^.]*$|$)")

        for loader, mod_name, is_pkg in pkgutil.walk_packages([path]):
            module = loader.find_module(mod_name).load_module(mod_name)

            modfn = module.__file__
            src_file = None
            md_file  = None
            fnmatch = re.search(fexpr, modfn)

            if fnmatch:
                bn = fnmatch.group('basename')
                bfn = os.path.basename(bn)
                src_file = os.path.join('%s.py' % bn)
            
            # filter DagNode types
            for cname, obj in inspect.getmembers(module, inspect.isclass):

                # plugins need to have two attributes: node_type & node_class
                node_type = None
                node_class = None
                node_category = None

                if not hasattr(obj, 'node_type') or not hasattr(obj, 'node_class'):
                    # keep moving
                    continue

                node_type = getattr(obj, 'node_type')
                node_class = getattr(obj, 'node_class')

                # for now, "node_category" is not required
                if getattr(obj, 'node_category'):
                    node_category = obj.node_category


                if cname not in globals():
                    globals()[cname] = obj

                imported.append(node_type)
                # raw_data = pkgutil.get_data('mod.components', 'data.txt')            
                self._node_data.update({node_type:{'dagnode':globals()[cname], 'metadata':None, 'source':None, 'enabled':True, 'category':node_category, 'class':node_class}})

                # add source and metadata files
                if os.path.exists(src_file):
                    self._node_data.get(node_type).update(source=src_file)

                #if os.path.exists(md_file):
                md_file = os.path.join(SCENEGRAPH_METADATA_PATH, '%s.mtd' % node_type)
                if os.path.exists(md_file):
                    self._node_data.get(node_type).update(metadata=md_file)

        return sorted(list(set(imported)))

    def load_plugins(self, path=None, plugins=[]):
        """
        Load built-in and external asset types

         .. todo::: load the external plugins as well.

        :param str path: path to scan.
        :param list plugins: plugin names to filter.
        """
        log.info('loading plugins...')

        if path is None:
            path = self.default_plugin_path

        builtins = self._load_builtins(path, plugins=plugins)

    def _load_builtins(self, path, plugins=[]):
        """
        Dynamically load all submodules/asset classes
        in this package.

        :param str path: path to scan.
        :param list plugins: plugin names to filter.

        :returns: list of loaded plugin names.
        :rtype: list
        """
        imported = []
        fexpr = re.compile(r"(?P<basename>.+?)(?P<fext>\.[^.]*$|$)")

        for loader, mod_name, is_pkg in pkgutil.walk_packages([path]):
            module = loader.find_module(mod_name).load_module(mod_name)

            modfn = module.__file__
            src_file = None
            md_file  = None
            
            fnmatch = re.search(fexpr, modfn)
            if fnmatch:
                src_file = '%s.py' % fnmatch.group('basename')
                md_file = '%s.mtd' % fnmatch.group('basename')

            # filter DagNode types
            for cname, obj in inspect.getmembers(module, inspect.isclass):
                
                # plugins need to have two attributes: node_type & node_class
                node_type = None
                node_class = None
                node_category = None

                if not hasattr(obj, 'node_type') or not hasattr(obj, 'node_class'):
                    # keep moving
                    continue

                node_type = getattr(obj, 'node_type')
                node_class = getattr(obj, 'node_class')

                if not plugins or node_type in plugins:

                    # for now, "node_category" is not required
                    if getattr(obj, 'node_category'):
                        node_category = obj.node_category
                        
                    if cname not in globals():
                        globals()[cname] = obj

                    imported.append(node_type)                
                    self._node_data.update({node_type:{'dagnode':globals()[cname], 'metadata':None, 'source':None, 'enabled':True, 'category':node_category, 'class':node_class}})

                    # add source and metadata files
                    if os.path.exists(src_file):
                        self._node_data.get(node_type).update(source=src_file)

                    if os.path.exists(md_file):
                        self._node_data.get(node_type).update(metadata=md_file)

        return sorted(list(set(imported)))

    def load_widgets(self, path=None, plugins=[]):
        """
        Load built-in and external node widgets.

        .. todo:: 
            - load the external plugins as well.

        :param str path: path to scan.
        :param list plugins: plugin names to filter.
        """
        log.info('loading plugin widgets...')

        if path is None:
            path = self.default_plugin_path

        widgets = self._load_widgets(path, plugins=plugins)

        # update the node data attribute with widget classes
        for node_type in widgets:
            
            if node_type in self._node_data:
                #print '# DEBUG: updating node "%s" with widget...' % node_type
                self._node_data.get(node_type).update(widgets.get(node_type))

    def _load_widgets(self, path, plugins=[]):
        """
        Dynamically load all node widgets.

        :param str path: path to scan.
        :param list plugins: plugin names to filter.

        :returns: dictionary of node type, widget.
        :rtype: dict
        """
        imported = dict()
        fexpr = re.compile(r"(?P<basename>.+?)(?P<fext>\.[^.]*$|$)")

        for loader, mod_name, is_pkg in pkgutil.walk_packages([path]):
            module = loader.find_module(mod_name).load_module(mod_name)

            modfn = module.__file__
            src_file = None

            fnmatch = re.search(fexpr, modfn)
            if fnmatch:
                src_file = '%s.py' % fnmatch.group('basename')

            # filter widget types
            for cname, obj in inspect.getmembers(module, inspect.isclass):

                # we need to match the widget_type attribute to 
                # the corresponding node_type value.
                widget_type = None

                if not hasattr(obj, 'widget_type'):
                    # keep moving
                    continue

                widget_type = getattr(obj, 'widget_type')

                if not plugins or widget_type in plugins:
                    if cname not in globals():
                        globals()[cname] = obj

                    imported.update({widget_type:{'widget':globals()[cname]}})

        return imported

    def _get_external_plugin_paths(self, dirname='scenegraph_plugins'):
        """
        Returns a list of paths from sys path.

        :param str dirname: name of an external directory to scan.

        :returns: list of external module paths.
        :rtype: list
        """
        result = []
        for p in sys.path:
            ppath = os.path.join(p, dirname)
            if os.path.exists(ppath):
                if os.path.exists(os.path.join(ppath, '__init__.py')):
                    if ppath not in result:
                        result.append(ppath)
        return result

    @property
    def valid_plugins(self):
        result = []
        for pname in self._node_data:
            pattrs = self._node_data.get(pname)

            enabled = pattrs.get('enabled', False)
            if not enabled:
                continue

            dag = pattrs.get('dagnode', None)
            widget = pattrs.get('widget', None)

            if dag is None or widget is None:
                continue

            if pname not in result:
                result.append(pname)

        return result    

    def get_plugins(self, plugins=[], disabled=False):
        """
        Return filtered plugin data.

        :param list plugins: plugin names to filter.
        :param bool disabled: show disabled plugins.

        :returns: dictionary of plugin data.
        :rtype: dict
        """
        result = dict()
        for plugin in sorted(self._node_data.keys()):
            if not plugins or plugin in plugins:
                plugin_attrs = self._node_data.get(plugin)
                if plugin_attrs.get('enabled', True) or disabled:
                    result[plugin] = plugin_attrs
        return result

    def get_dagnode(self, node_type, **kwargs):
        """
        Return the appropriate dag node type.

        :param str node_type: dag node type to return.

        :returns: dag node subclass.
        :rtype: DagNode
        """
        if node_type not in self._node_data:
            log.error('plugin type "%s" is not loaded.' % node_type)
            return

        dag = self._node_data.get(node_type).get('dagnode')
        # assign the node metadata file
        result = dag(_metadata=self._node_data.get(node_type).get('metadata', None), **kwargs)
        return result

    def get_widget(self, dagnode, **kwargs):
        """
        Return the appropriate node type widget. Returns the default widget
        if one is not defined.

        :param DagNode dagnode: node type.

        :returns: node widget subclass.
        :rtype: NodeWidget
        """
        if dagnode.node_type not in self._node_data:
            log.error('plugin "%s" is not loaded.' % dagnode.node_type)
            return

        if 'widget' not in self._node_data.get(dagnode.node_type):
            log.error('plugin "%s" widget not loaded.' % dagnode.node_type)
            return

        widget = self._node_data.get(dagnode.node_type).get('widget')
        return widget(dagnode)

    def default_name(self, nodetype):
        """
        Return the DagNode's default name.

        :param str nodetype: node type to query.

        :returns: node default name.
        :rtype: str 
        """
        if nodetype in self._node_data:
            cls = self._node_data.get(nodetype).get('dagnode')
            if cls:
                if hasattr(cls, 'default_name'):
                    return cls.default_name
        return

    def metadata_file(self, filename):
        """
        Returns the metadata description associated the given plugin.

        :returns: plugin source file.
        :rtype: str  
        """
        sg_core_path = os.path.join(SCENEGRAPH_PATH, 'core', 'nodes.py')
        if filename == sg_core_path:
            metadata_filename = os.path.join(SCENEGRAPH_METADATA_PATH, 'dagnode.mtd')
        else:
            basename = os.path.splitext(os.path.basename(filename))[0]
            metadata_filename = os.path.join(SCENEGRAPH_PLUGIN_PATH, '%s.mtd' % basename)

        if not os.path.exists(metadata_filename):
            raise OSError('plugin description file "%s" does not exist.' % metadata_filename)
        return metadata_filename

    def enable(self, plugin, enabled=True):
        """
        Enable/disable plugins.
        """
        if not plugin in self._node_data:
            log.error('plugin "%s" not recognized.' % plugin)
            return False

        for plug, plugin_attrs in self._node_data.iteritems():
            if plug == plugin:
                log.info('setting plugin "%s" enabled: %s' % (plugin, str(enabled)))
                self._node_data.get(plugin).update(enabled=enabled)
                return True
        return False

    def flush(self):
        """
        Flush all currently loaded plugins.
        """
        flush = []
        for attr in globals():
            if not attr.startswith('__'):
                obj = globals()[attr]
                if hasattr(obj, 'dag_types'):
                    flush.append(attr)

        if flush:
            for f in flush:
                globals().pop(f)
                log.info('flushing object: "%s"'% f)

        self._node_data = dict()
        self._default_modules = []


#- Utilities ------

def get_modules(path):
    """
    Returns all sub-modules of this package.

    :returns: list of module names in the current package.
    :rtype: list
    """
    mod_names = []
    modules = pkgutil.iter_modules(path=[path])
    for loader, mod_name, ispkg in modules:
        mod_names.append(mod_name)
        log.debug('reading module: "%s"' % mod_name)
    return sorted(mod_names)


def load_class(classpath):
    """
    Dynamically loads a class.

    params:
        classpath (str) - full path of class to import.
                            ie: SceneGraph.core.nodes.DagNode
    returns:
        (obj) - imported class object.
    """
    class_data = classpath.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]
    module = __import__(module_path, globals(), locals(), fromlist=[class_str])
    return getattr(module, class_str)


def parse_module_variable(module, key):
    """
    Parse a named variable from a given module.

    params:
        module (module) - module object.
        key    (str)    - string variable to search for.

    returns:
        (str) - parsed variable value.
    """
    for cname, obj in inspect.getmembers(module):
        if cname==key:
            return obj
    return None
