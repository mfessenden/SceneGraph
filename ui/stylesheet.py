#!/usr/bin/env python
import os
import re
import sys
from collections import OrderedDict as dict
from string import Template


from SceneGraph import options
reload(options)


regex = dict(
    property = re.compile(r"\@(?P<attr>[\.\w\-]+):(?P<class>[\.\w\-]+):?(?P<subclass>[\.\w\-]+)?\s?=\s?(?P<value>[\.\w\-]+)"),
    )


class StylesheetManager(object):

    def __init__(self):

        self._config_paths = ()
        self._config_files = dict()

    def run(self, paths=[]):
        """
        Read files from the 
        """
        self._config_paths = self._get_config_paths(paths=paths)
        self._config_files = self._get_config_files(self._config_paths)

    @property
    def config_names(self):
        return self._config_files.keys()    

    @property
    def config_files(self):
        return self._config_files.values() 

    def _get_config_paths(self, paths=[]):
        """
        Read configs from config paths.

        params:
            paths (list) - list of paths to add to the scan.

        returns:
            (tuple) - array of search paths.
        """
        if paths and type(paths) in [str, unicode]:
            paths = [paths,]

        cfg_paths = ()
        cfg_paths = cfg_paths + (options.SCENEGRAPH_CONFIG_PATH,)

        # read external paths
        if 'SCENEGRAPH_CONFIG_PATH' in os.environ:
            spaths = os.getenv('SCENEGRAPH_CONFIG_PATH').split(':')
            if paths:
                for p in paths:
                    if p not in spaths:
                        spaths.append(p)

            for path in spaths:
                if path not in cfg_paths:
                    if not os.path.exists(path):
                        print '# Warning: path "%s" does not exist, skipping.' % path
                        continue
                    print '# Info: reading external path: "%s".' % path
                    cfg_paths = cfg_paths + (path,)

        return cfg_paths

    def _get_config_files(self, paths=[]):
        """
        Get config files.

        params:
            paths (list) - list of paths to add to the scan.

        returns:
            (dict) - dictionary of config names/filenames.
        """
        cfg_files = dict()
        if not paths:
            return []

        for path in paths:
            for fn in os.listdir(path):
                bn, fext = os.path.splitext(fn)
                if fext.lower() == '.ini':
                    cfg_file = os.path.join(path, fn)
                    if cfg_file not in cfg_files.values():
                        print '# Info: adding config "%s" from "%s".' % (bn, cfg_file)
                        cfg_files[bn] = cfg_file
        return cfg_files

    def add_config(self, filename, name=None):
        """
        Add a config to the config files attribute.

        params:
            filename (str) - filename to read.
            name     (str) - name of the config.
        """
        if filename in self._config_files.values():
            for cfg_name, cfg_file in self._config_files.iteritems():
                if cfg_file == filename:
                    if name != cfg_name:
                        self._config_files.pop(cfg_name)
        self._config_files[name] = filename

