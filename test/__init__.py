from PySide import QtCore, QtGui


class DagNode(QtGui.QGraphicsItem):
    """
    A QGraphicsItem representing a node in a dependency graph.  These can be
    selected, moved, and connected together with DrawEdges.
    """
    
    Type = QtGui.QGraphicsItem.UserType + 1


    def __init__(self, dagNode):
        """
        """
        QtGui.QGraphicsItem.__init__(self)

        # The corresponding DAG node
        self.dagNode = dagNode

        # Input and output edges
        self.incomingDrawEdgeList = list()
        self.outgoingDrawEdgeList = list()

        #self.nub = DrawNodeNub()
        #self.nub.setParentItem(self)

        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(-1)
        
        self.width = 150
        self.height = 20

        # For handling movement undo/redos of groups of objects
        # This is a little strange to be handled by the node itself 
        # and maybe can move elsewhere?
        self.clickSnap = None
        self.clickPosition = None

        if type(self.dagNode) == dict:
            self.width = 15
            self.height = 15

    def type(self):
        """
        Assistance for the QT windowing toolkit.
        """
        return DrawNode.Type


    def removeDrawEdge(self, edge):
        """
        Removes the given edge from this node's list of edges.
        """
        if edge in self.incomingDrawEdgeList:
            self.incomingDrawEdgeList.remove(edge)
        elif edge in self.outgoingDrawEdgeList:
            self.outgoingDrawEdgeList.remove(edge)
        else:
            raise RuntimeError("Attempting to remove drawEdge that doesn't exist from node %s." % self.dagNode.name)
            

    def addDrawEdge(self, edge):
        """
        Add a given draw edge to this node.
        """
        if edge.destDrawNode() == self:
            self.incomingDrawEdgeList.append(edge)
        elif edge.sourceDrawNode() == self:
            self.outgoingDrawEdgeList.append(edge)
        edge.adjust()


    def drawEdges(self):
        """
        Return all incoming and outgoing edges in a list.
        """
        return (self.incomingDrawEdgeList + self.outgoingDrawEdgeList)


    def incomingDrawEdges(self):
        """
        Return only incoming edges in a list.
        """
        return self.incomingDrawEdgeList


    def outgoingDrawEdges(self):
        """
        Return only outgoing edges in a list.
        """
        return self.outgoingDrawEdgeList


    def boundingRect(self):
        """
        Defines the clickable hit-box.  Simply returns a rectangle instead of
        a rounded rectangle for speed purposes.
        """
        # TODO: Is this the right place to put this?  Maybe setWidth (adjust) would be fine.
        #if len(self.dagNode.name)*10 != self.width:
        #   self.prepareGeometryChange()
        #   self.width = len(self.dagNode.name)*10
        #   if self.width < 9: 
        #       self.width = 9
        adjust = 2.0
        return QtCore.QRectF(-self.width/2  - adjust, 
                             -self.height/2 - adjust,
                              self.width  + 3 + adjust, 
                              self.height + 3 + adjust)

    def shape(self):
        """
        The QT shape function.
        """
        # TODO: Find out what this is for again?
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(-self.width/2, -self.height/2, self.width, self.height), 5, 5)
        return path


    def paint(self, painter, option, widget):
        """
        Draw the node, whether it's in the highlight list, selected or 
        unselected, is currently executable, and its name.  Also draws a 
        little light denoting if it already has data present and/or if it is
        in a "stale" state.
        """
        inputsFulfilled = self.scene().dag.nodeAllInputsDataPresent(self.dagNode)
        
        # Draw the box
        gradient = QtGui.QLinearGradient(0, -self.height/2, 0, self.height/2)
        if option.state & QtGui.QStyle.State_Selected:
            gradient.setColorAt(0, QtGui.QColor(255, 255 if inputsFulfilled else 172, 0))
            gradient.setColorAt(1, QtGui.QColor(200, 128 if inputsFulfilled else 0, 0))
        else:
            topGrey = 200 if inputsFulfilled else 128
            bottomGrey = 96 if inputsFulfilled else 64
            gradient.setColorAt(0, QtGui.QColor(topGrey, topGrey, topGrey))
            gradient.setColorAt(1, QtGui.QColor(bottomGrey, bottomGrey, bottomGrey))

        # Draw a fat, bright outline if it's a highlighted node
        if self in self.scene().highlightNodes:
            highlightColor = QtGui.QColor(0, 128, 255)
            if self.scene().highlightIntensities:
                intensityIndex = self.scene().highlightIntensities[self.scene().highlightNodes.index(self)]
                highlightColor.setGreen(highlightColor.green() * intensityIndex)
                highlightColor.setBlue(highlightColor.blue() * intensityIndex)
            painter.setPen(QtGui.QPen(highlightColor, 3))
        else:
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 0))
        painter.setBrush(QtGui.QBrush(gradient))
        fullRect = QtCore.QRectF(-self.width/2, -self.height/2, self.width, self.height)
        painter.drawRoundedRect(fullRect, 5, 5)

        # No lights or text for dot nodes
        if type(self.dagNode) == depends_node.DagNodeDot:
            return

        # The "data present" light
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), 0.25))
        for output in self.dagNode.outputs():
            if self.scene().dag.nodeOutputDataPacket(self.dagNode, output).dataPresent():
                painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 255, 0)))
            else:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                break

        # The stale light overrides all
        if self.scene().dag.nodeStaleState(self.dagNode):
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 59, 174)))
        painter.drawRect(QtCore.QRectF(-self.width/2+5, -self.height/2+5, 5, 5))

        # Text (none for dot nodes)
        textRect = QtCore.QRectF(self.boundingRect().left() + 4,  self.boundingRect().top(),
                                 self.boundingRect().width() - 4, self.boundingRect().height())
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.black)
        painter.drawText(textRect, QtCore.Qt.AlignCenter, self.dagNode.name)


    def mousePressEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        # Note: This works without an 'if' because the only mouse button that 
        #       comes through here is the left
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        
        # Let the QT parent class handle the selection process before querying what's selected
        self.clickSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(), connectionMetaDict=self.scene().connectionMetaDict())
        self.clickPosition = self.pos()
        

    def mouseReleaseEvent(self, event):
        """
        Help manage mouse movement undo/redos.
        """
        # Don't register undos for selections without moves
        if self.pos() != self.clickPosition:
            currentSnap = self.scene().dag.snapshot(nodeMetaDict=self.scene().nodeMetaDict(), connectionMetaDict=self.scene().connectionMetaDict())
            self.scene().undoStack().push(depends_undo_commands.SceneOnlyUndoCommand(self.clickSnap, currentSnap, self.scene()))
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)


    def itemChange(self, change, value):
        """
        If the node has been moved, update all of its draw edges.
        """
        if change == QtGui.QGraphicsItem.ItemPositionHasChanged:
            for edge in self.drawEdges():
                edge.adjust()
        return QtGui.QGraphicsItem.itemChange(self, change, value)