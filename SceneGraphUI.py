#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
from functools import partial
import os

from . import logger
from . import config
from . import graph
from . import ui
reload(config)
reload(graph)
reload(ui)


class SceneGraph(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        super(SceneGraph, self).__init__(parent)
        
        self._current_file    = None              # current save file name (if any)
        self._startdir        = os.getenv('HOME')
        self.timer            = QtCore.QTimer()
        self._recent_file_log = os.path.join(os.getenv('HOME'), '.mrx', 'SceneGraph', 'recent_files.json')
        
        self.settings       = QtCore.QSettings('SceneGraphc.ini', QtCore.QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)
        self.menubar = QtGui.QMenuBar(self)
        self.centralwidget = QtGui.QWidget(self)
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.graphTab = QtGui.QWidget()
        self.tabGridLayout = QtGui.QGridLayout(self.graphTab)
        self.main_splitter = QtGui.QSplitter(self.graphTab)
        self.main_splitter.setOrientation(QtCore.Qt.Horizontal)
        
        # Node view
        self.graphicsView = graph.GraphicsView(self.main_splitter, gui=self)
        self.right_splitter = QtGui.QSplitter(self.main_splitter)
        self.right_splitter.setOrientation(QtCore.Qt.Vertical)
        
        # Node Attributes
        self.detailGroup = QtGui.QGroupBox(self.right_splitter)
        self.detailGroupLayout = QtGui.QVBoxLayout(self.detailGroup)
        # add widgets here
        self.optionsBox = QtGui.QGroupBox(self.right_splitter)
        self.tabGridLayout.addWidget(self.main_splitter, 0, 0, 1, 1)
        
        self.tabWidget.addTab(self.graphTab, "Scene View")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 978, 22))
        self.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(self.statusbar)
        
        self.setupUI()
        self.connect(self.graphicsView, QtCore.SIGNAL("tabPressed"), partial(self.createTabMenu, self.graphicsView))
        
        # load saved settings
        self.resize(self.settings.value('size').toSize())
        self.move(self.settings.value('pos').toPoint())
        self.setMenuBar(self.menubar)        
        
    def setupUI(self):
        """
        Set up the main UI
        """
        self.setupFonts()
        self.statusBar().setFont(self.fonts.get('status'))
        # event filter
        self.eventFilter = MouseEventFilter(self)        
        self.installEventFilter(self.eventFilter)
        
        self.buildWindowTitle()
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([770, 300])
        self.setStyleSheet("QTabWidget {background-color:rgb(68, 68, 68)}")
        
        self._setupGraphicsView()
        self._setupNodeAttributes()
        self._setupOptions()
        
        self._buildMenuBar()        
        self.setupConnections()        
        
        self.resetStatus()
    
    def setupFonts(self, font='SansSerif', size=9):
        """ 
        Initializes the fonts attribute
        """
        self.fonts = dict()
        self.fonts["ui"] = QtGui.QFont(font)
        self.fonts["ui"].setPointSize(size)
        
        self.fonts["status"] = QtGui.QFont(font)
        self.fonts["status"].setStyleHint(QtGui.QFont.Courier)
        self.fonts["status"].setPointSize(size+1)
    
    def setupConnections(self):
        """
        Set up widget signals/slots
        """
        self.timer.timeout.connect(self.resetStatus)
    
    def _setupGraphicsView(self, filter=False):        
        # scene view
        
        # BUILD THE NODE MANAGER

        self.graphicsScene = graph.GraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)
        self.nodeManager = graph.NodeManager(self.graphicsView)
        self.graphicsScene.setNodeManager(self.nodeManager)
        self.graphicsView.setSceneRect(0, 0, 1000, 1000)
        #self.graphicsView.setSceneRect(-10000, -10000, 20000, 20000)

        # graphics View
        self.graphicsView.wheelEvent = self.graphicsView_wheelEvent
        self.graphicsView.resizeEvent = self.graphicsView_resizeEvent
        self.graphicsView.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60, 255), QtCore.Qt.SolidPattern))
        
        self.graphicsView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) 
        # event filter
        if filter:
            self.viewEventFilter = MouseEventFilter(self.graphicsView)
            self.graphicsView.viewport().installEventFilter(self.viewEventFilter)            
        self.graphicsScene.selectionChanged.connect(self.nodesSelectedAction)            
        
    def _setupNodeAttributes(self):
        self.detailGroup.setTitle('Node Attributes')

    def _setupOptions(self):
        self.optionsBox.setTitle('Scene')
    
    def _buildMenuBar(self):
        """
        Build the main menubar
        """
        # FILE MENU
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setTitle("File")
        
        self.action_save = QtGui.QAction(self)
        self.action_saveAs = QtGui.QAction(self)        
        self.action_read = QtGui.QAction(self)
        self.action_reset = QtGui.QAction(self)
        
        self.menuFile.addAction(self.action_save)
        self.menuFile.addAction(self.action_saveAs)        
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_read)
        
        self.action_save.setText("Save graph...")
        self.action_saveAs.setText("Save graph as...")
        self.action_read.setText("Read graph...")
        self.action_reset.setText("Reset graph")
        
        self.action_saveAs.triggered.connect(self.saveGraphAs)
        self.action_save.triggered.connect(self.saveCurrentGraph)
        self.action_read.triggered.connect(self.readGraph)
        self.action_reset.triggered.connect(self.resetGraph)
        
        if not self._current_file:
            self.action_save.setEnabled(False)
        self.menubar.addAction(self.menuFile.menuAction())

        # GRAPH MENU
        self.menuGraph = QtGui.QMenu(self.menubar)
        self.menuGraph.setTitle("Graph")
        self.action_add_generic = QtGui.QAction(self)
        self.menuGraph.addAction(self.action_add_generic)
        self.action_add_generic.setText("Add Generic node...")
        self.action_add_generic.triggered.connect(partial(self.graphicsScene.nodeManager.createNode, 'generic'))
        self.menubar.addAction(self.menuGraph.menuAction())
        
        # Build the recent files menu
        self._buildRecentFilesMenu()
        
        # add reset action to the bottom
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_reset)
    
    def _buildRecentFilesMenu(self):
        """
        Build a menu of recently opened scenes
        """
        import os
        import simplejson as json
        recent_files = dict()
        
        # build the menu
        self.recent_menu = QtGui.QMenu('Recent files...',self)
        self.menuFile.addMenu(self.recent_menu)
        self.recent_menu.setEnabled(False)
        
        if self._recent_file_log and os.path.exists(self._recent_file_log):
            raw_data = open(self._recent_file_log).read()
            data = json.loads(raw_data, object_pairs_hook=dict)
            recent_files = data.get('recent_files', {})
        
        
        if recent_files:
            # Recent files menu
            for k in sorted(recent_files.keys()):
                filename = recent_files.get(k)
                file_action = QtGui.QAction(filename, self.recent_menu)
                file_action.triggered.connect(partial(self.readRecentGraph, filename))
                self.recent_menu.addAction(file_action)                 
            self.recent_menu.setEnabled(True)
    
    def buildWindowTitle(self):
        """
        Build the window title
        """
        title_str = 'Scene Graph - v%s' % config.VERSION_AS_STRING
        if self._current_file:
            title_str = '%s - %s' % (title_str, self._current_file)
        self.setWindowTitle(title_str)
    
    #- STATUS MESSAGING ------
    # TODO: this is temp, find a better way to redirect output
    def updateStatus(self, val, level='info'):
        """
        Send output to logger/statusbar
        """
        if level == 'info':
            self.statusBar().showMessage(self._getInfoStatus(val))
            logger.getLogger().info(val)
        if level == 'error':
            self.statusBar().showMessage(self._getErrorStatus(val))
            logger.getLogger().error(val)
        if level == 'warning':
            self.statusBar().showMessage(self._getWarningStatus(val))
            logger.getLogger().warning(val)
        self.timer.start(4000)
    
    def resetStatus(self):
        self.statusBar().showMessage('[SceneGraph]: Ready')
    
    def _getInfoStatus(self, val):
        return '[SceneGraph]: Info: %s' % val

    def _getErrorStatus(self, val):
        return '[SceneGraph]: Error: %s' % val

    def _getWarningStatus(self, val):
        return '[SceneGraph]: Warning: %s' % val

    #- SAVING/LOADING ------
    def saveGraphAs(self, filename=None):
        """
        Save the current graph to a json file
        """
        import os
        if not filename:
            if self._current_file:
                filename = QtGui.QFileDialog.getSaveFileName(self, "Save graph file", self._current_file, "JSON files (*.json)")
            else:
                filename = QtGui.QFileDialog.getSaveFileName(self, "Save graph file", self._startdir, "JSON files (*.json)")
            if filename == "":
                return          
        
        self.updateStatus('saving current graph "%s"' % filename)
        self.graphicsScene.nodeManager.write(filename)
        self._current_file = str(filename)
        self.action_save.setEnabled(True)
        self.buildWindowTitle()
    
    # TODO: figure out why this has to be a separate method from saveGraphAs
    def saveCurrentGraph(self):
        """
        Save the current graph file
        """
        if self._current_file:
            self.updateStatus('saving current graph "%s"' % self._current_file)
            self.nodeManager.write(self._current_file)
            self.buildWindowTitle()
        else:
            self.updateStatus('no graph file is loaded', level='error')
        
    
    def readGraph(self):
        """
        Read the current graph from a json file
        """
        import os
        filename = QtGui.QFileDialog.getOpenFileName(self, "Open graph file", self._startdir, "JSON files (*.json)")
        if filename == "":
            return
        
        self.resetGraph()
        self.updateStatus('reading graph "%s"' % filename)
        self.graphicsScene.nodeManager.read(filename)
        self._current_file = str(filename)
        self.action_save.setEnabled(True)
        self.buildWindowTitle()
    
    # TODO: combine this with readGraph
    def readRecentGraph(self, filename):
        self.resetGraph()
        self.updateStatus('reading graph "%s"' % filename)
        self.graphicsScene.nodeManager.read(filename)
        self._current_file = filename
        self.action_save.setEnabled(True)
        self.buildWindowTitle()

    def resetGraph(self):
        """
        Reset the current graph
        """
        self.graphicsScene.nodeManager.reset()
        self._current_file = None
        self.action_save.setEnabled(False)
        self.buildWindowTitle()
        
    def sizeHint(self):
        return QtCore.QSize(1070, 800)
    
    def removeDetailWidgets(self):
        """
        Remove a widget from the detailGroup box
        """
        for i in reversed(range(self.detailGroupLayout.count())):
            widget = self.detailGroupLayout.takeAt(i).widget()
            if widget is not None: 
                widget.deleteLater()
    
    #- ACTIONS ----
    def nodesSelectedAction(self):
        self.removeDetailWidgets()
        nodes = self.graphicsScene.selectedItems()
        if len(nodes) == 1:
            node = nodes[0]
            if node._is_node:
                nodeAttrWidget = ui.NodeAttributesWidget(self.detailGroup, manager=self.graphicsScene.nodeManager, gui=self)                
                nodeAttrWidget.setNode(node)
                self.detailGroupLayout.addWidget(nodeAttrWidget)     
    
    #- EVENTS ----
    def graphicsView_wheelEvent(self, event):
        factor = 1.41 ** ((event.delta()*.5) / 240.0)
        self.graphicsView.scale(factor, factor)

    def graphicsView_resizeEvent(self, event):
        self.graphicsScene.setSceneRect(0, 0, self.graphicsView.width(), self.graphicsView.height())
       
    #- MENUS -----
    def createTabMenu(self, parent):
        """ build a context menu for the lights list """
        print '# Creating tab menu...'
        menu=QtGui.QMenu(parent)
        menu.clear()
        reset_action = menu.addAction('Reset options to default')
        menu.exec_(parent.scenePos())

    def closeEvent(self, event):
        """ 
        Write window prefs when UI is closed
        """
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        event.accept()

class MouseEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # call a function here..
            # obj.doSomething()
            return True
        return False

