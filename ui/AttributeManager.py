#!/usr/bin/env python
import os
from PySide import QtCore, QtGui
from functools import partial
from SceneGraph import core


class AttributeManager(QtGui.QMainWindow):

    def __init__(self, parent=None, nodes=[]):
        QtGui.QMainWindow.__init__(self, parent)

        self.centralwidget = QtGui.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.mainLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.mainLayout.setObjectName("mainLayout")
        self.mainGroup = QtGui.QGroupBox(self.centralwidget)
        self.mainGroup.setObjectName("mainGroup")
        self.mainGroupLayout = QtGui.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.setObjectName("mainGroupLayout")
        self.listViewLayout = QtGui.QHBoxLayout()
        self.listViewLayout.setObjectName("listViewLayout")
        self.listView = QtGui.QListView(self.mainGroup)
        self.listView.setObjectName("listView")
        self.listViewLayout.addWidget(self.listView)
        self.actionButtonsLayout = QtGui.QVBoxLayout()
        self.actionButtonsLayout.setObjectName("actionButtonsLayout")
        self.tb_new = QtGui.QToolButton(self.mainGroup)
        self.tb_new.setObjectName("tb_new")
        self.tb_new.setProperty("class", "Prefs")
        self.actionButtonsLayout.addWidget(self.tb_new)
        self.tb_delete = QtGui.QToolButton(self.mainGroup)
        self.tb_delete.setObjectName("tb_delete")
        self.tb_delete.setProperty("class", "Prefs")
        self.actionButtonsLayout.addWidget(self.tb_delete)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.actionButtonsLayout.addItem(spacerItem)
        self.listViewLayout.addLayout(self.actionButtonsLayout)
        self.mainGroupLayout.addLayout(self.listViewLayout)
        self.detailGroup = QtGui.QGroupBox(self.mainGroup)
        self.detailGroup.setObjectName("detailGroup")
        self.detailGroupLayout = QtGui.QGridLayout(self.detailGroup)
        self.detailGroupLayout.setObjectName("detailGroupLayout")
        self.label_name = QtGui.QLabel(self.detailGroup)
        self.label_name.setObjectName("label_name")
        self.detailGroupLayout.addWidget(self.label_name, 0, 0, 1, 1)
        self.line_name = QtGui.QLineEdit(self.detailGroup)
        self.line_name.setObjectName("line_name")
        self.detailGroupLayout.addWidget(self.line_name, 0, 1, 1, 2)
        self.label_nice_name = QtGui.QLabel(self.detailGroup)
        self.label_nice_name.setObjectName("label_nice_name")
        self.detailGroupLayout.addWidget(self.label_nice_name, 1, 0, 1, 1)
        self.line_nice_name = QtGui.QLineEdit(self.detailGroup)
        self.line_nice_name.setObjectName("line_nice_name")
        self.detailGroupLayout.addWidget(self.line_nice_name, 1, 1, 1, 2)
        self.label_type = QtGui.QLabel(self.detailGroup)
        self.label_type.setObjectName("label_type")
        self.detailGroupLayout.addWidget(self.label_type, 2, 0, 1, 1)
        self.rb_connectable = QtGui.QRadioButton(self.detailGroup)
        self.rb_connectable.setObjectName("rb_connectable")
        self.detailGroupLayout.addWidget(self.rb_connectable, 3, 1, 1, 1)
        self.rb_private = QtGui.QRadioButton(self.detailGroup)
        self.rb_private.setObjectName("rb_private")
        self.detailGroupLayout.addWidget(self.rb_private, 3, 2, 1, 1)
        self.menu_type = QtGui.QComboBox(self.detailGroup)
        self.menu_type.setObjectName("menu_type")
        self.detailGroupLayout.addWidget(self.menu_type, 2, 1, 1, 2)
        self.mainGroupLayout.addWidget(self.detailGroup)
        self.mainLayout.addWidget(self.mainGroup)
        self.buttonsLayout = QtGui.QHBoxLayout()
        self.buttonsLayout.setObjectName("buttonsLayout")
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.buttonsLayout.addItem(spacerItem1)
        self.button_cancel = QtGui.QPushButton(self.centralwidget)
        self.button_cancel.setObjectName("button_cancel")
        self.buttonsLayout.addWidget(self.button_cancel)
        self.button_accept = QtGui.QPushButton(self.centralwidget)
        self.button_accept.setObjectName("button_accept")
        self.buttonsLayout.addWidget(self.button_accept)
        self.mainLayout.addLayout(self.buttonsLayout)
        self.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 474, 25))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.model = AttributesListModel()
        self.listView.setModel(self.model)
        self.selection_model = self.listView.selectionModel()

        self.listView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.listView.customContextMenuRequested.connect(self.listContextMenu)

        self.initializeUI()
        self.connectSignals()

    def initializeUI(self):
        """
        Set up the main UI
        """
        self.setWindowTitle("Attributes Manager")
        self.mainGroup.setTitle("Attributes")
        self.tb_new.setText("New...")
        self.tb_delete.setText("Delete...")
        self.detailGroup.setTitle("Detail")
        self.label_name.setText("Name:")
        self.label_nice_name.setText("Nice Name:")
        self.label_type.setText("Type:")
        self.rb_connectable.setText("Connectable")
        self.rb_private.setText("Private")
        self.button_cancel.setText("&Cancel")
        self.button_accept.setText("&OK")

    def connectSignals(self):
        pass




class AttributesListModel(QtCore.QAbstractListModel):
    def __init__(self,  parent=None, nodes=[],):
        QtCore.QAbstractListModel.__init__(self, parent)

        self.nodes       = nodes
        self.attributes  = []

    def addAttributes(self, attributes):
        """
        adds a list of tuples to the assets value
        """
        self.insertRows(0, len(attributes), values=attributes)

    def getAttributes(self):
        return self.attributes

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.attributes)

    def data(self, index, role):
        row = index.row()
        column = index.column()
        bookmark = self.attributes[row]

        if role == QtCore.Qt.DecorationRole:
            icon = self.icons.get(bookmark.icon)
            return icon

        if role == QtCore.Qt.DisplayRole:
            return bookmark.name

        if role == QtCore.Qt.ToolTipRole:
            return bookmark.path

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
            self.attributes.insert(position + row, values[row])
        self.endInsertRows()
        return True

    def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, position, position + rows - 1)
        self.attributes = (self.attributes[:position] + self.attributes[position + rows:])
        self.endRemoveRows()
        return True