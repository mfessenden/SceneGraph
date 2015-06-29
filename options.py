#!/usr/bin/env python
import os


PACKAGE                     = 'SceneGraph'
API_VERSION                 = 0.60
API_REVISION                = 8
API_VERSION_AS_STRING       = '%.02f.%d' % (API_VERSION, API_REVISION)
PLATFORM 					= None

SCENEGRAPH_PATH             = os.path.dirname(__file__)
SCENEGRAPH_NODE_PATH        = os.path.join(SCENEGRAPH_PATH, 'core', 'dagnodes')
SCENEGRAPH_UI               = os.path.join(SCENEGRAPH_PATH, 'ui', 'SceneGraph.ui')
SCENEGRAPH_ATTR_EDITOR_UI   = os.path.join(SCENEGRAPH_PATH, 'ui', 'designer', 'NodeAttributes.ui')
SCENEGRAPH_ICON_PATH        = os.path.join(SCENEGRAPH_PATH, 'icn')
SCENEGRAPH_STYLESHEET_PATH  = os.path.join(SCENEGRAPH_PATH, 'css')
SCENEGRAPH_PREFS_PATH       = os.path.join(os.getenv('HOME'), '.config', PACKAGE)
SCENEGRAPH_TEST_PATH        = os.path.join(SCENEGRAPH_PATH, 'test')


def get_platform():
	"""
	Returns the current platform (OS) variation.

	returns:
		(str) - platform (Linux, MacOSX or Windows)
	"""
	import sys
	if 'linux' in sys.platform:
		return 'Linux'
	if sys.platform == 'darwin':
		return 'MacOSX'
	return 'Windows'


get_platform()



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
}