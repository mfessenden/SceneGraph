#!/usr/bin/env python
from PySide import QtCore, QtGui
from functools import partial
import os

from . import logger
from . import options
from . import core
from . import ui
from . import prefs

reload(options)
reload(core)
reload(ui)
reload(prefs)


import os
import pysideuic
import xml.etree.ElementTree as xml
from cStringIO import StringIO

SCENEGRAPH_UI = options.SCENEGRAPH_UI


def loadUiType(uiFile):
    """
    Pyside lacks the "loadUiType" command, so we have to convert the ui file to py code in-memory first
    and then execute it in a special frame to retrieve the form_class.
    """
    parsed = xml.parse(uiFile)
    widget_class = parsed.find('widget').get('class')
    form_class = parsed.find('class').text

    with open(uiFile, 'r') as f:
        o = StringIO()
        frame = {}

        pysideuic.compileUi(f, o, indent=0)
        pyc = compile(o.getvalue(), '<string>', 'exec')
        exec pyc in frame

        #Fetch the base_class and form class based on their type in the xml from designer
        form_class = frame['Ui_%s'%form_class]
        base_class = eval('QtGui.%s'%widget_class)
    return form_class, base_class


#If you put the .ui file for this example elsewhere, just change this path.
form_class, base_class = loadUiType(SCENEGRAPH_UI)



class SceneGraph(form_class, base_class):
    def __init__(self, parent=None, **kwargs):
        super(SceneGraph, self).__init__(parent)

        self.setupUi(self)
        
        # add our custom GraphicsView object
        self.view = ui.GraphicsView(self.gview)
        self.scene = self.view.scene()
        self.gviewLayout.addWidget(self.view)

        # allow docks to be nested
        self.setDockNestingEnabled(True)

        #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._startdir        = kwargs.get('start', os.getenv('HOME'))
        self.timer            = QtCore.QTimer()

        # preferences
        self.prefs_key        = 'SceneGraph'
        self.prefs            = prefs.RecentFiles(self, ui=self.prefs_key)
        self.recent_menu      = None

        self.settings_file    = self.prefs.qtsettings
        self.qtsettings       = QtCore.QSettings(self.settings_file, QtCore.QSettings.IniFormat)
        self.qtsettings.setFallbacksEnabled(False)

        # icon
        self.setWindowIcon(QtGui.QIcon(os.path.join(options.SCENEGRAPH_ICON_PATH, 'graph_icon.png')))

        self.readSettings()
        self.initializeUI()        
        self.connectSignals()

        # stylesheet
        self.stylesheet = os.path.join(options.SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

    def initializeUI(self):
        """
        Set up the main UI
        """
        self.setupFonts()
        
        # event filter
        self.eventFilter = MouseEventFilter(self)
        self.installEventFilter(self.eventFilter)
        
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([770, 300])
        self.setStyleSheet("QTabWidget {background-color:rgb(68, 68, 68)}")

        # build the graph
        self._setupGraphicsView()

        self.statusBar().setFont(self.fonts.get('status'))
        self.outputPlainTextEdit.setFont(self.fonts.get('output'))
        self._buildRecentFilesMenu()
        self.buildWindowTitle()
        self.resetStatus()

    def setupFonts(self, font='SansSerif', size=9):
        """
        Initializes the fonts attribute
        """
        self.fonts = dict()
        self.fonts["ui"] = QtGui.QFont(font)
        self.fonts["ui"].setPointSize(size)

        self.fonts["status"] = QtGui.QFont('Monospace')
        self.fonts["status"].setPointSize(size-1)

        self.fonts["output"] = QtGui.QFont('Monospace')
        self.fonts["output"].setPointSize(size+1)

    def _setupGraphicsView(self, filter=False):
        """
        Initialize the graphics view and graph object.
        """
        # scene view signals
        self.scene.nodeAdded.connect(self.nodeAddedAction)
        self.scene.nodeChanged.connect(self.nodeChangedAction)
        self.scene.changed.connect(self.sceneChangedAction)

        # initialize the Graph
        self.graph = core.Graph(self.view, gui=self)
        self.network = self.graph.network.graph

        self.scene.setNodeManager(self.graph)
        self.view.setSceneRect(-5000, -5000, 10000, 10000)

        # graphics View
        self.view.wheelEvent = self.graphicsView_wheelEvent
        self.view.resizeEvent = self.graphicsView_resizeEvent

        # maya online
        self.view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60, 255), QtCore.Qt.SolidPattern))

        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # event filter
        if filter:
            self.viewEventFilter = MouseEventFilter(self.view)
            self.view.viewport().installEventFilter(self.viewEventFilter)

        # TESTING: disable
        self.scene.selectionChanged.connect(self.nodesSelectedAction)

    def connectSignals(self):
        """
        Setup signals & slots.
        """
        self.timer.timeout.connect(self.resetStatus)
        self.view.tabPressed.connect(partial(self.createTabMenu, self.view))

        # FILE MENU
        self.action_save_graph_as.triggered.connect(self.saveGraphAs)
        self.action_save_graph.triggered.connect(self.saveCurrentGraph)
        self.action_read_graph.triggered.connect(self.readGraph)
        self.action_clear_graph.triggered.connect(self.resetGraph)
        self.action_reset_scale.triggered.connect(self.resetScale)

        current_pos = QtGui.QCursor().pos()
        self.action_add_default.triggered.connect(partial(self.graph.addNode, 'default', pos=[current_pos.x(), current_pos.y()]))

        # output tab buttons
        self.tabWidget.currentChanged.connect(self.updateOutput)
        self.button_refresh.clicked.connect(self.updateOutput)
        self.button_clear.clicked.connect(self.outputPlainTextEdit.clear)

    def _buildRecentFilesMenu(self):
        """
        Build a menu of recently opened scenes
        """
        recent_files = dict()
        recent_files = self.prefs.getRecentFiles()
        self.menu_recent_files.clear()
        self.menu_recent_files.setEnabled(False)
        if recent_files:
            # Recent files menu
            for filename in recent_files:
                file_action = QtGui.QAction(filename, self.menu_recent_files)
                file_action.triggered.connect(partial(self.readRecentGraph, filename))
                self.menu_recent_files.addAction(file_action)
            self.menu_recent_files.setEnabled(True)

    def buildWindowTitle(self):
        """
        Build the window title
        """
        title_str = 'Scene Graph - v%s' % options.VERSION_AS_STRING
        if self.graph.getScene():
            title_str = '%s - %s' % (title_str, self.graph.getScene())
        self.setWindowTitle(title_str)

    #- STATUS MESSAGING ------
    # TODO: this is temp, find a better way to redirect output
    def updateStatus(self, val, level='info'):
        """
        Send output to logger/statusbar
        """
        self.statusBar().setFont(self.fonts.get('status'))
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
        """
        Reset the status bar message.
        """
        self.statusBar().showMessage('[SceneGraph]: ready')
        self.statusBar().setFont(self.fonts.get('status'))

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

        Pass the filename argument to override

        params:
            filename  - (str) file path
        """
        import os
        if not filename:
            if self.graph.getScene():
                filename, filters = QtGui.QFileDialog.getSaveFileName(self, "Save graph file", self.graph.getScene(), "JSON files (*.json)")
                if filename == "":
                    return

        filename = str(os.path.normpath(filename))
        self.updateStatus('saving current graph "%s"' % filename)

        # update the graph attributes
        #root_node.addNodeAttributes(**{'sceneName':filename})

        self.graph.write(filename)
        self.action_save_graph.setEnabled(True)
        self.buildWindowTitle()

        self.graph.setScene(filename)
        self.prefs.addFile(filename)
        self._buildRecentFilesMenu()
        self.buildWindowTitle()

    # TODO: figure out why this has to be a separate method from saveGraphAs
    def saveCurrentGraph(self):
        """
        Save the current graph file
        """
        self.updateStatus('saving current graph "%s"' % self.graph.getScene())
        self.graph.write(self.graph.getScene())
        self.buildWindowTitle()

        self.prefs.addFile(self.graph.getScene())
        self._buildRecentFilesMenu()        

    def readGraph(self):
        """
        Read the current graph from a json file
        """
        filename, ok = QtGui.QFileDialog.getOpenFileName(self, "Open graph file", self._startdir, "JSON files (*.json)")
        if filename == "":
            return

        self.graph.reset()
        self.resetGraph()
        self.updateStatus('reading graph "%s"' % filename)
        self.graph.read(filename)
        self.action_save_graph.setEnabled(True)
        self.graph.setScene(filename)
        self.buildWindowTitle()

    # TODO: combine this with readGraph
    def readRecentGraph(self, filename):
        self.resetGraph()
        self.graph.reset()
        self.updateStatus('reading graph "%s"' % filename)
        self.graph.read(filename)
        self.action_save_graph.setEnabled(True)
        self.graph.setScene(filename)
        self.buildWindowTitle()

    def resetGraph(self):
        """
        Reset the current graph
        """
        self.graph.reset()
        self.view.scene().clear()
        self.action_save_graph.setEnabled(False)
        self.network.clear()
        self.buildWindowTitle()
        self.updateOutput()

    def resetScale(self):
        self.view.resetMatrix()

    def sizeHint(self):
        return QtCore.QSize(1070, 800)

    def removeDetailWidgets(self):
        """
        Remove a widget from the detailGroup box.
        """
        for i in reversed(range(self.attrEditorLayout.count())):
            widget = self.attrEditorLayout.takeAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    #- ACTIONS ----
    def nodesSelectedAction(self):
        """
        Action that runs whenever a node is selected in the UI
        """
        self.removeDetailWidgets()
        nodes = self.scene.selectedItems()
        if len(nodes) == 1:
            node = nodes[0]
            if node._is_node:
                nodeAttrWidget = ui.AttributeEditor(self.attrEditorWidget, manager=self.scene.graph, gui=self)
                nodeAttrWidget.setNode(node)
                self.attrEditorLayout.addWidget(nodeAttrWidget)

    def nodeAddedAction(self, node):
        """
        Action whenever a node is added to the graph.
        """
        node.updateDagNode()
        self.updateOutput()

    def nodeChangedAction(self, node):
        """
        node = NodeWidget
        """
        #node.updateDagNode()
        self.updateOutput()

    def sceneChangedAction(self, event):
        self.nodesSelectedAction()
        self.updateNodes()

    #- Events ----
    def closeEvent(self, event):
        """
        Write window prefs when UI is closed
        """
        self.writeSettings()
        event.accept()

    def graphicsView_wheelEvent(self, event):
        factor = 1.41 ** ((event.delta()*.5) / 240.0)
        self.view.scale(factor, factor)

    def graphicsView_resizeEvent(self, event):
        #self.scene.setSceneRect(0, 0, self.view.width(), self.view.height())
        pass

    #- Menus -----
    def createTabMenu(self, parent):
        """
        Build a context menu at the current pointer pos.
        """
        menu=QtGui.QMenu(parent)
        menu.clear()
        add_action = menu.addAction('Add default node')        
        qcurs=QtGui.QCursor()
        view_pos =  self.view.current_cursor_pos
        add_action.triggered.connect(partial(self.graph.addNode, node_type='default', pos=[view_pos.x(), view_pos.y()]))
        menu.exec_(qcurs.pos())

    #- Settings -----
    def readSettings(self):
        """
        Read Qt settings from file
        """
        self.qtsettings.beginGroup(self.prefs_key)
        self.resize(self.qtsettings.value("size", QtCore.QSize(400, 256)))
        self.move(self.qtsettings.value("pos", QtCore.QPoint(200, 200)))
        self.qtsettings.endGroup()

    def writeSettings(self):
        """
        Write Qt settings to file
        """
        self.qtsettings.beginGroup(self.prefs_key)
        width = self.width()
        height = self.height()
        self.qtsettings.setValue("size", QtCore.QSize(width, height))
        self.qtsettings.setValue("pos", self.pos())
        self.qtsettings.endGroup()

    def updateOutput(self):
        """
        Update the output text edit.
        """
        import networkx.readwrite.json_graph as nxj
        import simplejson as json
        self.updateNodes()
        self.outputPlainTextEdit.clear()
        #graph_data = nxj.adjacency_data(self.graph.network)
        graph_data = nxj.node_link_data(self.graph.network)
        self.outputPlainTextEdit.setPlainText(json.dumps(graph_data, indent=5))
        self.outputPlainTextEdit.setFont(self.fonts.get('output'))

    def updateNodes(self):
        """
        Update the networkx graph with current node values.
        """
        if self.scene.sceneNodes:
            for node in self.scene.sceneNodes.values():
                try:
                    self.graph.network.node[node.uuid]['name']=node.dagnode.name
                    self.graph.network.node[node.uuid]['pos_x']=node.pos().x()
                    self.graph.network.node[node.uuid]['pos_y']=node.pos().y()
                    self.graph.network.node[node.uuid]['width']=node.width
                    self.graph.network.node[node.uuid]['height']=node.height
                    self.graph.network.node[node.uuid]['expanded']=node.expanded
                except:
                    pass

class MouseEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # call a function here..
            # obj.doSomething()
            return True
        return False

