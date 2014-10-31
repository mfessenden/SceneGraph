#!/X/tools/binlinux/xpython
from PySide import QtCore, QtGui
from functools import partial
import simplejson as json


class ContextMenu(object):
    """
    Creates a custom context menu from a data file
    """
    def __init__(self, parent, data):
        
        