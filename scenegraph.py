#!/usr/bin/env python
from PySide import QtCore, QtGui
from functools import partial
import os
import pysideuic
import xml.etree.ElementTree as xml
from cStringIO import StringIO

from SceneGraph import options
from SceneGraph import core
from SceneGraph import ui

reload(options)
reload(core)
reload(ui)


log = core.log
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



class SceneGraphUI(form_class, base_class):
    def __init__(self, parent=None, **kwargs):
        super(SceneGraphUI, self).__init__(parent)

        self.setupUi(self)
        
        # allow docks to be nested
        self.setDockNestingEnabled(True)

        #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._startdir        = kwargs.get('start', os.getenv('HOME'))
        self.timer            = QtCore.QTimer()

        # preferences
        self.settings_file    = os.path.join(options.SCENEGRAPH_PREFS_PATH, 'SceneGraph.ini')
        self.qtsettings       = Settings(self.settings_file, QtCore.QSettings.IniFormat, parent=self)
        self.qtsettings.setFallbacksEnabled(False)

        # icon
        self.setWindowIcon(QtGui.QIcon(os.path.join(options.SCENEGRAPH_ICON_PATH, 'graph_icon.png')))

        self.initializeUI()
        self.readSettings()       
        self.connectSignals()

        # stylesheet
        self.stylesheet = os.path.join(options.SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

        self.resetStatus()

    def initializeUI(self):
        """
        Set up the main UI
        """
        # add our custom GraphicsView object
        self.view = ui.GraphicsView(self.gview, ui=self)
        self.scene = self.view.scene()
        self.gviewLayout.addWidget(self.view)
        self.setupFonts()        
        
        # build the graph
        self.initializeGraphicsView()

        self.outputPlainTextEdit.setFont(self.fonts.get('output'))
        self.initializeRecentFilesMenu()
        self.buildWindowTitle()
        self.resetStatus()

    def setupFonts(self, font='SansSerif', size=9):
        """
        Initializes the fonts attribute
        """
        self.fonts = dict()
        self.fonts["ui"] = QtGui.QFont(font)
        self.fonts["ui"].setPointSize(size)

        self.fonts["output"] = QtGui.QFont('Monospace')
        self.fonts["output"].setPointSize(size)

    def initializeGraphicsView(self, filter=False):
        """
        Initialize the graphics view and graph object.
        """
        # scene view signals
        self.scene.nodeAdded.connect(self.nodeAddedAction)
        self.scene.nodeChanged.connect(self.nodeChangedAction)
        self.scene.changed.connect(self.sceneChangedAction)

        # initialize the Graph
        self.graph = core.Graph(viewport=self.view)
        self.network = self.graph.network.graph

        self.scene.setNodeManager(self.graph)
        self.view.setSceneRect(-5000, -5000, 10000, 10000)

        # graphics View
        self.view.wheelEvent = self.graphicsView_wheelEvent
        self.view.resizeEvent = self.graphicsView_resizeEvent

        # maya online
        self.view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60, 255), QtCore.Qt.SolidPattern))

        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # TESTING: disable
        self.scene.selectionChanged.connect(self.nodesSelectedAction)

    def connectSignals(self):
        """
        Setup signals & slots.
        """
        self.timer.timeout.connect(self.resetStatus)
        self.view.tabPressed.connect(partial(self.createTabMenu, self.view))
        self.view.statusEvent.connect(self.updateConsole)

        # file menu
        self.menu_file.aboutToShow.connect(self.initializeFileMenu)
        self.action_save_graph_as.triggered.connect(self.saveGraphAs)
        self.action_save_graph.triggered.connect(self.saveCurrentGraph)
        self.action_read_graph.triggered.connect(self.readGraph)
        self.action_clear_graph.triggered.connect(self.resetGraph)
        self.action_reset_scale.triggered.connect(self.resetScale)
        self.action_reset_ui.triggered.connect(self.resetUI)
        self.action_exit.triggered.connect(self.close)

        current_pos = QtGui.QCursor().pos()
        pos_x = current_pos.x()
        pos_y = current_pos.y()
        self.action_add_default.triggered.connect(partial(self.graph.addNode, 'default', pos_x=QtGui.QCursor().pos().x(), pos_y=QtGui.QCursor().pos().y()))

        # output tab buttons
        self.tabWidget.currentChanged.connect(self.updateOutput)
        self.button_refresh.clicked.connect(self.updateOutput)
        self.button_clear.clicked.connect(self.outputPlainTextEdit.clear)

    def initializeFileMenu(self):
        """
        Setup the file menu before it is drawn.
        """
        current_scene = self.graph.getScene()
        if not current_scene:
            self.action_save_graph.setEnabled(False)
        self.initializeRecentFilesMenu()

    def initializeRecentFilesMenu(self):
        """
        Build a menu of recently opened scenes.
        """
        recent_files = dict()
        recent_files = self.qtsettings.getRecentFiles()
        self.menu_recent_files.clear()
        self.menu_recent_files.setEnabled(False)
        if recent_files:
            # Recent files menu
            for filename in reversed(recent_files):
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
        if level == 'info':
            self.statusBar().showMessage(self._getInfoStatus(val))
            log.info(val)
        if level == 'error':
            self.statusBar().showMessage(self._getErrorStatus(val))
            log.error(val)
        if level == 'warning':
            self.statusBar().showMessage(self._getWarningStatus(val))
            log.warning(val)
        self.timer.start(4000)        

    def resetStatus(self):
        """
        Reset the status bar message.
        """
        self.statusBar().showMessage('[SceneGraph]: ready')

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
            filename, filters = QtGui.QFileDialog.getSaveFileName(self, "Save graph file", 
                                                                os.path.join(os.getenv('HOME'), 'my_graph.json'), 
                                                                "JSON files (*.json)")
            basename, fext = os.path.splitext(filename)
            if not fext:
                filename = '%s.json' % basename


        filename = str(os.path.normpath(filename))
        self.updateStatus('saving current graph "%s"' % filename)

        # update the graph attributes
        #root_node.addNodeAttributes(**{'sceneName':filename})

        self.graph.write(filename)
        self.action_save_graph.setEnabled(True)
        self.buildWindowTitle()

        self.graph.setScene(filename)
        self.qtsettings.addRecentFile(filename)
        self.initializeRecentFilesMenu()
        self.buildWindowTitle()

    # TODO: figure out why this has to be a separate method from saveGraphAs
    def saveCurrentGraph(self):
        """
        Save the current graph file
        """
        if not self.graph.getScene():
            return

        self.updateStatus('saving current graph "%s"' % self.graph.getScene())
        self.graph.write(self.graph.getScene())
        self.buildWindowTitle()

        self.qtsettings.addRecentFile(self.graph.getScene())
        self.initializeRecentFilesMenu()
        return self.graph.getScene()      

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
        self.qtsettings.addRecentFile(filename)
        self.buildWindowTitle()

    # TODO: combine this with readGraph
    def readRecentGraph(self, filename):
        self.resetGraph()
        self.graph.reset()
        self.updateStatus('reading graph "%s"' % filename)
        self.graph.read(filename)
        self.action_save_graph.setEnabled(True)
        self.graph.setScene(filename)
        self.qtsettings.addRecentFile(filename)
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

    def resetUI(self):
        """
        Attempts to restore docks and window to factory fresh state.
        """
        self.qtsettings.clear()
        self.setupUi(self)
        self.initializeUI()

    def sizeHint(self):
        return QtCore.QSize(1070, 800)

    def removeDetailWidgets(self):
        """
        Remove a widget from the detailGroup box.
        """
        for i in reversed(range(self.attributeScrollAreaLayout.count())):
            widget = self.attributeScrollAreaLayout.takeAt(i).widget()
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
            if hasattr(node, 'node_class'):
                if node.node_class in ['dagnode']:                
                    nodeAttrWidget = ui.AttributeEditor(self.attrEditorWidget, manager=self.scene.graph, gui=self)
                    nodeAttrWidget.setNode(node)
                    self.attributeScrollAreaLayout.addWidget(nodeAttrWidget)

    def nodeAddedAction(self, node):
        """
        Action whenever a node is added to the graph.
        """
        self.updateOutput()

    def nodeChangedAction(self, node):
        """
        node = NodeWidget
        """
        print '# SceneGraph: Node changed...'
        self.updateOutput()

    # TODO: disabling this, causing lag
    def sceneChangedAction(self, event):
        #self.nodesSelectedAction()
        self.updateNodes()
    
    def createCreateMenuActions(self):
        pass
    
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
        tab_menu = QtGui.QMenu(parent)
        tab_menu.clear()
        add_action = tab_menu.addAction('Add default node')        
        qcurs = QtGui.QCursor()
        view_pos =  self.view.current_cursor_pos
        scene_pos = self.view.mapToScene(view_pos)
        add_action.triggered.connect(partial(self.graph.addNode, node_type='default', pos_x=scene_pos.x(), pos_y=scene_pos.y()))
        tab_menu.exec_(qcurs.pos())

    def initializeViewContextMenu(self):
        """
        Initialize the GraphicsView context menu.
        """
        menu_actions = []
        menu_actions.append(QtGui.QAction('Rename node', self, triggered=self.renameNodeAction))
        return menu_actions

    def renameNodeAction(self, node):
        print 'renaming node...'


    #- Settings -----
    def readSettings(self):
        """
        Read Qt settings from file
        """
        self.qtsettings.beginGroup('MainWindow')
        self.resize(self.qtsettings.value("size", QtCore.QSize(400, 256)))
        self.move(self.qtsettings.value("pos", QtCore.QPoint(200, 200)))

        if 'windowState' in self.qtsettings.childKeys():
            self.restoreState(self.qtsettings.value("windowState"))

        self.qtsettings.endGroup()

    def writeSettings(self):
        """
        Write Qt settings to file
        """
        self.qtsettings.beginGroup('MainWindow')
        width = self.width()
        height = self.height()
        self.qtsettings.setValue("size", QtCore.QSize(width, height))
        self.qtsettings.setValue("pos", self.pos())
        self.qtsettings.setValue("windowState", self.saveState())
        self.qtsettings.endGroup()

    def updateOutput(self):
        """
        Update the output text edit.
        """
        import networkx.readwrite.json_graph as nxj
        import simplejson as json
        self.updateNodes()

        # store the current position in the text box
        bar = self.outputPlainTextEdit.verticalScrollBar()
        posy = bar.value()

        self.outputPlainTextEdit.clear()
        #graph_data = nxj.adjacency_data(self.graph.network)
        graph_data = nxj.node_link_data(self.graph.network)
        self.outputPlainTextEdit.setPlainText(json.dumps(graph_data, indent=5))
        self.outputPlainTextEdit.setFont(self.fonts.get('output'))

        self.outputPlainTextEdit.scrollContentsBy(0, posy)

    def updateConsole(self, status):
        """
        Update the console data.

        params:
            data - (dict) data from GraphicsView mouseMoveEvent

        """        
        self.sceneRectLineEdit.clear()
        self.viewRectLineEdit.clear()
        self.zoomLevelLineEdit.clear()

        if status.get('cursor_x'):
            self.cursorXLineEdit.clear()
            self.cursorXLineEdit.setText(str(status.get('cursor_x')))

        if status.get('cursor_y'):
            self.cursorYLineEdit.clear()
            self.cursorYLineEdit.setText(str(status.get('cursor_y')))

        if status.get('cursor_sx'):
            self.sceneCursorXLineEdit.clear()
            self.sceneCursorXLineEdit.setText(str(status.get('cursor_sx')))

        if status.get('cursor_sy'):
            self.sceneCursorYLineEdit.clear()
            self.sceneCursorYLineEdit.setText(str(status.get('cursor_sy')))

        scene_str = '%s, %s' % (status.get('scene_rect')[0], status.get('scene_rect')[1])
        self.sceneRectLineEdit.setText(scene_str)

        view_str = '%s, %s' % (status.get('view_size')[0], status.get('view_size')[1])
        self.viewRectLineEdit.setText(view_str)

        zoom_str = '%s' % status.get('zoom_level')[0]
        self.zoomLevelLineEdit.setText(zoom_str)

    # TODO: this is in Graph.updateGraph
    def updateNodes(self):
        """
        Update the networkx graph with current node values.
        """
        if self.scene.sceneNodes:
            for node in self.scene.sceneNodes.values():
                try:
                    self.graph.network.node[str(node.UUID)]['name']=node.dagnode.name

                    # update widget attributes
                    self.graph.network.node[str(node.UUID)]['pos_x']=node.pos().x()
                    self.graph.network.node[str(node.UUID)]['pos_y']=node.pos().y()
                    self.graph.network.node[str(node.UUID)]['width']=node.width
                    self.graph.network.node[str(node.UUID)]['height']=node.height
                    self.graph.network.node[str(node.UUID)]['expanded']=node.expanded

                    # update arbitrary attributes
                    self.graph.network.node[str(node.UUID)].update(**node.dagnode.getNodeAttributes())
                except:
                    pass


class Settings(QtCore.QSettings):
    def __init__(self, filename, frmt, parent=None, max_files=10):
        QtCore.QSettings.__init__(self, filename, frmt, parent)

        self._max_files     = max_files
        self._parent        = parent
        self._initialize()

    def _initialize(self):
        if 'RecentFiles' not in self.childGroups():
            self.beginWriteArray('RecentFiles', 0)
            self.endArray()

    def save(self, state='default'):
        self.beginGroup("Mainwindow/%s" % state)
        self.setValue("size", QtCore.QSize(self._parent.width(), self._parent.height()))
        self.setValue("pos", self._parent.pos())
        self.setValue("windowState", self._parent.saveState())
        self.endGroup()

    def load(self, state='default'):
        pass

    def getRecentFiles(self):
        """
        Get a tuple of the most recent files.
        """
        recent_files = []
        cnt = self.beginReadArray('RecentFiles')
        for i in range(cnt):
            self.setArrayIndex(i)
            fn = self.value('file')
            recent_files.append(fn)
        self.endArray()
        return tuple(recent_files)

    def addRecentFile(self, filename):
        """
        Adds a recent file to the stack.
        """
        recent_files = self.getRecentFiles()
        if filename in recent_files:
            recent_files = tuple(x for x in recent_files if x != filename)

        recent_files = recent_files + (filename,)
        self.beginWriteArray('RecentFiles')
        for i in range(len(recent_files)):
            self.setArrayIndex(i)
            self.setValue('file', recent_files[i])
        self.endArray()


class MouseEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # call a function here..
            # obj.doSomething()
            return True
        return QtGui.QMainWindow.eventFilter(self, obj, event)

