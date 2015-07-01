#!/usr/bin/env python
from PySide import QtGui


class NodeDataCommand(QtGui.QUndoCommand):    
    def __init__(self, old, new, scene, parent=None):
        QtGui.QUndoCommand.__init__(self, parent)

        self.restored        = True
        self.scene           = scene

        self.data_old        = old
        self.data_new        = new
        
    def id(self):
        return hex(255)

    def undo(self):
        self.scene.restoreNodes(self.data_old)
                
    def redo(self):
        if not self.restored:
            self.scene.restoreNodes(self.data_new)
        self.restored = False


class CommandMove(QtGui.QUndoCommand):
    def __init__(self, node, old_pos, new_pos, parent=None):
        QtGui.QUndoCommand.__init__(self, parent)

        self.node       = node
        self.from_pos   = old_pos
        self.to_pos     = new_pos
  
    def redo(self):
        self.node.setPos(self.to_pos)
  
    def undo(self):
        self.node.setPos(self.from_pos)