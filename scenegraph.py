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
reload(ui)


log = core.log
global SCENEGRAPH_DEBUG
SCENEGRAPH_UI = options.SCENEGRAPH_UI
SCENEGRAPH_DEBUG = os.getenv('SCENEGRAPH_DEBUG', '0')


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

        self.environment      = kwargs.get('env', 'standalone')  
        self._startdir        = kwargs.get('start', os.getenv('HOME'))
        self.timer            = QtCore.QTimer()

        # temp file
        self.temp_scene       = os.path.join(os.getenv('TMPDIR'), 'scenegraph_temp.json') 

        # stash temp selections here
        self._selected_nodes  = []

        # undo stack
        self.undo_stack       = QtGui.QUndoStack(self)

        # preferences
        self.settings_file    = os.path.join(options.SCENEGRAPH_PREFS_PATH, 'SceneGraph.ini')
        self.qtsettings       = Settings(self.settings_file, QtCore.QSettings.IniFormat, parent=self)
        self.qtsettings.setFallbacksEnabled(False)

        # icon
        self.setWindowIcon(QtGui.QIcon(os.path.join(options.SCENEGRAPH_ICON_PATH, 'graph_icon.png')))

        # stylesheet
        self.stylesheet = os.path.join(options.SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

        # item view/model
        self.tableView = ui.TableView(self.sceneWidgetContents)
        self.sceneScrollAreaLayout.addWidget(self.tableView)
        self.tableModel = ui.GraphTableModel(headers=['Node Type', 'Node'])
        self.tableView.setModel(self.tableModel)
        self.tableSelectionModel = self.tableView.selectionModel()

        self.nodesModel = ui.NodesListModel()
        self.nodeStatsList.setModel(self.nodesModel)
        self.nodeListSelModel = self.nodeStatsList.selectionModel()

        self.edgesModel = ui.EdgesListModel()
        self.edgeStatsList.setModel(self.edgesModel)
        self.edgeListSelModel = self.edgeStatsList.selectionModel()

        self.initializeUI()
        self.readSettings()       
        self.connectSignals()

        self.resetStatus()
        #QtGui.QApplication.instance().installEventFilter(self)
        self.draw_scene = QtGui.QGraphicsScene()
        self.draw_view.setScene(self.draw_scene)

        #QStream.stdout().messageWritten.connect(self.consoleOutput)
        #QStream.stderr().messageWritten.connect(self.consoleOutput)

    def eventFilter(self, obj, event):
        """
        Install an event filter to filter key presses away from the parent.
        """        
        if event.type() == QtCore.QEvent.KeyPress:
            #if event.key() == QtCore.Qt.Key_Delete:
            if self.hasFocus():
                return True
            return False
        else:
            return super(SceneGraphUI, self).eventFilter(obj, event)

    def initializeUI(self):
        """
        Set up the main UI
        """
        # add our custom GraphicsView object
        self.view = ui.GraphicsView(self.gview, ui=self)
        self.scene = self.view.scene
        self.gviewLayout.addWidget(self.view)
        self.setupFonts()        
        
        # build the graph
        self.initializeGraphicsView()

        self.outputTextBrowser.setFont(self.fonts.get('output'))
        self.initializeRecentFilesMenu()
        self.buildWindowTitle()
        self.resetStatus()

        # remove the Draw tab
        #self.tabWidget.removeTab(2)

        # setup undo/redo
        undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcuts(QtGui.QKeySequence.Undo)
        redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcuts(QtGui.QKeySequence.Redo)

        self.menu_edit.addAction(undo_action)
        self.menu_edit.addAction(redo_action)

        self.initializeNodesMenu()

        # validators for console widget
        self.scene_posx.setValidator(QtGui.QDoubleValidator(-5000, 10000, 2, self.scene_posx))
        self.scene_posy.setValidator(QtGui.QDoubleValidator(-5000, 10000, 2, self.scene_posy))
        self.view_posx.setValidator(QtGui.QDoubleValidator(-5000, 10000, 2, self.view_posx))
        self.view_posy.setValidator(QtGui.QDoubleValidator(-5000, 10000, 2, self.view_posy))

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
        Initialize the graphics view/scen and graph objects.
        """
        # scene view signals
        self.scene.nodeAdded.connect(self.nodeAddedAction)
        self.scene.nodeChanged.connect(self.nodeChangedAction)
        self.scene.changed.connect(self.sceneChangedAction)

        # initialize the Graph
        self.graph = core.Graph(viewport=self.view)
        self.network = self.graph.network
        self.network.graph['environment'] = self.environment

        self.scene.setGraph(self.graph)
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

        # file & ui menu
        self.menu_file.aboutToShow.connect(self.initializeFileMenu)
        self.menu_graph.aboutToShow.connect(self.initializeGraphMenu)
        self.menu_ui.aboutToShow.connect(self.initializeUIMenu)

        self.action_save_graph_as.triggered.connect(self.saveGraphAs)
        self.action_save_graph.triggered.connect(self.saveCurrentGraph)
        self.action_read_graph.triggered.connect(self.readGraph)
        self.action_revert.triggered.connect(self.revertGraph)
        self.action_clear_graph.triggered.connect(self.resetGraph)
        self.action_draw_graph.triggered.connect(self.refreshGraph)
        self.action_evaluate.triggered.connect(self.graph.evaluate)
        self.action_reset_scale.triggered.connect(self.resetScale)
        self.action_reset_ui.triggered.connect(self.restoreDefaultSettings)
        self.action_exit.triggered.connect(self.close)

        self.action_debug_mode.triggered.connect(self.toggleDebug)
        self.action_edge_type.triggered.connect(self.toggleEdgeTypes)

        current_pos = QtGui.QCursor().pos()
        pos_x = current_pos.x()
        pos_y = current_pos.y()

        # output tab buttons
        self.tabWidget.currentChanged.connect(self.updateOutput)
        self.button_refresh.clicked.connect(self.updateOutput)
        self.button_clear.clicked.connect(self.outputTextBrowser.clear)
        self.button_update_draw.clicked.connect(self.updateDrawTab)
        self.consoleTabWidget.currentChanged.connect(self.updateStats)

        # table view
        self.tableSelectionModel.selectionChanged.connect(self.tableSelectionChangedAction)
        self.nodeListSelModel.selectionChanged.connect(self.nodesModelChangedAction)
        self.edgeListSelModel.selectionChanged.connect(self.edgesModelChangedAction)

    def initializeFileMenu(self):
        """
        Setup the file menu before it is drawn.
        """
        current_scene = self.graph.getScene()
        if not current_scene:
            self.action_save_graph.setEnabled(False)
            self.action_revert.setEnabled(False)

        # create the recent files menu
        self.initializeRecentFilesMenu()

    def initializeGraphMenu(self):
        """
        Setup the graph menu before it is drawn.
        """
        edge_type = 'bezier'
        if self.scene.edge_type == 'bezier':
            edge_type = 'polygon'
        self.action_edge_type.setText('%s lines' % edge_type.title())

    def initializeNodesMenu(self):
        """
        Build a context menu at the current pointer pos.
        """
        for node in self.graph.node_types():
            node_action = self.menu_add_node.addAction(node)
            # add the node at the scene pos
            node_action.triggered.connect(partial(self.graph.addNode, node_type=node))

    def initializeUIMenu(self):
        """
        Setup the ui menu before it is drawn.
        """
        global SCENEGRAPH_DEBUG
        db_label = 'Debug on'
        if SCENEGRAPH_DEBUG == '1':
            db_label = 'Debug off'
        self.action_debug_mode.setText(db_label)

    def initializeRecentFilesMenu(self):
        """
        Build a menu of recently opened scenes.
        """
        recent_files = self.qtsettings.getRecentFiles()
        self.menu_recent_files.clear()
        self.menu_recent_files.setEnabled(False)
        if recent_files:
            i = 0
            # Recent files menu
            for filename in reversed(recent_files):
                if filename:
                    if i < self.qtsettings._max_files:
                        file_action = QtGui.QAction(filename, self.menu_recent_files)
                        file_action.triggered.connect(partial(self.readRecentGraph, filename))
                        self.menu_recent_files.addAction(file_action)
                        i+=1
            self.menu_recent_files.setEnabled(True)

    def buildWindowTitle(self):
        """
        Build the window title
        """
        title_str = 'Scene Graph'
        if self.graph.getScene():
            title_str = '%s - %s' % (title_str, self.graph.getScene())
        self.setWindowTitle(title_str)

    def sizeHint(self):
        return QtCore.QSize(800, 675)

    #- Status & Messaging ------
    def consoleOutput(self, msg):
        print 'message: ', msg

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
        self.action_revert.setEnabled(True)
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

    def saveTempFile(self):
        """
        Save a temp file when the graph changes.
        """
        temp_scene = self.temp_scene
        if 'temp_scene' not in self.graph.network.graph:
            self.graph.network.graph['temp_scene'] = self.temp_scene
        self.graph.write(temp_scene)
        return temp_scene

    def readGraph(self, filename=None):
        """
        Read the current graph from a json file
        """
        if filename is None:
            filename, ok = QtGui.QFileDialog.getOpenFileName(self, "Open graph file", self._startdir, "JSON files (*.json)")
            if filename == "":
                return

        if not os.path.exists(filename):
            log.error('filename %s does not exist' % filename)
            return

        self.resetGraph()
        self.updateStatus('reading graph "%s"' % filename)
        self.graph.read(filename)
        self.action_save_graph.setEnabled(True)

        if filename != self.temp_scene:
            self.graph.setScene(filename)
            self.qtsettings.addRecentFile(filename)
            log.debug('adding recent file: "%s"' % filename)
        self.buildWindowTitle()
        self.scene.clearSelection()

    # TODO: combine this with readGraph
    def readRecentGraph(self, filename):
        if not os.path.exists(filename):
            log.error('file %s does not exist' % filename)
            return

        self.resetGraph()
        self.updateStatus('reading graph "%s"' % filename)
        self.graph.read(filename)
        self.action_save_graph.setEnabled(True)
        self.graph.setScene(filename)
        self.qtsettings.addRecentFile(filename)
        self.buildWindowTitle()
        self.scene.clearSelection()

    def revertGraph(self):
        """
        Revert the current graph file.
        """
        filename=self.graph.getScene()
        if filename:
            self.resetGraph()
            self.readGraph(filename)
            log.info('reverting graph: %s' % filename)

    def resetGraph(self):
        """
        Reset the current graph
        """
        self.scene.clear()
        self.graph.reset()
        self.action_save_graph.setEnabled(False)
        self.buildWindowTitle()
        self.updateOutput()

    def resetScale(self):
        self.view.resetMatrix()      

    def toggleDebug(self):
        """
        Set the debug environment variable.
        """
        global SCENEGRAPH_DEBUG
        val = '0'
        if SCENEGRAPH_DEBUG == '0':
            val = '1'
        os.environ["SCENEGRAPH_DEBUG"] = val
        SCENEGRAPH_DEBUG = val
        self.scene.update()      

    def toggleEdgeTypes(self):
        """
        Toggle the edge types.
        """
        if self.scene.edge_type == 'bezier':
            self.scene.edge_type = 'polygon'

        elif self.scene.edge_type == 'polygon':
            self.scene.edge_type = 'bezier'
        self.scene.update()

    #- ACTIONS ----
    def nodesSelectedAction(self):
        """
        Action that runs whenever a node is selected in the UI
        """
        nodes = self.scene.selectedItems()

        # clear the list view
        self.tableModel.clear()
        self.tableView.reset()
        self.tableView.setHidden(True)  
        if nodes:
            if len(nodes) == 1:                
                node = nodes[0]

                if node not in self._selected_nodes:
                    self._selected_nodes = nodes


                    if hasattr(node, 'node_class'):
                        if node.node_class in ['dagnode']:
                            self.updateAttributeEditor(node.dagnode)
                            UUID = node.dagnode.UUID
                            if UUID:
                                ds_ids = self.scene.graph.downstream(node.dagnode.name)
                                dagnodes = []
                                for nid in ds_ids:
                                    dagnode = self.scene.graph.getDagNode(UUID=nid)
                                    if dagnode:
                                        dagnodes.append(dagnode)

                                dagnodes = [x for x in reversed(dagnodes)]
                                self.tableModel.addNodes(dagnodes)
                                self.tableView.setHidden(False)
                                self.tableView.resizeRowToContents(0)
                                self.tableView.resizeRowToContents(1)
            else:
                self.removeAttributeEditorWidget()
        else:
            self._selected_nodes = []
            self.removeAttributeEditorWidget()

    def getAttributeEditorWidget(self):
        return self.attrEditorWidget.findChild(QtGui.QWidget, 'AttributeEditor')

    def removeAttributeEditorWidget(self):
        """
        Remove a widget from the detailGroup box.
        """
        for i in reversed(range(self.attributeScrollAreaLayout.count())):
            widget = self.attributeScrollAreaLayout.takeAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def updateAttributeEditor(self, nodes, **attrs):
        """
        Update the attribute editor with a selected node.
        """
        if type(nodes) not in [list, tuple]:
            nodes = [nodes,]

        for node in nodes:
            if hasattr(node, 'Type'):
                if node.Type == 65539:
                    attr_widget = self.getAttributeEditorWidget()
                    
                    if not attr_widget:
                        attr_widget = ui.AttributeEditor(self.attrEditorWidget, manager=self.scene.graph, gui=self)                
                        self.attributeScrollAreaLayout.addWidget(attr_widget)
                    attr_widget.setNode(node)

    def tableSelectionChangedAction(self):
        """
        Update the attribute editor when a node is selected in the graph list.
        """
        if self.tableSelectionModel.selectedRows():
            idx = self.tableSelectionModel.selectedRows()[0]
            dagnode = self.tableModel.nodes[idx.row()]
            self.updateAttributeEditor(dagnode)

    def nodesModelChangedAction(self):
        self.scene.clearSelection()
        if self.nodeListSelModel.selectedRows():
            idx = self.nodeListSelModel.selectedRows()[0]
            node = self.nodesModel.nodes[idx.row()]
            node.setSelected(True)

    def edgesModelChangedAction(self):
        self.scene.clearSelection()
        if self.edgeListSelModel.selectedRows():
            idx = self.edgeListSelModel.selectedRows()[0]

            edge = self.edgesModel.edges[idx.row()]
            edge.setSelected(True)

    def nodeAddedAction(self, node):
        """
        Action whenever a node is added to the graph.
        """
        self.updateOutput()

    def nodeChangedAction(self, node):
        """
        node = NodeWidget
        """
        selected_nodes = self.scene.selectedNodes()
        if selected_nodes:
            # only update the attribute editor if
            # one node is selected
            if len(selected_nodes) == 1:
                self.updateAttributeEditor(node.dagnode)
        self.updateOutput()
        self.saveTempFile()

    # TODO: disabling this, causing lag
    def sceneChangedAction(self, event):
        pass
    
    def createCreateMenuActions(self):
        pass
    
    #- Events ----
    def closeEvent(self, event):
        """
        Write window prefs when UI is closed
        """
        self.writeSettings()
        QtGui.QApplication.instance().removeEventFilter(self)
        return super(SceneGraphUI, self).closeEvent(event)

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
        add_menu = QtGui.QMenu('Add node:')

        qcurs = QtGui.QCursor()
        view_pos =  self.view.current_cursor_pos
        scene_pos = self.view.mapToScene(view_pos)

        for node in self.graph.node_types():
            node_action = add_menu.addAction(node)
            # add the node at the scene pos
            node_action.triggered.connect(partial(self.graph.addNode, node_type=node, pos_x=scene_pos.x(), pos_y=scene_pos.y()))

        # haxx: stylesheet should work here
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        add_menu.setStyleSheet(str(ssf.readAll()))
        tab_menu.setStyleSheet(str(ssf.readAll()))

        tab_menu.addMenu(add_menu)
        tab_menu.exec_(qcurs.pos())

    def initializeViewContextMenu(self):
        """
        Initialize the GraphicsView context menu.
        """
        menu_actions = []
        menu_actions.append(QtGui.QAction('Rename node', self, triggered=self.renameNodeAction))
        return menu_actions

    def renameNodeAction(self):
        print 'renaming node...'

    def spinAction(self):
        self.timer.timeout.connect(self.rotateView)
        self.timer.start(90)

    def rotateView(self):
        self.view.rotate(4)

    #- Settings -----
    def readSettings(self):
        """
        Read Qt settings from file
        """
        self.qtsettings.beginGroup("MainWindow")
        self.restoreGeometry(self.qtsettings.value("geometry"))
        self.restoreState(self.qtsettings.value("windowState"))
        self.qtsettings.endGroup()

        # read the dock settings
        for w in self.findChildren(QtGui.QDockWidget):
            dock_name = w.objectName()
            self.qtsettings.beginGroup(dock_name)
            if "geometry" in self.qtsettings.childKeys():
                w.restoreGeometry(self.qtsettings.value("geometry"))
            self.qtsettings.endGroup()

    def writeSettings(self):
        """
        Write Qt settings to file
        """
        self.qtsettings.beginGroup('MainWindow')
        width = self.width()
        height = self.height()
        self.qtsettings.setValue("geometry", self.saveGeometry())
        self.qtsettings.setValue("windowState", self.saveState())
        self.qtsettings.endGroup()

        # write the dock settings
        for w in self.findChildren(QtGui.QDockWidget):
            dock_name = w.objectName()
            no_default = False
            # this is the first launch
            if dock_name not in self.qtsettings.childGroups():
                no_default = True

            self.qtsettings.beginGroup(dock_name)
            # save defaults
            if no_default:
                self.qtsettings.setValue("geometry/default", w.saveGeometry())
            self.qtsettings.setValue("geometry", w.saveGeometry())
            self.qtsettings.endGroup()

    def restoreDefaultSettings(self):
        """
        Attempts to restore docks and window to factory fresh state.
        """
        pos = self.pos()
        # read the mainwindow defaults
        main_geo_key = 'MainWindow/geometry/default'
        main_state_key = 'MainWindow/windowState/default'
        
        self.restoreGeometry(self.qtsettings.value(main_geo_key))
        self.restoreState(self.qtsettings.value(main_state_key))
        
        for w in self.findChildren(QtGui.QDockWidget):
            dock_name = w.objectName()

            defaults_key = '%s/geometry/default' % dock_name
            if defaults_key in self.qtsettings.allKeys():
                w.restoreGeometry(self.qtsettings.value(defaults_key))
        self.move(pos)

    def updateOutput(self):
        """
        Update the output text edit.
        """
        import networkx.readwrite.json_graph as nxj
        
        # store the current position in the text box
        bar = self.outputTextBrowser.verticalScrollBar()
        posy = bar.value()

        self.outputTextBrowser.clear()
        #graph_data = nxj.adjacency_data(self.graph.network)
        graph_data = nxj.node_link_data(self.graph.network)
        html_data = self.formatOutputHtml(graph_data)
        self.outputTextBrowser.setHtml(html_data)
        self.outputTextBrowser.setFont(self.fonts.get('output'))

        self.outputTextBrowser.scrollContentsBy(0, posy)
        self.outputTextBrowser.setReadOnly(True)

    def updateDrawTab(self, filename=None):
        """
        Generate an image of the current graph and update the scene.
        """
        # draw tab
        draw_file = self.drawGraph(filename)
        self.draw_scene.clear()
        pxmap = QtGui.QPixmap(draw_file)
        self.draw_scene.addPixmap(pxmap)

    def formatOutputHtml(self, data):
        """
        Fast and dirty html formatting.
        """
        import simplejson as json
        html_result = ""
        rawdata = json.dumps(data, indent=5)
        for line in rawdata.split('\n'):
            if line:
                ind = "&nbsp;"*line.count(" ")
                fline = "<br>%s%s</br>" % (ind, line)
                if '"name":' in line:
                    fline = '<br><b><font color="#628fab">%s%s</font></b></br>' % (ind, line)
                html_result += fline
        return html_result

    def updateConsole(self, status):
        """
        Update the console data.

        params:
            status - (dict) data from GraphicsView mouseMoveEvent

        """        
        self.sceneRectLineEdit.clear()
        self.viewRectLineEdit.clear()
        self.zoomLevelLineEdit.clear()

        if status.get('view_cursor'):
            vx, vy = status.get('view_cursor', (0.0,0.0))
            self.view_posx.clear()
            self.view_posy.clear()
            self.view_posx.setText('%.2f' % vx)
            self.view_posy.setText('%.2f' % vy)

        if status.get('scene_cursor'):
            sx, sy = status.get('scene_cursor', (0.0,0.0))
            self.scene_posx.clear()
            self.scene_posy.clear()
            self.scene_posx.setText('%.2f' % sx)
            self.scene_posy.setText('%.2f' % sy)

        if status.get('scene_pos'):
            spx, spy = status.get('scene_pos', (0.0,0.0))
            self.scene_posx1.clear()
            self.scene_posy1.clear()
            self.scene_posx1.setText('%.2f' % spx)
            self.scene_posy1.setText('%.2f' % spy)

        scene_str = '%s, %s' % (status.get('scene_size')[0], status.get('scene_size')[1])
        self.sceneRectLineEdit.setText(scene_str)

        view_str = '%s, %s' % (status.get('view_size')[0], status.get('view_size')[1])
        self.viewRectLineEdit.setText(view_str)

        zoom_str = '%.3f' % status.get('zoom_level')[0]
        self.zoomLevelLineEdit.setText(zoom_str)

    def updateStats(self):
        """
        Update the console stats lists.
        """
        self.nodesModel.clear()
        self.edgesModel.clear()

        nodes = self.graph.getSceneNodes()
        edges = self.graph.getSceneEdges()

        self.nodesModel.addNodes(nodes)
        self.edgesModel.addEdges(edges)

        self.nodeStatsLabel.setText('Nodes: (%d)' % len(nodes))
        self.edgeStatsLabel.setText('Edges: (%d)' % len(edges))


    def refreshGraph(self):
        self.graph.evaluate()
        self.scene.update()

    def drawGraph(self, filename=None):
        """
        Output the network as a png image.

        See: http://networkx.github.io/documentation/latest/reference/generated/networkx.drawing.nx_pylab.draw_networkx_nodes.html
        """
        if filename is None:
            filename = os.path.join(os.getenv('TMPDIR'), 'my_graph.png')

        import networkx as nx
        import matplotlib.pyplot as plt
        
        # spring_layout
        pos=nx.spring_layout(self.network, iterations=20)

        node_labels = dict()
        for node in self.network.nodes(data=True):
            nid, node_attrs = node
            node_labels[nid]=node_attrs.get('name')

        node_color = '#b4b4b4'

        nx.draw_networkx_edges(self.network,pos, alpha=0.3,width=1, edge_color='black')
        nx.draw_networkx_nodes(self.network,pos, node_size=600, node_color=node_color,alpha=1.0, node_shape='s')
        nx.draw_networkx_edges(self.network,pos, alpha=0.4,node_size=0,width=1,edge_color='k')
        nx.draw_networkx_labels(self.network,pos, node_labels, fontsize=10)

        if os.path.exists(filename):
            os.remove(filename)

        plt.savefig(filename)
        log.info('saving graph image "%s"' % filename)
        return filename

    #- Dialogs -----
    def confirmDialog(self, msg):
        """
        Returns true if dialog 'yes' button is pressed.
        """
        result = QtGui.QMessageBox.question(self, "Comfirm", msg, QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if (result == QtGui.QMessageBox.Yes):
            return True
        return False



class Settings(QtCore.QSettings):

    def __init__(self, filename, frmt=QtCore.QSettings.IniFormat, parent=None, max_files=10):
        QtCore.QSettings.__init__(self, filename, frmt, parent)

        self._max_files     = max_files
        self._parent        = parent
        self._initialize()

    def _initialize(self):
        """
        Setup the file for the first time.
        """
        if 'MainWindow' not in self.childGroups():
            if self._parent is not None:
                self.setValue('MainWindow/geometry/default', self._parent.saveGeometry())
                self.setValue('MainWindow/windowState/default', self._parent.saveState())

        if 'RecentFiles' not in self.childGroups():
            self.beginWriteArray('RecentFiles', 0)
            self.endArray()

    def save(self, key='default'):
        """
        Save, with optional category.

         * unused
        """
        self.beginGroup("Mainwindow/%s" % key)
        self.setValue("size", QtCore.QSize(self._parent.width(), self._parent.height()))
        self.setValue("pos", self._parent.pos())
        self.setValue("windowState", self._parent.saveState())
        self.endGroup()

    def load(self, key='default'):
        pass

    def deleteFile(self):
        log.info('deleting settings: "%s"' % self.fileName())
        return os.remove(self.fileName())

    @property
    def recent_files(self):
        """
        Returns a tuple of recent files, no larger than the max 
        and reversed (for usage in menus).

         * unused
        """
        files = self.getRecentFiles()
        tmp = []
        for f in reversed(files):
            tmp.append(f)
        return tuple(tmp[:self._max_files])

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

    def clearRecentFiles(self):
        self.remove('RecentFiles')
