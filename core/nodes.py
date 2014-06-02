from PyQt4 import QtGui, QtCore, QtSvg
import os


# not currently used
class NodeTest(QtGui.QGraphicsItem):
    """
    Simple test node
    icon=GraphicsItem()
    icon.setPos(200, 200)
    """   
    def __init__ (self):
        super(QtGui.QGraphicsItem, self).__init__()
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)
        self.rectF = QtCore.QRectF(0,0,125,180)
        
    def boundingRect (self):
        return self.rectF
    
    def paint (self, painter=None, style=None, widget=None):
        #print dir(painter)
        painter.drawRoundedRect(self.rectF.x()-10, self.rectF.y()-10, self.rectF.width(), self.rectF.height(), 5, 5)
        #painter.fillRect(self.rectF, QtCore.Qt.red)


class NodeBase(object):
    """
    Base node type
    """
    def __init__(self, *args, **kwargs):
        
        self._node_name  = None
        self.nodeimage     = None
        self.description   = None
        self.nodetype      = None
        self.nodecolor     = None
        self._attributes   = dict(input = [], output=[])
        

class GenericNode(NodeBase, QtSvg.QGraphicsSvgItem):

    clickedSignal = QtCore.pyqtSignal(QtCore.QObject)
    nodeCreatedInScene = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        NodeBase.__init__(self)
        
        self.nodetype      = 'generic'
        self._node_name    = kwargs.pop('name', 'My_Node')
        self.nodeimage     = os.path.join(os.path.dirname(__file__), '../', 'icn', 'node_base_225x180.svg')
        self.description   = 'just a generic node'
        self.nodecolor     = None
        
        # text attributes
        self._name_text    = None                   # QGraphicsTextItem 
        
        args=list(args)
        args.insert(0, self.nodeimage)
        QtSvg.QGraphicsSvgItem.__init__(self, *args, **kwargs)
        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable | QtGui.QGraphicsItem.ItemIsMovable | QtGui.QGraphicsItem.ItemIsFocusable)
        self.setCachingEnabled(False)
        self.setAcceptHoverEvents(True)
        
        self.rectF = QtCore.QRectF(0,0,250,180)        
        self.set_name()

    def mousePressEvent(self, event):
        """
        Runs when node is selected
        """
        #print '# node selected: "%s"' % self._node_name
        event.accept()
    
    def set_name(self):
        """
        Set the node title
        """
        if not self._name_text:
            font = QtGui.QFont("SansSerif", 14)
            #font.setStyleHint(QtGui.QFont.Helvetica)
            font.setStretch(100)
            self._name_text = QtGui.QGraphicsTextItem(self._node_name, self)
            self._name_text.setFont(font)
            self._name_text.setDefaultTextColor(QtGui.QColor(QtCore.Qt.black))
            self._name_text.setPos(self.sceneBoundingRect().left(), self.sceneBoundingRect().top())
            #self._name_text.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        else:
            self._name_text.setPlainText(self._node_name)
            
    @property
    def node_name(self):
        return self._node_name
    
    @node_name.setter
    def node_name(self, val):
        self._node_name = val
        self.set_name()

