#!/usr/bin/env python
from PySide import QtCore, QtGui
import maya.OpenMayaUI as OpenMayaUI
import shiboken


def getMayaWindow():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken.wrapInstance(long(ptr), QtGui.QMainWindow)
    else:
        print "No window found"


def main(debug=False):
    """
    Launch the Maya Scene Graph
    """
    from SceneGraph import scenegraph
    reload(scenegraph)

    global win
    try:
        win.close()
    except:
        pass

    win = scenegraph.SceneGraphUI(getMayaWindow(), env='maya')
    win.show()
    return win
