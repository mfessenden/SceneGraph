#!/usr/bin/env python
from PySide import QtCore, QtGui
import operator


class TableView(QtGui.QTableView):

    def __init__(self, parent=None, **kwargs):
        QtGui.QTableView.__init__(self, parent)

        # attributes
        self._last_indexes  = []              # stash the last selected indexes

        self.installEventFilter(self)
        self.verticalHeader().setDefaultSectionSize(17)
        
        self.setShowGrid(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.Alignment())
        self.verticalHeader().setVisible(False)

        self.fileSizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.fileSizePolicy.setHorizontalStretch(0)
        self.fileSizePolicy.setVerticalStretch(0)
        self.fileSizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(self.fileSizePolicy)

        #self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setIconSize(QtCore.QSize(16, 16))
        self.setShowGrid(False)
        self.setGridStyle(QtCore.Qt.NoPen)
        self.setSortingEnabled(True)
        self.verticalHeader().setDefaultSectionSize(18)  # 24
        self.verticalHeader().setMinimumSectionSize(18)  # 24

        # dnd
        self.setDragEnabled(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)

        # context Menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def getSelectedIndexes(self):
        """
        returns the selected indexes
        """
        return self.selectionModel().selectedIndexes()

    def getSelectedRows(self):
        """
        returns the selected rows
        """
        return self.selectionModel().selectedRows()

    def focusOutEvent(self, event):
        if self.selectionModel().selectedIndexes():
            for index in self.selectionModel().selectedRows():
                self._last_indexes.append(QtCore.QPersistentModelIndex(index))

        if self._last_indexes:
            for i in self._last_indexes:
                self.selectionModel().setCurrentIndex(i, QtGui.QItemSelectionModel.Select)
        event.accept()



class GraphTableModel(QtCore.QAbstractTableModel):   

    NODE_TYPE_ROW = 0
    NODE_NAME_ROW = 1

    def __init__(self, nodes=[], headers=[], parent=None, **kwargs):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.nodes = nodes
        self.headers = headers

    def rowCount(self, parent):
        return len(self.nodes)

    def columnCount(self, parent):
        return len(self.headers)

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows - 1)
        #for row in range(rows):
        #    self.nodes.insert(position + row, Asset())
        self.endInsertRows()
        self.dirty = True
        return True

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):        
        self.beginRemoveRows(parent, position, position + rows - 1)
        self.endRemoveRows()
        return True

    def insertColumns(self, position, columns, parent = QtCore.QModelIndex()):
        self.beginInsertColumns(parent, position, position + columns - 1) 
        self.endInsertColumns()        
        return True

    def removeColumns(self, position, columns, parent = QtCore.QModelIndex()):
        self.beginRemoveColumns(parent, position, position + columns - 1) 
        self.endRemoveColumns()        
        return True

    def clear(self):
        if len(self.nodes) == 1:
            self.removeRows(0, 1)
        else:
            self.removeRows(0, len(self.nodes)-1)
        self.nodes=[]

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        node = self.nodes[index.row()]
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), index, index)
        return 1

    def data(self, index, role):
        row = index.row()
        column = index.column()
        node=self.nodes[row]

        if role == QtCore.Qt.FontRole:
            font = QtGui.QFont('Monospace')
            if not node.enabled:
                font.setItalic(True)
            return font

        if role == QtCore.Qt.ForegroundRole:
            color = QtGui.QColor(150, 150, 150)
            if not node.enabled:
                color.setRgb(95, 95, 105)
            return color

        if role == QtCore.Qt.DisplayRole:
            if column == self.NODE_TYPE_ROW:
                return node.node_type

            if column == self.NODE_NAME_ROW:
                return node.name

    def setHeaders(self, headers):
        self.headers=headers

    def headerData(self, section, orientation, role):  
        if role == QtCore.Qt.DisplayRole:            
            if orientation == QtCore.Qt.Horizontal:
                if int(section) <= len(self.headers)-1:
                    return self.headers[section]
                else:
                    return ''
            
    def addNodes(self, nodes):
        """
        adds a list of tuples to the nodes value
        """
        self.insertRows(0, len(nodes)-1)
        self.nodes=nodes
        self.layoutChanged.emit()
    
    def addNode(self, node):
        """
        adds a single ndoe to the nodes value
        """
        self.insertRows(len(self.nodes)-1, len(self.nodes)-1)
        self.nodes.append(node)
        
    def getNodes(self):
        return self.nodes

    def sort(self, col, order):
        """
        sort table by given column number
        """
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.nodes = sorted(self.nodes, key=operator.itemgetter(col))        
        if order == QtCore.Qt.DescendingOrder:
            self.nodes.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))


class NodesListModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None, nodes=[],):
        QtCore.QAbstractListModel.__init__(self, parent)

        self.nodes = nodes

    def addNodes(self, nodes):
        """
        adds a list of tuples to the assets value
        """
        self.insertRows(0, len(nodes), values=nodes)

    def getNodes(self):
        return self.nodes

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.nodes)

    def data(self, index, role):
        row = index.row()
        column = index.column()
        node = self.nodes[row]

        if role == QtCore.Qt.DisplayRole:
            return node.dagnode.name

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def clear(self):
        if len(self.nodes) == 1:
            self.removeRows(0, 1)
        else:
            self.removeRows(0, len(self.nodes)-1)
        self.nodes=[]

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


class EdgesListModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None, edges=[],):
        QtCore.QAbstractListModel.__init__(self, parent)

        self.edges = edges

    def addEdges(self, edges):
        """
        adds a list of tuples to the assets value
        """
        #print 'adding edges: ', len(edges)
        self.insertRows(0, len(edges), values=edges)

    def getEdges(self):
        return self.edges

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.edges)

    def data(self, index, role):
        row = index.row()
        column = index.column()
        edge = self.edges[row]

        if role == QtCore.Qt.DisplayRole:
            return edge.dagnode.name

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def clear(self):
        if len(self.edges) == 1:
            self.removeRows(0, 1)
        else:
            self.removeRows(0, len(self.edges)-1)
        self.edges=[]

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            row = index.row()
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRows(self, position, rows, parent=QtCore.QModelIndex(), values=[]):
        self.beginInsertRows(parent, position, position + rows - 1)
        for row in range(rows):
            self.edges.insert(position + row, values[row])
        self.endInsertRows()
        return True

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, position, position + rows - 1)
        self.edges = (self.edges[:position] + self.edges[position + rows:])
        self.endRemoveRows()
        return True