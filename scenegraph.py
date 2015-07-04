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
        try:
            exec pyc in frame
        except:
            pass

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
        self.setDockNestingEnabled(True)
        #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.view             = None

        # preferences
        self.debug            = kwargs.get('debug', False)
        self.use_gl           = kwargs.get('opengl', False)

        self.edge_type        = 'bezier'
        self.viewport_mode    = 'smart'
        self.render_fx        = True
        self.antialiasing     = 2
        self.environment      = kwargs.get('env', 'standalone')

        self._startdir        = kwargs.get('start', os.getenv('HOME'))
        self.timer            = QtCore.QTimer()

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

        # item views/models
        self.tableView = ui.TableView(self.sceneWidgetContents)
        self.sceneScrollAreaLayout.addWidget(self.tableView)
        self.tableModel = ui.GraphTableModel(headers=['Node Type', 'Node'])
        self.tableView.setModel(self.tableModel)
        self.tableSelectionModel = self.tableView.selectionModel()

        # nodes list model
        self.nodesModel = ui.NodesListModel()
        self.nodeStatsList.setModel(self.nodesModel)
        self.nodeListSelModel = self.nodeStatsList.selectionModel()

        # edges list 
        self.edgesModel = ui.EdgesListModel()
        self.edgeStatsList.setModel(self.edgesModel)
        self.edgeListSelModel = self.edgeStatsList.selectionModel()

        self.readSettings()

        """
        print '# OpenGL mode:   ', self.use_gl
        print '# Edge type:     ', self.edge_type
        print '# Viewport mode: ', self.viewport_mode
        """

        self.initializeUI()              
        self.connectSignals()

        self.resetStatus()        
        self.draw_scene = QtGui.QGraphicsScene()
        self.draw_view.setScene(self.draw_scene)
        self.initializeStylesheet()
        #QtGui.QApplication.instance().installEventFilter(self)

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
        self.initializePreferencesUI()
        # build the graph
        self.initializeGraphicsView()

        self.outputTextBrowser.setFont(self.fonts.get('output'))
        self.initializeRecentFilesMenu()
        self.buildWindowTitle()
        self.resetStatus()

        # remove the Draw tab
        self.tabWidget.removeTab(2)

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
        self.toggleDebug()
        self.setFont(self.fonts.get("ui"))

    def initializeStylesheet(self):
        """
        Setup the stylehsheet.
        """
        self.stylesheet = os.path.join(options.SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

    def setupFonts(self, font='SansSerif', size=9):
        """
        Initializes the fonts attribute
        """
        family = 'Consolas'
        if options.PLATFORM == 'MacOSX':
            size = 11
            family = 'Menlo'

        self.fonts = dict()
        self.fonts["ui"] = QtGui.QFont(font)
        #self.fonts["ui"].setFamily(family)
        self.fonts["ui"].setPointSize(size)

        self.fonts["output"] = QtGui.QFont('Monospace')
        self.fonts["output"].setPointSize(size)

    def initializeGraphicsView(self, filter=False):
        """
        Initialize the graphics view/scen and graph objects.
        """
        # initialize the Graph
        self.graph = core.Graph()
        self.network = self.graph.network
        

        # add our custom GraphicsView object (gview is defined in the ui file)
        self.view = ui.GraphicsView(self.gview, ui=self, opengl=self.use_gl, edge_type=self.edge_type)
        self.gviewLayout.addWidget(self.view) 

        self.setupFonts()
        self.view.setSceneRect(-5000, -5000, 10000, 10000)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.network.graph['environment'] = self.environment
        
    def connectSignals(self):
        """
        Setup signals & slots.
        """
        self.timer.timeout.connect(self.resetStatus)
        self.view.tabPressed.connect(partial(self.createTabMenu, self.view))
        self.view.statusEvent.connect(self.updateConsole)

        # Scene handler
        self.view.scene().handler.sceneNodesUpdated.connect(self.nodesChangedAction)
        self.view.selectionChanged.connect(self.nodesSelectedAction)

        # file & ui menu
        self.menu_file.aboutToShow.connect(self.initializeFileMenu)
        self.menu_graph.aboutToShow.connect(self.initializeGraphMenu)
        self.menu_window.aboutToShow.connect(self.initializeUIMenu)

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

        # preferences
        self.action_debug_mode.triggered.connect(self.toggleDebug)
        self.edge_type_menu.currentIndexChanged.connect(self.toggleEdgeTypes)
        self.viewport_mode_menu.currentIndexChanged.connect(self.toggleViewMode)
        self.check_use_gl.toggled.connect(self.toggleOpenGLMode)
        self.logging_level_menu.currentIndexChanged.connect(self.toggleLoggingLevel)
        self.check_render_fx.toggled.connect(self.toggleEffectsRendering)

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
        if self.view.scene().edge_type == 'bezier':
            edge_type = 'polygon'
        self.action_edge_type.setText('%s lines' % edge_type.title())

    def initializeNodesMenu(self):
        """
        Build a context menu at the current pointer pos.
        """
        for node in self.graph.node_types():
            node_action = self.menu_add_node.addAction(node)
            # add the node at the scene pos
            node_action.triggered.connect(partial(self.graph.add_node, node_type=node))

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

    def initializePreferencesUI(self):
        """
        Setup the preferences area.
        """
        edge_types = ['bezier', 'polygon']
        view_modes = dict(
                        full = 'QtGui.QGraphicsView.FullViewportUpdate',
                        smart = 'QtGui.QGraphicsView.SmartViewportUpdate',
                        minimal = 'QtGui.QGraphicsView.MinimalViewportUpdate'
                        )

        self.edge_type_menu.blockSignals(True)
        self.viewport_mode_menu.blockSignals(True)
        self.check_use_gl.blockSignals(True)
        self.logging_level_menu.blockSignals(True)
        self.check_render_fx.blockSignals(True)

        self.edge_type_menu.clear()
        self.viewport_mode_menu.clear()
        self.logging_level_menu.clear()

        # edge type menu
        self.edge_type_menu.addItems(edge_types)
        self.edge_type_menu.setCurrentIndex(self.edge_type_menu.findText(self.edge_type))

        # render FX
        self.check_render_fx.setChecked(self.render_fx)

        # build the viewport menu
        for item in view_modes.items():
            label, mode = item[0], item[1]
            self.viewport_mode_menu.addItem(label, str(mode))
        self.viewport_mode_menu.setCurrentIndex(self.viewport_mode_menu.findText(self.viewport_mode))

        # OpenGL check
        GL_MODE = self.use_gl
        if GL_MODE is None:
            GL_MODE = False

        self.check_use_gl.setChecked(GL_MODE)

        # logging level
        current_log_level = [x[0] for x in options.LOGGING_LEVELS.items() if x[1] == log.level][0]
        for item in options.LOGGING_LEVELS.items():
            label, mode = item[0], item[1]
            self.logging_level_menu.addItem(label.lower(), mode)            
        self.logging_level_menu.setCurrentIndex(self.logging_level_menu.findText(current_log_level.lower()))
    
        self.edge_type_menu.blockSignals(False)
        self.viewport_mode_menu.blockSignals(False)
        self.check_use_gl.blockSignals(False)
        self.logging_level_menu.blockSignals(False)
        self.check_render_fx.blockSignals(False)

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
        temp_scene = self.graph.temp_scene
        if 'autosave' not in self.graph.network.graph:
            self.graph.network.graph['autosave'] = self.graph.temp_scene
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

        if filename != self.graph.temp_scene:
            self.graph.setScene(filename)
            self.qtsettings.addRecentFile(filename)
            log.debug('adding recent file: "%s"' % filename)
        self.buildWindowTitle()
        self.view.scene().clearSelection()

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
        self.view.scene().clearSelection()

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
        self.view.scene().initialize()
        self.graph.reset()
        self.action_save_graph.setEnabled(False)
        self.buildWindowTitle()
        self.updateOutput()

    def resetScale(self):
        self.view.resetMatrix()      

    def toggleViewMode(self):
        """
        Update the GraphicsView update mode for performance.
        """
        mode = self.viewport_mode_menu.currentText()        
        qmode = self.viewport_mode_menu.itemData(self.viewport_mode_menu.currentIndex())
        self.view.viewport_mode = eval(qmode)
        self.view.scene().update()
        self.viewport_mode = mode

    def toggleOpenGLMode(self, val):
        """
        Toggle OpenGL mode and swap out viewports.
        """
        self.use_gl = val

        widget = self.view.viewport()
        widget.deleteLater()

        if self.use_gl:
            from PySide import QtOpenGL
            self.view.setViewport(QtOpenGL.QGLWidget())
            log.info('initializing OpenGL renderer.')
        else:
            self.view.setViewport(QtGui.QWidget())
        self.initializeStylesheet()
        self.view.scene().update()

    def toggleEffectsRendering(self, val):
        """
        Toggle rendering of node effects.

         * todo: this probably belongs in GraphicsView/Scene.
        """
        self.render_fx = val
        log.info('toggling effects %s' % ('on' if val else 'off'))
        for node in self.view.scene().scenenodes.values():
            if hasattr(node, '_render_effects'):
                node._render_effects = self.render_fx 
                node.update()
        self.view.scene().update()

    def toggleLoggingLevel(self):
        """
        Toggle the logging level.
        """
        log.level = self.logging_level_menu.itemData(self.logging_level_menu.currentIndex())        

    def toggleDebug(self):
        """
        Set the debug environment variable and set widget
        debug values to match.
        """
        global SCENEGRAPH_DEBUG
        val = '0'
        if SCENEGRAPH_DEBUG == '0':
            val = '1'
        os.environ["SCENEGRAPH_DEBUG"] = val
        SCENEGRAPH_DEBUG = val

        node_widgets = self.view.scene().getNodes()
        edge_widgets = self.view.scene().getEdges()

        if node_widgets:
            for widget in node_widgets:
                widget.setDebug(eval(SCENEGRAPH_DEBUG))

        if edge_widgets:
            for ewidget in edge_widgets:
                ewidget._debug = SCENEGRAPH_DEBUG

        self.view.scene().update()      

    def toggleEdgeTypes(self):
        """
        Toggle the edge types.
        """
        edge_type = self.edge_type_menu.currentText()
        if edge_type:
            self.edge_type = edge_type

        for edge in self.view.scene().getEdges():
            edge.edge_type = self.edge_type
        self.view.scene().update()

    #- ACTIONS ----
    def nodesSelectedAction(self):
        """
        Action that runs whenever a node is selected in the UI
        """
        from SceneGraph import ui
        # get a list of selected node widgets
        selected_nodes = self.view.scene().selectedNodes(nodes_only=True)

        # clear the list view
        self.tableModel.clear()
        self.tableView.reset()
        self.tableView.setHidden(True)  
        if selected_nodes:
            node = selected_nodes[0]

            node_selection_changed = False

            for n in selected_nodes:
                # edges: 65538, nodes: 65537

                if n not in self._selected_nodes:
                    node_selection_changed = True

            if node_selection_changed:
                self._selected_nodes = selected_nodes
                dagnodes = [x.dagnode for x in selected_nodes]

                self.updateAttributeEditor(dagnodes)

                # populate the graph widget with downstream nodes
                UUID = node.dagnode.id
                if UUID:
                    ds_ids = self.graph.downstream(node.dagnode.name)
                    dagnodes = []
                    for nid in ds_ids:
                        dnodes = self.graph.getNode(nid)
                        if dnodes:
                            dagnodes.append(dnodes[0])

                    dagnodes = [x for x in reversed(dagnodes)]
                    self.tableModel.addNodes(dagnodes)
                    self.tableView.setHidden(False)
                    self.tableView.resizeRowToContents(0)
                    self.tableView.resizeRowToContents(1)

        else:
            self._selected_nodes = []
            self.removeAttributeEditorWidget()

    def getAttributeEditorWidget(self):
        """
        Returns the AttributeEditor widget (if it exists).

        returns:
            (QWidget) - AttributeEditor instance.
        """
        return self.attrEditorWidget.findChild(QtGui.QWidget, 'AttributeEditor')

    def removeAttributeEditorWidget(self):
        """
        Remove a widget from the detailGroup box.
        """
        for i in reversed(range(self.attributeScrollAreaLayout.count())):
            widget = self.attributeScrollAreaLayout.takeAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def updateAttributeEditor(self, dagnodes, **attrs):
        """
        Update the attribute editor with a selected node.

        params:
            dagnodes (list) - list of dag node objects.
        """
        if type(dagnodes) not in [list, tuple]:
            dagnodes = [dagnodes,]

        attr_widget = self.getAttributeEditorWidget()
                
        if not attr_widget:
            attr_widget = ui.AttributeEditor(self.attrEditorWidget, handler=self.view.scene().handler)                
            self.attributeScrollAreaLayout.addWidget(attr_widget)
        attr_widget.setNodes(dagnodes)

    def tableSelectionChangedAction(self):
        """
        Update the attribute editor when a node is selected in the graph list.
        """
        if self.tableSelectionModel.selectedRows():
            idx = self.tableSelectionModel.selectedRows()[0]
            dagnode = self.tableModel.nodes[idx.row()]
            self.updateAttributeEditor(dagnode)

    def nodesModelChangedAction(self):
        self.view.scene().clearSelection()
        if self.nodeListSelModel.selectedRows():
            idx = self.nodeListSelModel.selectedRows()[0]
            node = self.nodesModel.nodes[idx.row()]
            node.setSelected(True)
            self.updateAttributeEditor(node.dagnode)

    def edgesModelChangedAction(self):
        self.view.scene().clearSelection()
        if self.edgeListSelModel.selectedRows():
            idx = self.edgeListSelModel.selectedRows()[0]

            edge = self.edgesModel.edges[idx.row()]
            edge.setSelected(True)

    # todo: deprecated?
    def nodeAddedAction(self, node):
        """
        Action whenever a node is added to the graph.
        """
        self.updateOutput()

    def nodesChangedAction(self, nodes):
        """
        Runs whenever nodes are changed in the UI.

        params:
            nodes (list) - list of Node widgets.
        """
        attr_widget = self.getAttributeEditorWidget()

        # update the AttributeEditor
        if attr_widget:
            attr_widget.updateChildEditors()

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

    #- Menus -----
    def createTabMenu(self, parent):
        """
        Build a context menu at the current pointer pos.

        params:
            parent (QWidget) - parent widget.
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
            node_action.triggered.connect(partial(self.graph.add_node, node_type=node, pos=(scene_pos.x(), scene_pos.y())))

        # haxx: stylesheet should work here
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        add_menu.setStyleSheet(str(ssf.readAll()))
        tab_menu.setStyleSheet(str(ssf.readAll()))

        tab_menu.addMenu(add_menu)
        tab_menu.exec_(qcurs.pos())

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

        self.qtsettings.beginGroup("Preferences")

        # viewport mode (global?)   
        viewport_mode = self.qtsettings.value("viewport_mode")
        if viewport_mode is not None:
            self.viewport_mode = viewport_mode

        # render fx (scene?)
        render_fx = self.qtsettings.value("render_fx")
        if render_fx is not None:
            if render_fx == 'false':
                self.render_fx =False
            if render_fx == 'true':
                self.render_fx =True

        # edge type (scene)
        edge_type = self.qtsettings.value("edge_type")
        if edge_type is not None:
            self.edge_type = edge_type

        # OpenGL mode (global)
        use_gl = self.qtsettings.value("use_gl")
        if use_gl is not None:
            if use_gl == 'false':
                self.use_gl =False
            if use_gl == 'true':
                self.use_gl =True

        #logging level (global)
        logging_level = self.qtsettings.value("logging_level")
        if logging_level is None:
            logging_level = 30 # warning

        log.setLevel(int(logging_level))
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

        # general preferences
        self.qtsettings.beginGroup('Preferences')
        self.qtsettings.setValue("viewport_mode", self.viewport_mode)
        self.qtsettings.setValue("render_fx", self.render_fx)
        self.qtsettings.setValue("edge_type", self.edge_type)
        self.qtsettings.setValue("use_gl", self.use_gl)
        self.qtsettings.setValue("logging_level", log.level)
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

        # update graph attributes
        self.graph.updateNetworkAttributes()
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

        nodes = self.view.scene().getNodes()
        edges = self.view.scene().getEdges()

        self.nodesModel.addNodes(nodes)
        self.edgesModel.addEdges(edges)

    def refreshGraph(self):
        """
        Refresh the current graph.
        """
        self.graph.evaluate()
        self.view.scene().update()

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
        self._groups        = ['MainWindow', 'RecentFiles', 'Preferences']
        self.initialize()

    def initialize(self):
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

        self.initializePreferences()

    def initializePreferences(self):
        """
        Set up the default preferences from global options.
        """
        if 'Preferences' not in self.childGroups():
            self.beginGroup("Preferences")
            # query the defauls from options.
            for option in options.SCENEGRAPH_PREFERENCES:
                if 'default' in options.SCENEGRAPH_PREFERENCES.get(option):
                    self.setValue('Preferences/default/%s' % option, options.SCENEGRAPH_PREFERENCES.get(option).get('default'))
            self.endGroup()

    def getDefaultValue(self, group, key):
        """
        Return the default values for a group.
        """
        result = None
        if group not in self.childGroups():
            log.warning('no settings saved for group "%s".' % group)
            return

        self.beginGroup(group)
        if not 'default' in self.childGroups():
            log.warning('default settings for group "%s" do not exist.' % group)
            return

        self.beginGroup('default')
        if key not in self.childKeys():
            log.warning('key "%s" does not exist in "%s/default".' % (key, group))
            return
        result = self.value(key)
        self.endGroup()
        return result

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

    def deleteFile(self):
        """
        Delete the preferences file on disk.
        """
        log.info('deleting settings: "%s"' % self.fileName())
        return os.remove(self.fileName())

    #- Recent Files ----
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
