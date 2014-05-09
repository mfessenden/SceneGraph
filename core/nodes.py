from PyQt4 import QtGui, QtCore, QtSvg
import os


class NodeBase(object):
    """
    Base node type
    """
    def __init__(self, *args, **kwargs):
        
        self.display_text  = None
        self.nodeimage     = None
        self.description   = None
        self.nodetype      = None
        self.nodecolor     = None
        

class GenericNode(NodeBase, QtSvg.QGraphicsSvgItem):

    clickedSignal = QtCore.pyqtSignal(QtCore.QObject)
    nodeCreatedInScene = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        NodeBase.__init__(self)
        
        self.name          = 'generic1'
        self.display_text  = 'Generic'
        #self.nodeimage     = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'icn', 'node_base_225x180.svg')
        self.nodeimage     = os.path.join('/USERS/michaelf/workspace/SceneGraph', 'icn', 'node_base_225x180.svg')
        self.description   = 'just a generic node'
        self.nodetype      = 'generic'
        self.nodecolor     = None
        
        args=list(args)
        args.insert(0, self.nodeimage)
        QtSvg.QGraphicsSvgItem.__init__(self, *args, **kwargs)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable|QtGui.QGraphicsItem.ItemIsMovable|QtGui.QGraphicsItem.ItemIsFocusable)
        self.setCachingEnabled(False)
        self.setAcceptHoverEvents(True)
        
        self.rectF = QtCore.QRectF(0,0,225,180)

    def mousePressEvent(self, event):
        print '# node selected: "%s"' % self.name
        event.accept()
