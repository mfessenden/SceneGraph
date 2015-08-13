#!/usr/bin/env python
import os
from PySide import QtCore, QtGui
from functools import partial
from SceneGraph import core


class PluginManager(QtGui.QDialog):

    def __init__(self, parent=None, plugins=[]):
        QtGui.QDialog.__init__(self, parent)

        self.fonts          = dict()

        if parent is not None:
            self.plugin_manager = parent.graph.plug_mgr
        else:
            graph = core.Graph()
            self.plugin_manager = graph.plug_mgr

            # todo: messy haxx
            from SceneGraph import ui
            self.stylesheet = ui.StylesheetManager(self)
            style_data = self.stylesheet.style_data()
            self.setStyleSheet(style_data) 

        self.setupFonts()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.mainLayout = QtGui.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        self.mainLayout.setObjectName("mainLayout")
        
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setObjectName("tabWidget")
        self.plugins_tab = QtGui.QWidget()
        self.plugins_tab.setObjectName("plugins_tab")
        self.pluginsTabLayout = QtGui.QVBoxLayout(self.plugins_tab)
        self.pluginsTabLayout.setSpacing(4)
        self.pluginsTabLayout.setContentsMargins(4, 4, 4, 4)
        self.pluginsTabLayout.setObjectName("pluginsTabLayout")
        
        self.pluginsGroup = QtGui.QGroupBox(self.plugins_tab)
        self.pluginsGroup.setProperty("class", "Plugins")        
        self.pluginsGroup.setObjectName("pluginsGroup")
        self.pluginsGroupLayout = QtGui.QHBoxLayout(self.pluginsGroup)
        self.pluginsGroupLayout.setSpacing(6)
        self.pluginsGroupLayout.setContentsMargins(9, 9, 9, 9)
        self.pluginsGroupLayout.setObjectName("pluginsGroupLayout")
        
        # table view
        self.pluginView = TableView(self.pluginsGroup)
        self.pluginView.setProperty("class", "Plugins")

        self.pluginView.setObjectName("pluginView")
        self.pluginsGroupLayout.addWidget(self.pluginView)
        self.pluginButtonsLayout = QtGui.QVBoxLayout()
        self.pluginButtonsLayout.setSpacing(4)
        self.pluginButtonsLayout.setObjectName("pluginButtonsLayout")
        
        # buttons
        self.button_disable = QtGui.QToolButton(self.pluginsGroup)
        self.button_disable.setMinimumSize(QtCore.QSize(75, 0))
        self.button_disable.setObjectName("button_disable")
        self.button_disable.setProperty("class", "Prefs")
        self.pluginButtonsLayout.addWidget(self.button_disable)

        self.button_reload = QtGui.QToolButton(self.pluginsGroup)
        self.button_reload.setMinimumSize(QtCore.QSize(75, 0))
        self.button_reload.setObjectName("button_reload")
        self.button_reload.setProperty("class", "Prefs")
        self.pluginButtonsLayout.addWidget(self.button_reload)

        self.button_load = QtGui.QToolButton(self.pluginsGroup)
        self.button_load.setMinimumSize(QtCore.QSize(75, 0))
        self.button_load.setObjectName("button_load")        
        self.button_load.setProperty("class", "Prefs")
        self.pluginButtonsLayout.addWidget(self.button_load)

        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.pluginButtonsLayout.addItem(spacerItem)
        self.pluginsGroupLayout.addLayout(self.pluginButtonsLayout)
        self.pluginsTabLayout.addWidget(self.pluginsGroup)
        self.tabWidget.addTab(self.plugins_tab, "")
        self.mainLayout.addWidget(self.tabWidget)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.mainLayout.addWidget(self.buttonBox)

        # table model
        self.tableModel = PluginTableModel(parent=self)
        self.pluginView.setModel(self.tableModel)
        self.tableSelectionModel = self.pluginView.selectionModel()
        
        self.initializeUI()
        self.connectSignals()
        self.checkPlugins()

    def initializeUI(self):
        """
        Setup the main UI
        """
        self.setWindowTitle("SceneGraph Plugin Manager")
        self.pluginsGroup.setTitle("Loaded Plugins")
        self.button_disable.setText("Disable")
        self.button_reload.setText("Reload")
        self.button_load.setText("Load...")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.plugins_tab), "Plugins")

        # NYI
        self.button_load.setEnabled(False)

    def connectSignals(self):
        self.button_disable.clicked.connect(self.disabledAction)
        self.button_reload.clicked.connect(self.checkPlugins)
        self.buttonBox.accepted.connect(self.acceptedAction)
        self.buttonBox.rejected.connect(self.close)

        self.tableSelectionModel.selectionChanged.connect(self.tableSelectionChanged)
        #self.pluginView.viewport().mouseMoveEvent()

    def checkPlugins(self):
        """
        Build the table.
        """
        data = []
        plugins = self.plugin_manager._node_data
        self.tableModel.clear()
        for plug_name in plugins:
            if plug_name not in ['default', 'dot']:
                pattrs = plugins.get(plug_name)
                dagnode = pattrs.get('dagnode', None)
                src = pattrs.get('source')
                enabled =pattrs.get('enabled')
                if dagnode is not None:
                    dagnode=dagnode.__name__
                
                widget = pattrs.get('widget', None)
                if widget is not None:
                    widget=widget.__name__

                metadata = pattrs.get('metadata', None)

                data.append([plug_name, dagnode, src, enabled])
        self.tableModel.addPlugins(data)

    def selectedPlugins(self):
        """
        returns:
            (list) - list of plugin attributes.
        """
        if not self.tableSelectionModel.selectedRows():
            return []
        plugins = []
        for i in self.tableSelectionModel.selectedRows():
            plugins.append(self.tableModel.plugins[i.row()])
        return plugins

    def tableSelectionChanged(self):
        plugins = self.selectedPlugins()

        enabled = True
        if plugins:
            for plugin in plugins:
                plugin_name = [self.tableModel.PLUGIN_NAME_ROW]
                if not plugin[self.tableModel.PLUGIN_ENABLED_ROW]:
                    enabled = False

        button_text = 'Disable'
        if not enabled:
            button_text = 'Enable'

        self.button_disable.setText(button_text)

    def disabledAction(self):
        plugins = self.selectedPlugins()
        if plugins:
            for plugin in plugins:
                plugin_name = plugin[self.tableModel.PLUGIN_NAME_ROW]
                enabled = bool(plugin[self.tableModel.PLUGIN_ENABLED_ROW])

                self.plugin_manager.enable(plugin_name, not enabled)
                self.checkPlugins()

    def acceptedAction(self):
        self.close()

    def sizeHint(self):
        return QtCore.QSize(800, 500)

    def setupFonts(self, font='SansSerif', size=9):
        """
        Initializes the fonts attribute
        """
        self.fonts = dict()
        self.fonts["ui"] = QtGui.QFont(font)
        self.fonts["ui"].setPointSize(size)

        self.fonts["mono"] = QtGui.QFont('Monospace')
        self.fonts["mono"].setPointSize(size)

        self.fonts["disabled"] = QtGui.QFont(font)
        self.fonts["disabled"].setPointSize(size)
        self.fonts["disabled"].setItalic(True)


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
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setIconSize(QtCore.QSize(16, 16))
        self.setShowGrid(False)
        self.setGridStyle(QtCore.Qt.NoPen)
        self.setSortingEnabled(False)
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



class PluginTableModel(QtCore.QAbstractTableModel):   

    PLUGIN_NAME_ROW     = 0
    PLUGIN_DAGNODE_ROW  = 1
    PLUGIN_FILE_ROW     = 2    
    PLUGIN_ENABLED_ROW  = 3

    def __init__(self, nodes=[], headers=['Plugin', 'Node Type', 'Source', 'Enabled'], parent=None, **kwargs):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.fonts      = parent.fonts
        self.plugins    = nodes
        self.headers    = headers

    def rowCount(self, parent):
        return len(self.plugins)

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
        if len(self.plugins) == 1:
            self.removeRows(0, 1)
        else:
            self.removeRows(0, len(self.plugins)-1)
        self.plugins=[]

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        plugin = self.plugins[index.row()]
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"), index, index)
        return 1

    def data(self, index, role):
        row     = index.row()
        column  = index.column()
        plugin  = self.plugins[row]

        is_enabled = plugin[self.PLUGIN_ENABLED_ROW]

        if role == QtCore.Qt.DisplayRole:
            if column == self.PLUGIN_NAME_ROW:
                return plugin[self.PLUGIN_NAME_ROW]

            if column == self.PLUGIN_FILE_ROW:
                return plugin[self.PLUGIN_FILE_ROW]

            if column == self.PLUGIN_DAGNODE_ROW:
                return plugin[self.PLUGIN_DAGNODE_ROW]

            if column == self.PLUGIN_ENABLED_ROW:
                return plugin[self.PLUGIN_ENABLED_ROW]

        elif role == QtCore.Qt.FontRole:
            font = self.fonts.get("ui")
            if not is_enabled:
                font = self.fonts.get("disabled")
            return font

        elif role == QtCore.Qt.ForegroundRole:            
            brush = QtGui.QBrush()
            brush.setColor(QtGui.QColor(212, 212, 212))
            
            if not is_enabled:
                brush.setColor(QtGui.QColor(204, 82, 73))

            return brush

    def setHeaders(self, headers):
        self.headers=headers

    def headerData(self, section, orientation, role):  
        if role == QtCore.Qt.DisplayRole:            
            if orientation == QtCore.Qt.Horizontal:
                if int(section) <= len(self.headers)-1:
                    return self.headers[section]
                else:
                    return ''
            
    def addPlugins(self, plugins):
        """
        adds a list of tuples to the nodes value
        """
        self.insertRows(0, len(plugins)-1)
        self.plugins=plugins
        self.layoutChanged.emit()
    
    def addPlugin(self, plugin):
        """
        adds a single ndoe to the nodes value
        """
        self.insertRows(len(self.plugins)-1, len(self.plugins)-1)
        self.plugins.append(plugin)
        
    def getPlugins(self):
        return self.plugins

    def sort(self, col, order):
        """
        sort table by given column number
        """
        import operator
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.plugins = sorted(self.plugins, key=operator.itemgetter(col))        
        if order == QtCore.Qt.DescendingOrder:
            self.plugins.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))

