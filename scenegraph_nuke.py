#!/usr/bin/env python
from PySide import QtCore, QtGui


def main(debug=False):
    """
    Launch the Maya Scene Graph
    """
    from SceneGraph import scenegraph

    global win
    try:
        win.close()
    except:
        pass

    win = scenegraph.SceneGraphUI(env='nuke')
    win.show()
    return win
