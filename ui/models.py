#!/usr/bin/env python
from PySide import QtCore, QtGui


class NodeListModel(QtCore.QAbstractListModel):
    def __init__(self,  parent=None, nodes=[],):
        QtCore.QAbstractListModel.__init__(self, parent)

        self.nodes = nodes

    def addNodes(self, nodes):
        """
        adds a list of tuples to the assets value
        """
        self.insertRows(0, len(nodes), values=nodes)

    def clear(self):
        self.nodes = []

    def getNodes(self):
        return self.nodes

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.nodes)

    def data(self, index, role):
        row = index.row()
        column = index.column()
        node = self.nodes[row]

        if role == QtCore.Qt.DecorationRole:
            icon = QtGui.QIcon()
            return icon

        if role == QtCore.Qt.DisplayRole:
            return node.name

        if role == QtCore.Qt.ToolTipRole:
            return node.name

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            row = index.row()
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRows(self, position, rows, parent=QtCore.QModelIndex(), values=[]):
        self.beginInsertRows(parent, position, position + rows - 1)
        for row in range(rows):
            self.nodes.insert(position + row, values[row])
        self.endInsertRows()
        return True

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, position, position + rows - 1)
        self.nodes = (self.nodes[:position] + self.nodes[position + rows:])
        self.endRemoveRows()
        return True