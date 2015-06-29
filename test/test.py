#!/usr/bin/env python
from PySide import QtCore, QtGui
from functools import partial
import os
import pysideuic
import xml.etree.ElementTree as xml
from cStringIO import StringIO
from SceneGraph import core 
from SceneGraph import options

log = core.log


SCENEGRAPH_TEST_PATH = options.SCENEGRAPH_TEST_PATH
SCENEGRAPH_TEST_UI = os.path.join(SCENEGRAPH_TEST_PATH, 'TestGraph.ui')


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


# load the ui file
form_class, base_class = loadUiType(SCENEGRAPH_TEST_UI)


class TestGraph(form_class, base_class):
    def __init__(self, parent=None, opengl=False, debug=False, **kwargs):
        super(TestGraph, self).__init__(parent)

        self.use_gl      = opengl
        self._debug      = debug
        self.environment = 'standalone'
        self.setupUi(self)
        
        # allow docks to be nested
        self.setDockNestingEnabled(True)
        #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setWindowTitle("Node Test Graph")

        self.initializeGraphicsView()
        self.initializeStylesheet()
        self.connectSignals()

    def initializeStylesheet(self):
        """
        Setup the stylehsheet.
        """
        self.stylesheet = os.path.join(options.SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

    def initializeGraphicsView(self):
        from SceneGraph import ui
        reload(ui)
        self.graph = core.Graph()
        self.network = self.graph.network
        self.network.graph['environment'] = self.environment

        # add our custom GraphicsView object
        self.view = ui.GraphicsView(self.gview, ui=self, opengl=self.use_gl, debug=self._debug)
        self.gviewLayout.addWidget(self.view) 

    def connectSignals(self):
        self.button_add.clicked.connect(self.addAction)
        self.button_remove.clicked.connect(self.removeAction)
        self.button_refresh.clicked.connect(self.refreshAction)

    def addAction(self, nodetype='default'):
        """
        Add a node to the Graph object.
        """
        dag=self.graph.addNode(nodetype)

        # get the node's widget.
        node = dag._widget
        if node:
            #node.height=75
            #node.is_expanded=True
            return True
        log.warning('cannot find a node widget for "%s"' % dag.name)
        return False

    def removeAction(self):
        nodes = self.view.scene().selectedNodes()
        if nodes:
            for node in nodes:
                print node.dagnode.id
        return False

    def refreshAction(self):
        print '# refreshing...'
        return False

    def readGraph(self, filename):
        pass
