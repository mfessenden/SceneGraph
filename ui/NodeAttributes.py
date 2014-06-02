#!/usr/bin/env xpython
from PyQt4 import QtGui, QtCore
import re


class NodeAttributesWidget(QtGui.QWidget):

    def __init__(self, parent=None, **kwargs):
        QtGui.QWidget.__init__(self, parent)
        
        self.manager        = kwargs.get('manager')
        self._current_node  = None
        
        self.gridLayout = QtGui.QGridLayout(self)
        
        # Name Attribute
        self.nameLabel = QtGui.QLabel(self)
        self.gridLayout.addWidget(self.nameLabel, 0, 0, 1, 1)
        self.nameEdit = QtGui.QLineEdit(self)
        self.gridLayout.addWidget(self.nameEdit, 0, 1, 1, 1)

        self.pathLabel = QtGui.QLabel(self)
        self.gridLayout.addWidget(self.pathLabel, 1, 0, 1, 1)
        self.pathEdit = QtGui.QLineEdit(self)
        self.gridLayout.addWidget(self.pathEdit, 1, 1, 1, 1)

        spacerItem = QtGui.QSpacerItem(20, 178, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 2, 1, 1, 1)

        self.nameLabel.setText("Name:")
        self.pathLabel.setText("Path:")
    
    def setNode(self, node_item):
        """
        Set the currently focused node
        """
        if node_item:
            self._current_node = node_item
            self.nameEdit.setText(node_item.node_name)
            self.nameEdit.textEdited.connect(self.nodeUpdatedFilter)
            self.nameEdit.editingFinished.connect(self.nodeFinalizedFilter)
            
            self.pathEdit.setText(node_item.path())
            self.pathEdit.setEnabled(False)
            
    def nodeUpdateAction(self):
        """
        Update the current node
        """
        new_name = str(self.nameEdit.text())
        if self._current_node:
            newNode = self.manager.renameNode(self._current_node.node_name, new_name)
            self.setNode(newNode)
    
    def nodeUpdatedFilter(self):
        """
        Runs when the task description (token) is updated
        """
        cur_val = re.sub('^_', '', str(self.nameEdit.text()).replace(' ', '_'))
        cur_val = re.sub('__', '_', cur_val)
        self.nameEdit.setText(cur_val)

    def nodeFinalizedFilter(self):
        """
        Runs when the task description (token) editing is finished
        """
        cur_val = str(self.nameEdit.text())
        cur_val = re.sub('^_', '', cur_val)
        cur_val = re.sub('_$', '', cur_val)        
        self.nameEdit.setText(cur_val)
        self.nodeUpdateAction()
