#!/usr/bin/env python
import os

PACKAGE              	= 'SceneGraph'
VERSION              	= 0.40
REVISION             	= 4
VERSION_AS_STRING    	= '%.02f.%d' % (VERSION, REVISION)

SCENEGRAPH_PATH 		= os.path.dirname(__file__)
SCENEGRAPH_ICON_PATH 	= os.path.join(SCENEGRAPH_PATH, 'icn')
SCENEGRAPH_PREFS_PATH  	= os.path.join(os.getenv('HOME'), '.tools', PACKAGE)