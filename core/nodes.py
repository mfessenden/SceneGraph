from PyQt4 import QtGui, QtCore, QtSvg


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
        
        self.display_text  = 'Generic'
        self.nodeimage     = '/USERS/michaelf/workspace/SceneGraph/icn/rect_150x150.svg'
        self.description   = 'just a generic node'
        self.nodetype      = 'generic'
        self.nodecolor     = None

        QtSvg.QGraphicsSvgItem.__init__(self, *args, **kwargs)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable|QtGui.QGraphicsItem.ItemIsMovable|QtGui.QGraphicsItem.ItemIsFocusable)
        self.setCachingEnabled(False)
        self.setAcceptHoverEvents(True)
