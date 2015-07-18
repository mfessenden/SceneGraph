#!/usr/bin/env python
import os


PACKAGE                     = 'SceneGraph'
API_MAJOR_VERSION           = 0.64
API_REVISION                = 2
API_VERSION                 = float('%s%s' % (API_MAJOR_VERSION, API_REVISION))
API_VERSION_AS_STRING       = '%.02f.%d' % (API_MAJOR_VERSION, API_REVISION)
PLATFORM                    = None
API_MINIMUM                 = 0.640


SCENEGRAPH_PATH             = os.path.dirname(__file__)
SCENEGRAPH_PLUGIN_PATH      = os.path.join(SCENEGRAPH_PATH, 'plugins')
SCENEGRAPH_UI               = os.path.join(SCENEGRAPH_PATH, 'ui', 'SceneGraph.ui')
SCENEGRAPH_ATTR_EDITOR_UI   = os.path.join(SCENEGRAPH_PATH, 'ui', 'designer', 'NodeAttributes.ui')
SCENEGRAPH_ICON_PATH        = os.path.join(SCENEGRAPH_PATH, 'icn')
SCENEGRAPH_STYLESHEET_PATH  = os.path.join(SCENEGRAPH_PATH, 'css')
SCENEGRAPH_PREFS_PATH       = os.path.join(os.getenv('HOME'), '.config', PACKAGE)
SCENEGRAPH_TEST_PATH        = os.path.join(SCENEGRAPH_PATH, 'test')
SCENEGRAPH_USER_WORK_PATH   = os.path.join(os.getenv('HOME'), 'graphs')
SCENEGRAPH_FONTS            = dict()


SCENEGRAPH_COLORS = {
    'blush':[246, 202, 203, 255],
    'petal':[247, 170, 189, 255],
    'petunia':[231, 62, 151, 255],
    'deep_pink':[229, 2, 120, 255],
    'melon':[241, 118, 110, 255],
    'pomegranate':[178, 27, 32, 255],
    'poppy_red':[236, 51, 39, 255],
    'orange_red':[240, 101, 53, 255],
    'olive':[174, 188, 43, 255],
    'spring':[227, 229, 121, 255],
    'yellow':[255, 240, 29, 255],
    'mango':[254, 209, 26, 255],
    'cantaloupe':[250, 176, 98, 255],
    'tangelo':[247, 151, 47, 255],
    'burnt_orange':[236, 137, 36, 255],
    'bright_orange':[242, 124, 53, 255],
    'moss':[176, 186, 39, 255],
    'sage':[212, 219, 145, 255],
    'apple':[178, 215, 140, 255],
    'grass':[111, 178, 68, 255],
    'forest':[69, 149, 62, 255],
    'peacock':[21, 140, 167, 255],
    'teal':[24, 157, 193, 255],
    'aqua':[153, 214, 218, 255],
    'violet':[55, 52, 144, 255],
    'deep_blue':[15, 86, 163, 255],
    'hydrangea':[150, 191, 229, 255],
    'sky':[139, 210, 244, 255],
    'dusk':[16, 102, 162, 255],
    'midnight':[14, 90, 131, 255],
    'seaside':[87, 154, 188, 255],
    'poolside':[137, 203, 225, 255],
    'eggplant':[86, 5, 79, 255],
    'lilac':[222, 192, 219, 255],
    'chocolate':[87, 43, 3, 255],
    'blackout':[19, 17, 15, 255],
    'stone':[125, 127, 130, 255],
    'gravel':[181, 182, 185, 255],
    'pebble':[217, 212, 206, 255],
    'sand':[185, 172, 151, 255],
    }


LOGGING_LEVELS = {
    'CRITICAL':50,
    'ERROR': 40,
    'WARNING':30,
    'INFO': 20,
    'DEBUG':10,
    'NOTSET':0
    }


# Default preferences
SCENEGRAPH_PREFERENCES = {
    'use_gl' : {'default':False, 'desc':'Render graph with OpenGL.'},
    'edge_type' : {'default':'bezier', 'desc':'Draw edges with bezier paths.'},
    'render_fx' : {'default': True, 'desc':'Render node drop shadows and effects.'},
    'antialiasing' : {'default': 2, 'desc':'Antialiasing level.'},
    'logging_level' : {'default':30, 'desc':'Verbosity level.'},
    'font_ui' : {'default':'DejaVu Sans', 'desc':'Default UI font.'},
    'font_mono' : {'default':'Menlo', 'desc':'Monospace font for UI.'},
    'font_nodes' : {'default':'Menlo', 'desc':'Font for node labels.'},
    'autosave_inc' : {'default':90000, 'desc':'Autosave delay (seconds x 1000).'},
    }



def setup_platform_defaults():
    """
    Setup globals for a specific platform.
    """
    import sys
    plaform = 'Windows'
    if 'linux' in sys.platform:
        plaform = 'Linux'

    if sys.platform == 'darwin':
        plaform = 'MacOSX'
    return plaform


def setup_fonts(font='SansSerif', size=8, platform=None):
    """
    Initializes the global fonts attribute.
    """
    from PySide import QtGui
    fonts = dict()
    mono_family = 'Consolas'

    # standard sizes
    size_ui = size
    size_mn = size
    size_sm = size

    if platform == 'MacOSX':
        size_ui = size + 4
        size_mn = size + 2
        size_sm = size_ui - 1        
        mono_family = 'Menlo'

    fonts["ui"] = QtGui.QFont(font)
    fonts["ui"].setPointSize(size_ui)

    fonts["output"] = QtGui.QFont('Monospace')
    fonts["output"].setPointSize(size_mn)
    fonts["output"].setFamily(mono_family)

    fonts["console"] = QtGui.QFont('Monospace')
    fonts["console"].setPointSize(size_mn)
    fonts["console"].setFamily(mono_family)

    fonts["attr_editor"] = QtGui.QFont(font)
    fonts["attr_editor"].setPointSize(size_ui)

    fonts["attr_editor_group"] = QtGui.QFont(font)
    fonts["attr_editor_group"].setPointSize(size_ui)
    fonts["attr_editor_group"].setBold(True)

    fonts["attr_editor_label"] = QtGui.QFont(font)
    fonts["attr_editor_label"].setPointSize(size_sm)

    fonts["disabled"] = QtGui.QFont(font)
    fonts["disabled"].setPointSize(size_ui)
    fonts["disabled"].setItalic(True)
    return fonts


# initialize globals
PLATFORM         = setup_platform_defaults()
SCENEGRAPH_FONTS = setup_fonts(platform=PLATFORM)