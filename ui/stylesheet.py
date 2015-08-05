#!/usr/bin/env python
import os
import re
import sys
from collections import OrderedDict as dict
from string import Template
from PySide import QtCore, QtGui
import simplejson as json

from SceneGraph.core import log
from SceneGraph import options
reload(options)


log.setLevel('INFO')


regex = dict(
    style_name = re.compile(r"@STYLENAME\s?=\s?(?P<style>\w+)"),
    property = re.compile(r"\@(?P<attr>[\.\w\-]+):?\s?(?P<class>[\.\w\-]+)?:?\s?(?P<subclass>[\.\w\-]+)?\s?=\s?(?P<value>[\.\w\-\s\#]+)"),
    value = re.compile(r"@(?P<value>[\.\w\-]+)"),
    )


class StylesheetManager(object):

    def __init__(self, parent=None):

        self._ui            = parent                    # parent UI

        self._font_db       = QtGui.QFontDatabase()
        self._config_paths  = ()
        self._config_files  = dict()

        self._qss_paths     = ()
        self._qss_files     = dict()

    def run(self, paths=[], style='default'):
        """
        Read files from the 
        """
        self._config_paths = self._get_config_paths(paths=paths)
        self._config_files = self._get_config_files(self._config_paths)

        self._qss_paths = self._get_qss_paths(paths=paths)
        self._qss_files = self._get_qss_files(self._qss_paths)

        style = StyleParser(self, style=style)
        style.run()

        if self._ui is not None:
            if self._ui.use_stylesheet:
                style_data = style.data
                self._ui.setStyleSheet(style_data)
                attr_editor = self._ui.getAttributeEditorWidget()
                if attr_editor:
                    attr_editor.setStyleSheet(style_data)

    @property
    def config_names(self):
        return self._config_files.keys()    

    @property
    def config_files(self):
        return self._config_files.values() 

    @property
    def qss_names(self):
        return self._qss_files.keys()    

    @property
    def qss_files(self):
        return self._qss_files.values() 

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
                        log.warning('config path "%s" does not exist, skipping.' % path)
                        continue
                    log.info('reading config external path: "%s".' % path)
                    cfg_paths = cfg_paths + (path,)

        return cfg_paths

    def _get_qss_paths(self, paths=[]):
        """
        Read stylesheets from config paths.

        params:
            paths (list) - list of paths to add to the scan.

        returns:
            (tuple) - array of search paths.
        """
        if paths and type(paths) in [str, unicode]:
            paths = [paths,]

        qss_paths = ()
        qss_paths = qss_paths + (options.SCENEGRAPH_STYLESHEET_PATH,)

        # read external paths
        if 'SCENEGRAPH_STYLESHEET_PATH' in os.environ:
            qpaths = os.getenv('SCENEGRAPH_STYLESHEET_PATH').split(':')
            if paths:
                for p in paths:
                    if p not in qpaths:
                        qpaths.append(p)

            for path in qpaths:
                if path not in qss_paths:
                    if not os.path.exists(path):
                        log.warning('stylesheet path "%s" does not exist, skipping.' % path)
                        continue
                    log.info('reading external stylesheet path: "%s".' % path)
                    qss_paths = qss_paths + (path,)

        return qss_paths

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
                if fext.lower() in ['.ini', '.cfg']:
                    cfg_file = os.path.join(path, fn)
                    if cfg_file not in cfg_files.values():
                        log.info('adding config "%s" from "%s".' % (bn, cfg_file))
                        cfg_files[bn] = cfg_file
        return cfg_files

    def _get_qss_files(self, paths=[]):
        """
        Get qss files.

        params:
            paths (list) - list of paths to add to the scan.

        returns:
            (dict) - dictionary of stylesheet names/filenames.
        """
        qss_files = dict()
        if not paths:
            return []

        for path in paths:
            for fn in os.listdir(path):
                bn, fext = os.path.splitext(fn)
                if fext.lower() in ['.qss', '.css']:
                    qss_file = os.path.join(path, fn)
                    if qss_file not in qss_files.values():
                        style_name = self._parse_stylesheet_name(qss_file)
                        if style_name is None:
                            log.warning('cannot parse style name from "%s".' % qss_file)
                            style_name = 'no-style'

                        log.info('adding stylesheet "%s" from "%s".' % (style_name, qss_file))

                        if style_name not in qss_files:
                            qss_files[style_name] = qss_file
        return qss_files

    def _parse_stylesheet_name(self, filename):
        """
        Parse the stylesheet name from a file.

        params:
            filename (str) - filename to read.
        """
        style_name = None
        if os.path.exists(filename):
            for line in open(filename,'r'):
                line = line.rstrip('\n')
                rline = line.lstrip(' ')
                rline = rline.rstrip()
                smatch = re.search(regex.get('style_name'), rline)
                if smatch:
                    style_name = smatch.group('style')
                    break
        return style_name

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

    #- Fonts -----

    def buildUIFontList(self, valid=[]):
        """
        Returns a list of monospace fonts.
        """
        if not valid:
            valid = options.SCENEGRAPH_VALID_FONTS.get('ui')

        families = []
        for font_name in self._font_db.families():
            if not self._font_db.isFixedPitch(font_name):
                if font_name in valid:
                    families.append(font_name)
        return families

    def buildMonospaceFontList(self, valid=[]):
        """
        Returns a list of monospace fonts.
        """
        if not valid:
            valid = options.SCENEGRAPH_VALID_FONTS.get('mono')

        families = []
        for font_name in self._font_db.families():
            if self._font_db.isFixedPitch(font_name):
                if font_name in valid:
                    families.append(font_name)
        return families


class StyleParser(object):

    def __init__(self, parent, style=None):

        self.manager        = parent
        self.style          = style

        self._stylesheet    = None
        self._config        = None

        self._data          = dict()

    @property
    def data(self):
        import copy
        data = dict()
        style_data = copy.deepcopy(self._data)
        for k, v in style_data.pop('defaults', {}).iteritems():
            data['%s' % k] = v

        for class_name in style_data.keys():
            class_attrs = style_data.get(class_name)
            for attr, value in class_attrs.iteritems():
                cname = '%s-%s' % (attr, class_name)
                data[cname] = value

        ff = open(self._stylesheet, 'r')
        ss_lines = ""
        for line in ff.readlines():
            if line:
                if '@' in line:
                    if not '@STYLENAME' in line:
                        smatch = re.search(regex.get('value'), line)
                        if smatch:
                            value = smatch.group('value')
                            if value in data:
                                new_value = data.get(value)
                                ss_lines += '%s' % re.sub('@%s' % value, new_value, line)
                                continue

                ss_lines += '%s' % line
        return ss_lines

    def run(self, style='default'):
        stylesheet = self.manager._qss_files.get(style, None)
        config     = self.manager._config_files.get(style, None)

        if stylesheet and os.path.exists(stylesheet):
            self._stylesheet = stylesheet

        if config and os.path.exists(config):
            self._config = config

        if self._stylesheet is not None and self._config is not None:
            self._data = self._parse_config(self._config)

    def _parse_config(self, config):
        """
        Parse a config file.
        """
        data = dict()
        data.update(defaults=dict())

        with open(config) as f:
            for line in f.readlines():
                line = line.rstrip('\n')
                rline = line.lstrip(' ')
                rline = rline.rstrip()
                smatch = re.search(regex.get('property'), rline)
                if smatch:
                    match_data = smatch.groupdict()
                    class_name = 'defaults'
                    if 'class' in match_data:
                        cname = match_data.pop('class')
                        if cname:
                            class_name = cname

                    if class_name not in data:
                        data[class_name] = dict()

                    attr_name = match_data.get('attr')
                    attr_val = match_data.get('value')
                    subclass = match_data.get('subclass')

                    if attr_val:
                        data[class_name][attr_name] = attr_val
                        if subclass:
                            data[class_name][attr_name]['subclass'] = subclass
        return data

    def apply(self, stylesheet=None, style=None):
        """
        * Not used.        
        """
        ssf = QtCore.QFile(default_stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self._ui.setStyleSheet(str(ssf.readAll()))
        attr_editor = self._ui.getAttributeEditorWidget()
        if attr_editor:
            attr_editor.setStyleSheet(str(ssf.readAll()))
        ssf.close()
