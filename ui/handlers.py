#!/usr/bin/env python
from PySide import QtCore
from SceneGraph import core
from . import node_widgets
from . import commands

log = core.log


class EventHandler(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
   
        