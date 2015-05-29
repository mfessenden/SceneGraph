#!/usr/bin/env python
import os

PACKAGE              		= 'SceneGraph'
VERSION              		= 0.50
REVISION             		= 1
VERSION_AS_STRING    		= '%.02f.%d' % (VERSION, REVISION)

SCENEGRAPH_PATH 			= os.path.dirname(__file__)
SCENEGRAPH_ICON_PATH 		= os.path.join(SCENEGRAPH_PATH, 'icn')
SCENEGRAPH_STYLESHEET_PATH  = os.path.join(SCENEGRAPH_PATH, 'css')
SCENEGRAPH_PREFS_PATH  		= os.path.join(os.getenv('HOME'), '.tools', PACKAGE)