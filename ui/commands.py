#!/usr/bin/env python
import re
from PySide import QtGui


class SceneNodesCommand(QtGui.QUndoCommand):    
    def __init__(self, old, new, scene, msg=None, parent=None):
        QtGui.QUndoCommand.__init__(self, parent)

        self.restored        = True
        self.scene           = scene

        self.data_old        = old
        self.data_new        = new

        self.diff            = DictDiffer(old, new)
        self.setText(self.diff.output())

        # set the current undo view message
        if msg is not None:
            self.setText(msg)

    def id(self):
        return (0xAC00 + 0x0002)

    def undo(self):
        self.scene.restoreNodes(self.data_old)
                
    def redo(self):
        if not self.restored:
            self.scene.restoreNodes(self.data_new)
        self.restored = False


class SceneChangedCommand(QtGui.QUndoCommand):
    """
    Command to track scene changes.
    """ 
    def __init__(self, old, new, scene, msg=None, parent=None):
        QtGui.QUndoCommand.__init__(self, parent)

        self.restored        = True
        self.scene           = scene

        self.data_old        = old
        self.data_new        = new

        self.diff            = DictDiffer(old, new)
        self.setText(self.diff.output())

        # set the current undo view message
        if msg is not None:
            self.setText(msg)

    def id(self):
        return (0xAC00 + 0x0003)

    def undo(self):
        self.scene.restoreNodes(self.data_old)
                
    def redo(self):
        if not self.restored:
            self.scene.restoreNodes(self.data_new)
        self.restored = False


class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

    def output(self):
        """
        Return a string for the undo command view.
        """
        msg = ""
        if self.changed():
            for x in self.changed():
                msg += "%s," % x
            msg = re.sub(",$", "", msg)
            msg+=" changed"
        
        return msg