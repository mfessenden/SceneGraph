# -- coding: utf-8 --
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


regex = dict(
    style_name = re.compile(r"@STYLENAME\s?=\s?(?P<style>\w+)"),
    property = re.compile(r"\@(?P<attr>[\.\w\-]+):?\s?(?P<class>[\.\w\-]+)?:?\s?(?P<subclass>[\.\w\-]+)?\s?=\s?(?P<value>[\.\w\-\s\#]+)"),
    value = re.compile(r"@(?P<value>[\.\w\-]+)"),
    )


class StylesheetManager(object):

    def __init__(self, parent=None, style='default', paths=[]):

        self._ui            = parent                    # parent UI
        self._style         = style                     # style to parse
        self._font_db       = QtGui.QFontDatabase()     # font database
        self._fonts         = dict()                    # dictionary of font types

        self._config_paths  = ()                        # paths for cfg mods
        self._config_files  = dict()                    # cfg files

        self._qss_paths     = ()                        # qss file paths
        self._qss_files     = dict()                    # qss files
        self._initialized   = False

        if not self._initialized:
            self.run(paths=paths)

    def run(self, paths=[]):
        """
        Read all of the currently defined config files/stylesheets.

        :param str style: style name to parse.
        :param list paths: additional search paths.
        """
        self._fonts = self.initializeFontsList()

        self._config_paths = self._get_config_paths(paths=paths)
        self._config_files = self._get_config_files(self._config_paths)

        self._qss_paths = self._get_qss_paths(paths=paths)
        self._qss_files = self._get_qss_files(self._qss_paths)

        self._initialized = True

    @property
    def style(self):
        return self._style

    def style_data(self, style=None, **kwargs):
        """
        Return the stylesheet data.

        :returns: parsed stylesheet data.
        :rtype: str
        """
        if style is None:
            style = self._style
        parser = StyleParser(self, style=style)
        parser.run()
        data = parser.data(**kwargs)
        return data

    @property
    def config_names(self):
        """
        Returns a list of config file names.

        :returns: list of config names.
        :rtype: list
        """
        return self._config_files.keys()    

    def config_files(self, style='default'):
        """
        Returns a dictionary of config files for the given style.

        :param str style: style name to return.

        :returns: font/palette config files.
        :rtype: dict
        """
        return self._config_files.get(style, {})

    @property
    def qss_names(self):
        """
        Returns a list of stylesheet file names.

        :returns: list of stylesheet names.
        :rtype: list
        """
        return self._qss_files.keys()    

    @property
    def qss_files(self):
        return self._qss_files.values() 

    def _get_config_paths(self, paths=[]):
        """
        Read configs from config paths.

        :param list paths: list of paths to add to the scan.

        :returns: array of search paths.
        :rtype: tuple
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
                    log.debug('reading config external path: "%s".' % path)
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
                    log.debug('reading external stylesheet path: "%s".' % path)
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

                    names = bn.split('-')
                    if len(names) < 2:
                        log.warning('improperly named config file: "%s"' % cfg_file)
                        continue

                    style_name, cfg_type = names
                    if style_name not in cfg_files:
                        cfg_files[style_name] = dict(fonts=None, palette=None)

                    log.debug('adding %s config "%s" from "%s".' % (cfg_type, style_name, cfg_file))
                    cfg_files[style_name][cfg_type] = cfg_file
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

                        log.debug('adding stylesheet "%s" from "%s".' % (style_name, qss_file))

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

        :param str filename: filename to read.
        :param str name: name of the config.
        """
        if filename in self._config_files.values():
            for cfg_name, cfg_file in self._config_files.iteritems():
                if cfg_file == filename:
                    if name != cfg_name:
                        self._config_files.pop(cfg_name)
        self._config_files[name] = filename

    #- Fonts -----
    def initializeFontsList(self, valid=[]):
        """
        Builds the manager fonts list.

        params:
            valid (list) - list of valid font names.
        """
        if not valid:
            valid = [x for fontlist in options.SCENEGRAPH_VALID_FONTS.values() for x in fontlist]

        result = dict(ui=[], mono=[])
        for font_name in self._font_db.families():
            if font_name in valid:
                if not self._font_db.isFixedPitch(font_name):                
                    result['ui'].append(font_name)
                else:
                    result['mono'].append(font_name)
        return result

    def buildUIFontList(self, valid=[]):
        """
        Returns a list of monospace fonts.
        """
        if not valid:
            valid = options.SCENEGRAPH_VALID_FONTS.get('ui')

        families = []
        for font_name in self._fonts.get('ui'):
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
        for font_name in self._fonts.get('mono'):
            if font_name in valid:
                families.append(font_name)
        return families


class StyleParser(object):

    def __init__(self, parent, style=None):

        self.manager            = parent
        self.style              = style

        self._stylesheet        = None
        self._config_fonts      = None
        self._config_palette    = None

        self._data              = dict()

    def run(self, style='default'):
        """
        Parse the stylesheet data and substitute values from config file data.

        :param str style: style name to parse.
        :param dict kwargs: overrides.
        """
        stylesheet = self.manager._qss_files.get(style, None)
        configs    = self.manager.config_files(style)

        if stylesheet and os.path.exists(stylesheet):
            self._stylesheet = stylesheet

        if configs:
            if 'fonts' in configs:
                self._config_fonts = configs.get('fonts')

            if 'palette' in configs:
                self._config_palette = configs.get('palette')

        if self._stylesheet is not None:
            self._data = self._parse_configs()

    def _parse_configs(self):
        """
        Parse config data into a dictionary.
        """
        data = dict()
        data.update(defaults=dict())

        for config in [self._config_fonts, self._config_palette]:
            if not config or not os.path.exists(config):
                continue

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

    def data(self, **kwargs):
        """
        Returns the raw stylesheet data with config values substituted.

        :returns: stylesheet data.
        :rtype: str
        """
        import copy
        data = dict()
        style_data = copy.deepcopy(self._data)
        for k, v in style_data.pop('defaults', {}).iteritems():
            data['%s' % k] = v

        if options.PLATFORM in style_data:
            platform_defaults = style_data.get(options.PLATFORM)
            for attr, val in platform_defaults.iteritems():
                data[attr] = val

        # print data
        #print json.dumps(data, indent=5)

        if kwargs:
            for kattr, kval in kwargs.iteritems():
                attr_name = re.sub('_', '-', kattr)
                #print '# override: "%s": %s' % (attr_name, kval)
                data[attr_name] = kval

        ff = open(self._stylesheet, 'r')
        ss_lines = ""
        for line in ff.readlines():
            if line:
                if '@' in line:
                    if not '@STYLENAME' in line:
                        smatch = re.search(regex.get('value'), line)
                        if smatch:
                            value = str(smatch.group('value'))
                            if value in data:
                                new_value = str(data.get(value))
                                ss_lines += '%s' % re.sub('@%s' % value, new_value, line)
                                continue

                ss_lines += '%s' % line
        return ss_lines

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
