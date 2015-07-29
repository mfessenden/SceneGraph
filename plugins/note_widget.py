#!/usr/bin/env python
import sys
import math
import weakref
from PySide import QtCore, QtGui
from SceneGraph.core import log
from SceneGraph import options
from SceneGraph.ui import SceneNodesCommand


SCENEGRAPH_WIDGET_TYPE = 'note'


class NoteWidget(QtGui.QGraphicsObject): 

    Type           = QtGui.QGraphicsObject.UserType + 1
    doubleClicked  = QtCore.Signal()
    nodeChanged    = QtCore.Signal(object) 
    nodeDeleted    = QtCore.Signal(object)
    node_class     = 'note' 

    def __init__(self, dagnode, parent=None):
        super(NoteWidget, self).__init__(parent)

        # connect the dag node
        self.dagnode         = dagnode
        self.dagnode.connect_widget(self)
        
        # attributes        
        self.corner_size     = 20
        self.bufferX         = 3
        self.bufferY         = 3
        self.pen_width       = 1.5                            # pen width for NoteBackground  

        # fonts
        self._font           = 'SansSerif'
        self._font_size      = self.dagnode.font_size
        self._font_bold      = False
        self._font_italic    = False

        # widget colors
        self._l_color        = [5, 5, 5, 255]                 # label color
        self._p_color        = [10, 10, 10, 255]              # pen color (outer rim)
        self._s_color        = [0, 0, 0, 60]                  # shadow color

        # widget globals
        self._debug          = False
        self.is_selected     = False                          # indicates that the node is selected
        self.is_hover        = False                          # indicates that the node is under the cursor
        self.handle_selected = False                          # indicates that the node handle is selected
        self._render_effects = True                           # enable fx

        # temp resizing attributes
        self.top_left        = ()
        self.btm_right       = ()

        # label
        self._evaluate_tag   = False                          # indicates the node is set to "evaluate" (a la Houdini)
        self.label           = NodeText(self)
        self.resize_handle   = QtGui.QGraphicsRectItem(self)
        self.center_label    = QtGui.QGraphicsTextItem(self)  # debug  

        # undo/redo snapshots
        self._current_pos    = QtCore.QPointF(0,0)
        self._data_snapshot  = None
        self._pos_snapshot   = None

        self.setHandlesChildEvents(True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)

        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsScenePositionChanges, True)
        self.setAcceptsHoverEvents(True)

        # set node position
        self.setPos(QtCore.QPointF(self.dagnode.pos[0], self.dagnode.pos[1]))

    def close(self):
        """
        Cleanup and delete the node and children.
        """
        if self is not None:
            if self.scene() is not None:
                self.scene().removeItem(self)
   
    #- Attributes ----
    @property
    def id(self):
        return self.dagnode.id
    
    @property
    def name(self):
        return self.dagnode.name

    @property
    def width(self):
        return float(self.dagnode.width)
        
    @width.setter
    def width(self, val):
        self.dagnode.width = val

    @property
    def height(self):
        return float(self.dagnode.base_height)

    @height.setter
    def height(self, val):
        self.dagnode.base_height = float(val)

    @property
    def color(self):
        """
        Return the 'node color' (background color)
        """
        return self.dagnode.color

    @color.setter
    def color(self, val):
        """
        Return the 'node color' (background color)
        """
        self.dagnode.color = val

    @property
    def is_enabled(self):
        return self.dagnode.enabled

    @is_enabled.setter
    def is_enabled(self, val):
        self.dagnode.enabled = val
        self.nodeChanged.emit(self)
        return self.dagnode.enabled

    @property
    def is_expanded(self):
        return False

    #- Events ----
    def hoverMoveEvent(self,event):
        QtGui.QGraphicsItem.hoverMoveEvent(self, event)
        scene_pos = event.scenePos()
        if self.handle_selected:
            if not self.handleRect().contains(self.mapFromScene(scene_pos)):
                self.handle_selected = False

    def hoverLeaveEvent(self,event):
        self.handle_selected = False
        QtGui.QGraphicsItem.hoverLeaveEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Scale the node as the resize handle is dragged.
        """
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

        if self.handle_selected:
            scene_pos = event.scenePos()

            # if there's no stashed value, set it
            if not self.top_left:
                # map scene coordinates to local
                top_left = self.mapToScene(self.boundingRect().topLeft())
                self.top_left = (top_left.x(), top_left.y())

            self.btm_right = (scene_pos.x(), scene_pos.y())
            # create a temporary rectangle with the current selection
            rect = QtCore.QRectF(QtCore.QPointF(*self.top_left), QtCore.QPointF(*self.btm_right))    
            self.dagnode.width = rect.width()
            self.dagnode.height = rect.height()

    def mousePressEvent(self, event):
        """
        Set the handle selection state if the handle widget is clicked.
        """
        self.handle_selected = False
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        scene_pos = event.scenePos()
        if self.handleRect().contains(self.mapFromScene(scene_pos)):
            self.handle_selected = True

    def mouseReleaseEvent(self, event):
        """
        Reset resize values when the mouse is released.
        """
        self.top_left = []
        self.btm_right = []
        #cpos = self.mapToScene(self.boundingRect().center())

        if self.handle_selected:
            self.handle_selected = False
            #self.setPos(cpos.x(), cpos.y())            
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        

    def dagnodeUpdated(self, *args, **kwargs):
        """
        Callback from the dag node.
        """
        pass

    def itemChange(self, change, value):
        """
        Default node 'changed' signal.

        ItemMatrixChange

        change == "GraphicsItemChange"
        """
        if change == self.ItemPositionHasChanged:
            self.nodeChanged.emit(self)
            #self.updateConnections()
        return super(NoteWidget, self).itemChange(change, value)

    def boundingRect(self):
        """
        Returns a bounding rectangle for the node.

        returns:
            (QRectF) - node bounding rect.
        """
        if self.top_left and self.btm_right:
            top_left = self.mapFromScene(*self.top_left)
            btm_right = self.mapFromScene(*self.btm_right)
            return QtCore.QRectF(top_left, btm_right)

        w = self.width
        h = self.height
        bx = self.bufferX
        by = self.bufferY
        return QtCore.QRectF(-w/2 -bx, -h/2 - by, w + bx*2, h + by*2)

    def shape(self):
        """
        Create the shape for collisions.

        returns:
            (QPainterPath) - painter path object.
        """
        w = self.width + 4
        h = self.height + 4
        bx = self.bufferX
        by = self.bufferY
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-w/2, -h/2, w, h), 7, 7)
        return path

    #- SUBCLASS -----
    #- Global Properties ----
    @property
    def center(self):
        return self.boundingRect().center()

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        returns:
            (QColor) - widget background color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.is_hover:
            base_color = QtGui.QColor(*self.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.color)

    @property
    def pen_color(self):
        """
        Returns the widget pen color.

        returns:
            (QColor) - widget pen color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[40, 40, 40])
        if self.is_selected:
            return QtGui.QColor(*[251, 210, 91])
        return QtGui.QColor(*self._p_color)

    @property
    def label_color(self):
        """
        Returns the widget label color.

        returns:
            (QColor) - widget label color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[50, 50, 50])
        if self.is_selected:
            return QtGui.QColor(*[88, 0, 0])
        return QtGui.QColor(*self._l_color)

    @property
    def shadow_color(self):
        """
        Returns the node shadow color, as dictated
        by the dagnode.

        returns:
            (QColor) - shadow color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[35, 35, 35, 60])
        if self.is_selected:
            return QtGui.QColor(*[104, 56, 0, 60])
        return QtGui.QColor(*self._s_color)

    def getNoteShape(self):
        """
        Returns a note-shaped polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - note-shaped polygon
        """
        rect = self.boundingRect()

        p1 = rect.topLeft()
        p2 = rect.topRight()
        p3 = rect.topRight()
        p4 = rect.bottomRight()
        p5 = rect.bottomLeft()

        p2.setX(p2.x() - self.corner_size)
        p3.setY(p2.y() + self.corner_size)
        return QtGui.QPolygonF([p1, p2, p3, p4, p5, p1])

    def getCornerShape(self):
        """
        Returns a corner polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - corner polygon
        """
        rect = self.boundingRect()

        p1 = rect.topRight() # need as p1
        p2 = rect.topRight() # need as p2

        p1.setX(p1.x() - self.corner_size)
        p2.setY(p1.y() + self.corner_size)

        p3 = QtCore.QPointF(p1.x(), p2.y())
        return QtGui.QPolygonF([p1, p2, p3, p1])

    def handleRect(self):
        """
        * testing
        """
        rect = self.boundingRect()
        size = 6
        buffer = 2
        p1 = rect.bottomRight() # need as p1
        p2 = QtCore.QPointF(p1.x() - (size+buffer), p1.y())
        topLeft = QtCore.QPointF(p2.x(), p2.y() - (size+buffer))
        return QtCore.QRectF(topLeft, QtCore.QSize(size, size))

    def paint(self, painter, option, widget):
        """
        Paint the widget container and all of the child widgets.
        """
        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        # draw resize handle
        handle_color = self.bg_color
        handle_color.setAlpha(75)
        if self.handle_selected:
            handle_color = handle_color.lighter(250)
        hpen_color = handle_color.darker(200)
        hpen_color.setAlpha(125)
        self.resize_handle.setPen(QtGui.QPen(hpen_color))
        self.resize_handle.setBrush(QtGui.QBrush(handle_color))
        
        self.label.setPos(self.label_pos)
        self.label.label.setTextWidth(self.width * 0.8)

        # setup colors
        bg_color1 = self.bg_color
        bg_color2 = bg_color1.darker(150)
        bg_color3 = self.bg_color.lighter(50)
        bg_color3.setAlpha(125)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)
        gradient.setColorAt(0, bg_color1)
        gradient.setColorAt(1, bg_color2)

        # pen color
        pcolor = self.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.pen_width)

        cpen = QtGui.QPen(QtCore.Qt.NoPen)

        # background brush
        qbrush = QtGui.QBrush(gradient)
        # corner brush
        cbrush = QtGui.QBrush(bg_color2.darker(80))
        # handle brush
        hbrush = QtGui.QBrush(bg_color3)

        if self._debug:
            qpen = QtGui.QPen(QtGui.QColor(*[220, 220, 220]))
            qpen.setStyle(QtCore.Qt.DashLine)
            qpen.setWidthF(0.5)

            cpen = QtGui.QPen(QtGui.QColor(*[0, 0, 255]))
            cpen.setStyle(QtCore.Qt.DashLine)
            cpen.setWidthF(0.5)

            qbrush = QtGui.QBrush(QtCore.Qt.NoBrush)
            cbrush = QtGui.QBrush(QtCore.Qt.NoBrush)
            painter.drawRect(self.boundingRect())

            center_color = QtGui.QColor(*[164, 224, 255, 75])
            painter.setPen(QtGui.QPen(center_color, 0.5, QtCore.Qt.DashLine))

            # center point 
            h1 = QtCore.QPoint(-self.width/2, 0)
            h2 = QtCore.QPoint(self.width/2, 0)

            v1 = QtCore.QPoint(0, -self.height/2)
            v2 = QtCore.QPoint(0, self.height/2)

            hline = QtCore.QLine(h1, h2)
            vline = QtCore.QLine(v1, v2)

            painter.drawLine(hline)
            painter.drawLine(vline)

        # shapes
        note_shape = self.getNoteShape()
        corner_shape = self.getCornerShape()
        corner_shape.translate(-0.5, 0.5)
        painter.setPen(qpen)
        painter.setBrush(qbrush)

        # draw background
        painter.drawPolygon(note_shape)        
        painter.setBrush(cbrush)
        painter.setPen(cpen)
        # draw corner
        painter.drawPolygon(corner_shape)

        self.center_label.hide()
        cpos = self.mapToScene(self.boundingRect().center())

        # if the handle is selected, update the position
        if self.handle_selected:
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(*[200, 200, 200, 255])))
            clabel = '%.2f, %.2f' % (cpos.x(), cpos.y())
            self.center_label.setPlainText(clabel)
            
            # show the center coordinates if we're in debug mode
            if self._debug:
                self.center_label.show()
                self.center_label.setPos(0,0)
            self.setPos(cpos.x(),cpos.y())            
        self.resize_handle.setRect(self.handleRect())
            
    def setDebug(self, val):
        """
        Set the debug value of all child nodes.
        """
        if val != self._debug:
            self._debug = val
            #self.background.setDebug(val)
            for item in self.childItems():
                if hasattr(item, '_debug'):
                    item._debug = val

    @classmethod
    def ParentClasses(cls, p=None):
        """
        Return all subclasses.
        """
        base_classes = []
        cl = p if p is not None else cls.__class__
        for b in cl.__bases__:
            if b.__name__ != "object":
                base_classes.append(b.__name__)
                base_classes.extend(cls.ParentClasses(b))
        return base_classes


    #- NOTEWIDGET SPECIFIC ----
    @property
    def label_pos(self):
        return QtCore.QPointF(-self.width/2, -self.height/2 - self.bufferY)


class NodeText(QtGui.QGraphicsObject):
    
    doubleClicked     = QtCore.Signal()
    labelChanged      = QtCore.Signal()
    clicked           = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QGraphicsObject.__init__(self, parent)

        self.dagnode        = parent.dagnode
        self._debug         = False

        self.label = QtGui.QGraphicsTextItem(self.dagnode.doc_text, self)
        self.label.node = parent
        self._document = self.label.document()

        #self._document.setMaximumBlockCount(1)
        self._document.contentsChanged.connect(self.nodeTextChanged)

        # set flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        self.label.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.label.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

        # bounding shape
        self.rect_item = QtGui.QGraphicsRectItem(self.boundingRect(), self)
        self.rect_item.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        #self.rect_item.setPen(QtGui.QPen(QtGui.QColor(125,125,125)))        
        self.rect_item.pen().setStyle(QtCore.Qt.DashLine)
        self.rect_item.stackBefore(self.label)
        self.setHandlesChildEvents(False)

    @QtCore.Slot()
    def nodeTextChanged(self):
        """
        Runs when the node name is changed.
        """      
        new_name = self.text
        if new_name != self.dagnode.doc_text:
            self.dagnode.doc_text = new_name
            
        # re-center the label
        bounds = self.boundingRect()
        self.label.setPos(bounds.width()/2. - self.label.boundingRect().width()/2, 0)

    @property
    def is_editable(self):
        return self.label.textInteractionFlags() == QtCore.Qt.TextEditorInteraction

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.nodeTextChanged()
        else:
            QtGui.QGraphicsObject.keyPressEvent(self, event)

    @property
    def node(self):
        return self.parentItem()

    def boundingRect(self):
        try:
            return self.label.boundingRect()
        except:
            return QtCore.QRectF(0, 0, 0, 0)

    @property
    def text(self):
        return str(self._document.toPlainText())

    @text.setter
    def text(self, text):
        self._document.setPlainText(text)
        return self.text

    def shape(self):
        """
        Aids in selection.
        """
        path = QtGui.QPainterPath()
        polyon = QtGui.QPolygonF(self.boundingRect())
        path.addPolygon(polyon)
        return path

    def paint(self, painter, option, widget):
        """
        Draw the label.
        """
        label_color = self.node.label_color
        label_italic = self.node._font_italic

        # diabled fonts always render italicized
        if not self.node.is_enabled:
            label_italic = True

        #painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        qfont = QtGui.QFont(self.node._font)
        qfont.setPointSize(self.dagnode.font_size)
        qfont.setBold(self.node._font_bold)
        qfont.setItalic(label_italic)
        self.label.setFont(qfont)

        # debug
        if self._debug:
            label_color = QtGui.QColor(*[200, 200, 200])
            qpen = QtGui.QPen(QtGui.QColor(125,125,125))
            qpen.setWidthF(0.5)
            qpen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(qpen)
            painter.drawPolygon(self.boundingRect())

        self.label.setDefaultTextColor(label_color)
        self.text = self.node.dagnode.doc_text


class NoteBackground(QtGui.QGraphicsObject):

    def __init__(self, parent=None):
        super(NoteBackground, self).__init__(parent)

        self.dagnode = parent.dagnode
        self._debug  = False

        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, False)

    @property
    def node(self):
        return self.parentItem()

    @property 
    def pen_width(self):
        return self.node.pen_width

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        returns:
            (QColor) - widget background color.
        """
        if not self.node.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.node.is_selected:
            return QtGui.QColor(*[255, 183, 44])

        if self.node.is_hover:
            base_color = QtGui.QColor(*self.dagnode.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.dagnode.color)

    @property
    def pen_color(self):
        """
        Returns the widget pen color.

        returns:
            (QColor) - widget pen color.
        """
        if not self.node.is_enabled:
            return QtGui.QColor(*[40, 40, 40])
        if self.node.is_selected:
            return QtGui.QColor(*[251, 210, 91])
        return QtGui.QColor(*self.node._p_color)

    def boundingRect(self):
        if self.node:
            return self.node.boundingRect()
        return QtCore.QRectF(0,0,0,0)

    def getNoteShape(self):
        """
        Returns a note-shaped polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - note-shaped polygon
        """
        rect = self.boundingRect()
        corner_w = rect.width() - (rect.width() * 0.8)

        p1 = rect.topLeft()
        p2 = rect.topRight()
        p3 = rect.topRight()
        p4 = rect.bottomRight()
        p5 = rect.bottomLeft()

        p2.setX(p2.x() - corner_w)
        p3.setY(p2.y() + corner_w)
        return QtGui.QPolygonF([p1, p2, p3, p4, p5, p1])

    def getCornerShape(self):
        """
        Returns a corner polygon (based on the current boundingRect)

        returns:
            (QPolygonF) - corner polygon
        """
        rect = self.boundingRect()
        corner_w = rect.width() - (rect.width() * 0.8)
        corner_h = rect.height() - (rect.height() * 0.8)

        p1 = rect.topRight() # need as p1
        p2 = rect.topRight() # need as p2

        p1.setX(p1.x() - corner_w)
        p2.setY(p1.y() + corner_w)

        p3 = p2
        p3.setX(p2.x() - corner_w)
        return QtGui.QPolygonF([p1, p2, p3, p1])

    def paint(self, painter, option, widget):
        """
        Paint the node background.
        """
        # setup colors
        bg_color1 = self.node.bg_color
        bg_color2 = bg_color1.darker(150)

        # background gradient
        gradient = QtGui.QLinearGradient(0, -self.node.height/2, 0, self.node.height/2)
        gradient.setColorAt(0, bg_color1)
        gradient.setColorAt(1, bg_color2)

        # pen color
        pcolor = self.node.pen_color
        qpen = QtGui.QPen(pcolor)
        qpen.setWidthF(self.node.pen_width)

        qbrush = QtGui.QBrush(gradient)
        cbrush = QtGui.QBrush(QtGui.QColor(*[225, 189, 10, 55]))

        painter.setPen(qpen)
        painter.setBrush(qbrush)

        painter.drawPolygon(self.getNoteShape())

    def setDebug(self, val):
        """
        Set the debug value of all child nodes.
        """
        if val != self._debug:
            self._debug = val


class ResizeHandle(QtGui.QGraphicsObject): 

    clicked  = QtCore.Signal()

    def __init__(self, parent=None):
        super(ResizeHandle, self).__init__(parent)

        self.dagnode         = parent.dagnode
        self.width           = 5.0

        self._debug          = False
        self.is_selected     = False                  # indicates that the node is selected
        self.is_hover        = False                  # indicates that the node is under the cursor
        self._render_effects = True                   # enable fx
        
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)
        self.setFlag(QtGui.QGraphicsObject.ItemSendsGeometryChanges, True)
        
        self.setAcceptedMouseButtons(True)
        self.setAcceptsHoverEvents(True)

    @property
    def node(self):
        return self.parentItem()

    @property
    def color(self):
        """
        Return the 'node color' (background color)
        """
        return self.dagnode.color

    @color.setter
    def color(self, val):
        """
        Return the 'node color' (background color)
        """
        self.dagnode.color = val

    @property
    def is_enabled(self):
        return self.dagnode.enabled

    @property
    def bg_color(self):
        """
        Returns the widget background color.

        returns:
            (QColor) - widget background color.
        """
        if not self.is_enabled:
            return QtGui.QColor(*[125, 125, 125])

        if self.is_selected:
            return QtGui.QColor(*[255, 183, 44, 125])

        if self.is_hover:
            base_color = QtGui.QColor(*self.color)
            return base_color.lighter(125)
        return QtGui.QColor(*self.color)

    def boundingRect(self):
        try:
            return self.node.boundingRect()
        except:
            return QtCore.QRectF(0, 0, 0, 0) 

    def mousePressEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        self.clicked.emit()
        QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

    def getShape(self):
        """
        Returns a shape based on the parent's boundingRect

        returns:
            (QPolygonF) - qquare polygon
        """
        rect = self.boundingRect()

        p1 = rect.bottomRight()
        p2 = QtCore.QPointF(p1.x() - self.width, p1.y())
        p3 = QtCore.QPointF(p2.x(), p2.y() - self.width)
        p4 = QtCore.QPointF(p3.x() + self.width, p3.y())
        return QtGui.QPolygonF([p1, p2, p3, p4, p1])

    def paint(self, painter, option, widget):
        """
        Paint the node background.
        """
        self.is_selected = False
        self.is_hover = False

        if option.state & QtGui.QStyle.State_Selected:
            self.is_selected = True

        if option.state & QtGui.QStyle.State_MouseOver:
            self.is_hover = True

        # setup colors
        bg_color = self.bg_color.darker(100)
        qpen = QtGui.QPen(QtCore.Qt.NoPen)
        qbrush = QtGui.QBrush(bg_color)

        painter.setPen(qpen)
        painter.setBrush(qbrush)

        shape = self.getShape()
        shape.translate(-2, -2)
        painter.drawPolygon(shape)