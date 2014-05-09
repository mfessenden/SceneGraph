#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
from functools import partial

from . import graph
reload(graph)


class SceneGraph(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        super(SceneGraph, self).__init__(parent)
        
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
        
        # for debugging
        self.graphicsScene.createNode('generic', [0, 0])
        self.graphicsScene.createNode('generic', [600, 25])
        
        self.graphicsScene.createNode('generic', [800, 1100])
        self.graphicsScene.createNode('generic', [10, 900])
        
    def setupUI(self):
        """
        Set up the main UI
        """
        # event filter
        self.eventFilter = MouseEventFilter(self)        
        self.installEventFilter(self.eventFilter)
        
        self.setWindowTitle('Scene Graph')
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([770, 300])
        self.setStyleSheet("QTabWidget {background-color:rgb(68, 68, 68)}")
        
        self._setupGraphicsView()
        self._setupNodeAttributes()
        self._setupOptions()
    
    def setupConnections(self):
        pass
    
    def _setupGraphicsView(self, filter=False):        
        # scene view
        self.graphicsScene = graph.GraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)
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
        
    def _setupNodeAttributes(self):
        self.detailGroup.setTitle('Node Attributes')

    def _setupOptions(self):
        self.optionsBox.setTitle('Options')

    def sizeHint(self):
        return QtCore.QSize(1070, 800)
    
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


class MouseEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # call a function here..
            # obj.doSomething()
            return True
        return False
    