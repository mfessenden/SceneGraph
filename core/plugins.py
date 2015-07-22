#!/usr/bin/env python
import os
import re
import imp
import sys
import pkgutil
import inspect
import time
import simplejson as json

from SceneGraph.core import log
from SceneGraph.options import SCENEGRAPH_PATH, SCENEGRAPH_PLUGIN_PATH, SCENEGRAPH_ICON_PATH


log.level = 20 # 20 = info, 


class PluginManager(object):
    """
    Class to manage loading and unloading of plugins.

    Paths will be scanned automatically. To override external plugin paths, 
    pass the paths you want to use with the 'paths' argument, else the 
    PluginManager will scan for directories on the PYTHONPATH.

    run with PluginManager.load_plugins()
    """
    def __init__(self, paths=[], **kwargs):
        self._node_data = dict()    

        # plugin paths & module data
        self._default_plugin_path    = SCENEGRAPH_PLUGIN_PATH
        self._default_modules        = get_modules(self._default_plugin_path)

        # external paths & module
        self._external_plugin_paths  = paths
        self._external_modules       = []

        # auto-load default plugins
        self.load_plugins(self._default_plugin_path)
        self.load_widgets(self._default_plugin_path)

        # setup external paths
        if not self._external_plugin_paths:
            self._external_plugin_paths = self.initializeExternalPaths()

    def initializeExternalPaths(self):
        """
        Builds a list of external plugins paths. 

        returns:
            (tuple) - plugin scan paths.
        """
        result = ()
        ext_pp = os.getenv('SCENEGRAPH_PLUGIN_PATH')
        if ext_pp:
            for path in ext_pp.split(':'):
                result = result + (path,)
        return list(result)

    def plugin_paths(self):
        """
        Returns a list of all plugin paths, starting with builting.

        returns:
            (tuple) - plugin scan paths.
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

        returns:
            (dict) - class name, filename
        """
        plugin_data = dict()
        for k, v in globals().iteritems():
            if inspect.isclass(v):
                
                filename = inspect.getsourcefile(v)
                module = inspect.getmodule(v)

                plugin_name = parse_module_variable(module, 'SCENEGRAPH_NODE_TYPE')
                widget_name = parse_module_variable(module, 'SCENEGRAPH_WIDGET_TYPE')

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

        params:
            plugins (list)  - plugins to filter.
            disabled (bool) - show disabled plugins.

        returns:
            (list) - list of node types (strings).
        """
        return self.get_plugins(plugins=plugins, disabled=disabled) 

    @property
    def default_plugin_path(self):
        """
        Return the default plugin path.

        returns:
            (str) - current default plugin path.
        """
        return self._default_plugin_path

    @default_plugin_path.setter
    def default_plugin_path(self, path):
        """
        Set the default plugin path.

        params:
            path (str) - directory path.

        returns:
            (str) - current default plugin path.
        """
        if path != self._default_plugin_path:
            self.flush()
            self._default_plugin_path = path
        return self.default_plugin_path

    @property
    def default_modules(self):
        """
        Returns the default plugin modules.

        returns:
            (list) - list of default plugin module names.
        """
        return self._default_modules

    @property
    def external_plugin_paths(self):
        """
        Returns a list of external plugin paths.

        returns:
            (list) - list of external plugin paths.
        """
        return self._external_plugin_paths    

    @property
    def external_modules(self):
        """
        Returns a list of external plugin module names.

        returns:
            (list) - list of external plugin module names.
        """
        return self._external_modules  

    #- Loading ----

    def load_plugins(self, path=None, plugins=[]):
        """
        Load built-in and external asset types

         *todo: load the external plugins as well.

        params:
            path        (str) - path to scan.
            plugin_name (str) - plugin name to filter.

        """
        log.info('loading plugins...')

        if path is None:
            path = self.default_plugin_path

        builtins = self._load_builtins(path, plugins=plugins)
        #external = _load_external_classes(path, verbose=verbose, asset_name=asset_name)
        #widgets = self._load_widgets(path, plugins=plugins)

    def _load_builtins(self, path, plugins=[]):
        """
        Dynamically load all submodules/asset classes
        in this package.

        params:
            path        (str) - path to scan.
            plugin_name (str) - plugin name to filter.

        returns:
            (list) - list of loaded plugin names.
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

            node_type = parse_module_variable(module, 'SCENEGRAPH_NODE_TYPE')
            
            # filter DagNode types
            for cname, obj in inspect.getmembers(module, inspect.isclass):
                
                if not plugins or cname in plugins:
                    if hasattr(obj, 'node_type'):
                        if getattr(obj, 'node_type') != 'dagnode':
                            #print '# DEBUG: Loading "%s" from plugin "%s"' % (cname, src_file)
                            globals()[cname] = obj
                            imported.append(cname)                
                            self._node_data.update({node_type:{'dagnode':globals()[cname], 'metadata':None, 'source':None, 'enabled':True}})

                            # add source and metadata files
                            if os.path.exists(src_file):
                                self._node_data.get(node_type).update(source=src_file)

                            if os.path.exists(md_file):
                                self._node_data.get(node_type).update(metadata=md_file)

        return sorted(list(set(imported)))

    def load_widgets(self, path=None, plugins=[]):
        """
        Load built-in and external node widgets.

         *todo: load the external plugins as well.

        params:
            path        (str) - path to scan.
            plugin_name (str) - plugin name to filter.

        """
        log.info('loading plugin widgets...')

        if path is None:
            path = self.default_plugin_path

        default_widgets = self._load_widgets(path, plugins=plugins)

        # update the node data attribute with widget classes
        for node_type in default_widgets:
            if node_type in self._node_data:
                self._node_data.get(node_type).update(default_widgets.get(node_type))
        #external_widgets = _load_external_classes(path, verbose=verbose, asset_name=asset_name)

    def _load_widgets(self, path, plugins=[]):
        """
        Dynamically load all node widgets.

        params:
            path        (str) - path to scan.
            plugin_name (str) - plugin name to filter.

        returns:
            (dict) - dictionary of node type, widget.
        """
        imported = dict()
        fexpr = re.compile(r"(?P<basename>.+?)(?P<fext>\.[^.]*$|$)")

        for loader, mod_name, is_pkg in pkgutil.walk_packages([path]):
            module = loader.find_module(mod_name).load_module(mod_name)

            node_type = parse_module_variable(module, 'SCENEGRAPH_WIDGET_TYPE')

            if node_type:
                modfn = module.__file__
                src_file = None

                fnmatch = re.search(fexpr, modfn)
                if fnmatch:
                    src_file = '%s.py' % fnmatch.group('basename')

                # filter DagNode types
                for cname, obj in inspect.getmembers(module, inspect.isclass):
                    if not plugins or cname in plugins:
                        if hasattr(obj, 'ParentClasses'):
                            #if 'NodeWidget' in obj.ParentClasses(obj):
                            globals()[cname] = obj
                            imported.update({node_type:{'widget':globals()[cname]}})              
        return imported

    def _get_external_plugin_paths(self, path='scenegraph_plugins'):
        """
        Returns a list of paths from sys path

        params:
            path        (str) - name of an external directory to scan.

        returns:
            (list) - list of external module paths.
        """
        result = []
        for p in sys.path:
            ad = os.path.join(p, path)
            if os.path.exists(ad):
                if os.path.exists(os.path.join(ad, '__init__.py')):
                    if ad not in result:
                        result.append(ad)
        return result

    def get_plugins(self, plugins=[], disabled=False):
        """
        Return filtered plugin data.

        params:
            plugins (list)  - plugins to filter.
            disabled (bool) - show disabled plugins.

        returns:
            (dict) - dictionary of plugin data.
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

        params:
            node_type (str) - dag node type to return.

        returns:
            (DagNode) - dag node subclass.
        """
        if node_type not in self._node_data:
            log.error('plugin type "%s" is not loaded.' % node_type)
            return

        dag = self._node_data.get(node_type).get('dagnode')

        # assign the node metadata file
        return dag(_metadata=self._node_data.get(node_type).get('metadata', None), **kwargs)

    def get_widget(self, dagnode, **kwargs):
        """
        Return the appropriate node type widget. Returns the default widget
        if one is not defined.

        params:
            dagnode (DagNode) - node type.

        returns:
            (Node) - node widget subclass.
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

        params:
            nodetype (str) - node type to query.

        returns:
            (str) - node default name.
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

        returns:
            (str) - plugin source file.
        """
        sg_core_path = os.path.join(SCENEGRAPH_PATH, 'core', 'nodes.py')
        if filename == sg_core_path:
            metadata_filename = os.path.join(SCENEGRAPH_PLUGIN_PATH, 'dagnode.mtd')
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

    returns:
        (list) - list of module names in the current package.
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
