#!/X/tools/binlinux/xpython
from PySide import QtCore, QtGui, QtSvg
import weakref
import re
import simplejson as json

from . import logger
from . import core
reload(core)


class GraphicsView (QtGui.QGraphicsView):
    
    tabPressed        = QtCore.Signal(bool)
    rootSelected      = QtCore.Signal(bool)
    
    def __init__ (self, parent = None, **kwargs):
        super(GraphicsView, self).__init__ (parent)
        
        self.gui    = kwargs.get('gui')
        self.parent = parent
        
        self.setInteractive(True)  # this allows the selection rectangles to appear
        self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        self.renderer = QtSvg.QSvgRenderer()
        self.setRenderHint(QtGui.QPainter.Antialiasing)
    
    def wheelEvent (self, event):
        """
        Scale the viewport with the middle-mouse wheel
        """
        super(GraphicsView, self).wheelEvent(event)
        factor = 1.2
        if event.delta() < 0 :
            factor = 1.0 / factor
        self.scale(factor, factor)
    
    def mousePressEvent(self, event):
        """
        Pan the viewport if the control key is pressed
        """
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
        super(GraphicsView, self).mousePressEvent(event)

    def keyPressEvent(self, event):
        """
        Fit the viewport if the 'A' key is pressed
        """
        graphicsScene = self.scene()
        nodeManager = graphicsScene.nodeManager
        
        if event.key() == QtCore.Qt.Key_A:           
            # get the bounding rect of the graphics scene
            boundsRect = graphicsScene.itemsBoundingRect()
            # set it to the GraphicsView scene rect...        
            self.setSceneRect(boundsRect)
            # resize
            self.fitInView(boundsRect, QtCore.Qt.KeepAspectRatio)

        elif event.key() == QtCore.Qt.Key_C and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = nodeManager.selectedNodes()
            nodeManager.copyNodes(nodes)
            print '# copying nodes: ', nodes

        elif event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
            nodes = nodeManager.pasteNodes()
            print '# pasting nodes: ', nodes

        elif event.key() == QtCore.Qt.Key_Delete:
            for item in graphicsScene.selectedItems():
                if isinstance(item, core.LineClass) or isinstance(item, core.NodeBase):
                    item.deleteNode()
                    
        if event.key() == QtCore.Qt.Key_S:           
            self.rootSelected.emit(True)

        event.accept()
       
    def get_scroll_state(self):
        """
        Returns a tuple of scene extents percentages
        """
        centerPoint = self.mapToScene(self.viewport().width()/2,
                                      self.viewport().height()/2)
        sceneRect = self.sceneRect()
        centerWidth = centerPoint.x() - sceneRect.left()
        centerHeight = centerPoint.y() - sceneRect.top()
        sceneWidth =  sceneRect.width()
        sceneHeight = sceneRect.height()
    
        sceneWidthPercent = centerWidth / sceneWidth if sceneWidth != 0 else 0
        sceneHeightPercent = centerHeight / sceneHeight if sceneHeight != 0 else 0
        return sceneWidthPercent, sceneHeightPercent


class GraphicsScene(QtGui.QGraphicsScene):    
    """
    Notes:
    
    self.itemsBoundingRect() - returns the maximum boundingbox for all nodes
    
    """
     
    def __init__ (self, parent=None):
        super(GraphicsScene, self).__init__ (parent)
        
        self.line        = None    
        self.sceneNodes  = weakref.WeakValueDictionary()
        self.nodeManager = None    
    
    def setNodeManager(self, val):
        self.nodeManager = val
    
    def createNode(self, node_type, **kwargs):
        """
        Create a node in the current scene with the given attributes
        
        params:
            node_type   - (str) node type to create
            
        returns:
            (object)    - scene node
        """
        node_name   = kwargs.get('name', 'Node')
        node_pos    = kwargs.get('pos', [0,0])
        # Now transfer the node_type (which is the base class Node) to a category or attribute node
        if node_type is "generic":
            sceneNode = core.GenericNode(name=node_name)
        if node_type is "root":
            sceneNode = core.RootNode()
        #sceneNode.connectSignals()
        sceneNode.setPos(node_pos[0], node_pos[1])
        self.sceneNodes[sceneNode.node_name] = sceneNode
        self.addItem(sceneNode)
        return sceneNode

    def dropEvent(self, event):
        newPos = event.scenePos()
    
    def mouseDoubleClickEvent(self, event):
        super(GraphicsScene, self).mouseDoubleClickEvent(event)
    
    """
    # CONNECTING NODES:
         
         - we need to implement mousePressEvent, mouseMoveEvent & mouseReleaseEvent methods  
    """
    def mousePressEvent(self, event):
        """
        If an input/output connector is selected, draw a line
        """
        item = self.itemAt(event.scenePos())
        if event.button() == QtCore.Qt.LeftButton and (isinstance(item, core.nodes.NodeInput) or isinstance(item, core.nodes.NodeOutput)):
            self.line = QtGui.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
            self.addItem(self.line)
        super(GraphicsScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line:
            newLine = QtCore.QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(newLine)
        super(GraphicsScene, self).mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.line:
            startItems = self.items(self.line.line().p1())
            if len(startItems) and startItems[0] == self.line:
                startItems.pop(0)
            endItems = self.items(self.line.line().p2())
            if len(endItems) and endItems[0] == self.line:
                endItems.pop(0)

            self.removeItem(self.line)

            # If this is true a successful line was created
            if self.connectionTest(startItems, endItems):
                # Creates a line that is basically of 0 length, just to put a line into the scene
                connectionLine = core.nodes.LineClass(startItems[0], endItems[0], QtCore.QLineF(startItems[0].scenePos(), endItems[0].scenePos()))
                self.addItem(connectionLine)
                # Now use that previous line created and update its position, giving it the proper length and etc...
                connectionLine.updatePosition()
                
                ###  NEED TO IMPLEMENT THIS< OR DELETE ###
                
                # Sending the data downstream. The start item is the upstream node ALWAYS. The end item is the downstream node ALWAYS.
                #connectionLine.getEndItem().getWidgetMenu().receiveFrom(connectionLine.getStartItem(), delete=False)
                #connectionLine.getStartItem().getWidgetMenu().sendData(connectionLine.getStartItem().getWidgetMenu().packageData())
                # Emitting the "justConnected" signal (That is on all connection points)
                #connectionLine.myEndItem.lineConnected.emit()
                #connectionLine.myStartItem.lineConnected.emit()
                
                ### ###
        self.line = None
        super(GraphicsScene, self).mouseReleaseEvent(event)

    def connectionTest(self, startItems, endItems):
        """
        This is the big if statement that is checking
        to make sure that whatever nodes the user is trying to
        make a connection between is allowable.
        """
        if startItems[0]:
            if startItems[0].isInputConnection:
                temp = startItems[0]
                if endItems[0]:
                    startItems[0] = endItems[0]
                    endItems[0] = temp

        try:
            if len(startItems) is not 0 and len(endItems) is not 0:
                if startItems[0] is not endItems[0]:
                    if isinstance(startItems[0], core.nodes.NodeOutput) and isinstance(endItems[0], core.nodes.NodeInput):
                        if (startItems[0].isOutputConnection and endItems[0].isInputConnection):
                            return True
        except AttributeError:
            pass
        return False


class NodeManager(object):
    """
    Manages nodes in the parent graph
    """
    def __init__(self, parent, gui):
        
        self.viewport       = parent
        self.scene          = self.viewport.scene()
        self.root_node      = None
        self._copied_nodes  = []
        self._startdir      = gui._startdir
        self._default_name  = 'scene_graph_v001'            # default scene name
        
    def getNodes(self):
        """
        Returns a weakref to all of the scene nodes
        
        returns:
            (weakref) 
        """
        return self.scene.sceneNodes

    def getNode(self, node_name):
        """
        Get a node by name
        """
        if node_name in self.getNodes():
            return self.getNodes().get(node_name)
        return

    def getRootNode(self):
        """
        Return the root node
        
        returns:
            (object)  - root node
        """
        return self.root_node

    def selectedNodes(self):
        """
        Returns nodes selected in the graph
        """
        selected_nodes = []
        for nn in self.getNodes():
            node = self.getNode(nn)
            if node.isSelected():
                selected_nodes.append(node)
        return selected_nodes
    
    def createNode(self, node_type, **kwargs):
        """
        Creates a node in the parent graph
        
        returns:
            (object)  - created node
        """
        force = kwargs.get('force', False)
        node_name = kwargs.pop('name', 'Node')
        if not force:
            node_name = self._nodeNamer(node_name)
        return self.scene.createNode(node_type, name=node_name, **kwargs)
    
    def createRootNode(self, hide=False, **kwargs):
        """
        Creates a root node
        
        params:
            hide      - (bool) hide the root node when created
    
        returns:
            (object)  - created node
        """
        import os
        sceneName = os.path.normpath(os.path.join(self._startdir, '%s.json' % self._default_name))
        self.root_node = self.scene.createNode('root', **kwargs)
        if hide:
            self.root_node.hide()
        self.root_node.addNodeAttributes(sceneName=sceneName)
        return self.root_node

    def removeNode(self, node):
        """
        Removes a node from the graph

        params:
            node    - (obj) node object
    
        returns:
            (object)  - removed node
        """
        node_name = node.node_name
        logger.getLogger().info('Removing node: "%s"' % node_name)
        self.scene.removeItem(node)
        if node_name in self.scene.sceneNodes.keys():
            return self.scene.sceneNodes.pop(node_name)
        return
    
    def renameNode(self, old_name, new_name):
        """
        Rename a node in the graph

        params:
            old_name    - (str) name to replace
            new_name    - (str) name to with

        returns:
            (object)  - renamed node
        """
        if new_name in self._getNames():
            logger.getLogger().error('"%s" is not unique' % new_name)
            return

        node=self.scene.sceneNodes.pop(old_name)
        node.node_name = new_name
        self.scene.sceneNodes[node.node_name]=node
        node.update()
        return node

    def copyNodes(self, nodes):
        """
        Copy nodes to the copy buffer
        """
        self._copied_nodes = []
        self._copied_nodes = nodes
        return self._copied_nodes

    def pasteNodes(self):
        """
        Paste saved nodes
        """
        pasted_nodes = []
        for node in self._copied_nodes:
            node.setSelected(False)
            new_name = self._nodeNamer(node.node_name)
            posx = node.pos().x() + node.width
            posy = node.pos().y() + node.height
            new_node = self.createNode('generic', name=new_name, pos=[posx, posy])
            new_node.addNodeAttributes(**node.getNodeAttributes())
            new_node.setSelected(True)
            pasted_nodes.append(new_node)
        return pasted_nodes
    
    def connectNodes(self, output, input):
        """
        Connect two nodes via a "Node.attribute" string
        """
        input_name, input_conn = input.split('.')
        output_name, output_conn = output.split('.')
        input_node = self.getNode(input_name)
        output_node = self.getNode(output_name)
        
        input_conn_node  = input_node.getInputConnection(input_conn)
        output_conn_node = output_node.getOutputConnection(output_conn)
        
        if input_conn_node and output_conn_node:
            connectionLine = core.nodes.LineClass(output_conn_node, input_conn_node, QtCore.QLineF(output_conn_node.scenePos(), input_conn_node.scenePos()))
            self.scene.addItem(connectionLine)
            connectionLine.updatePosition()
        else:
            if not input_conn_node:
                logger.getLogger().error('cannot find an input connection "%s" for node "%s"' % (input_conn, input_node ))

            if not output_conn_node:
                logger.getLogger().error('cannot find an output connection "%s" for node "%s"' % (output_conn, output_node))
    
    def reset(self):
        """
        Remove all node & connection data
        """
        for item in self.scene.items():
            if isinstance(item, core.nodes.NodeBase):
                self.scene.removeItem(item)
            elif isinstance(item, core.nodes.LineClass):
                self.scene.removeItem(item)
        self.createRootNode()

    def _getNames(self):
        """
        Returns the names of all the current nodes
        """
        return sorted(self.getNodes().keys())
    
    def _nodeNamer(self, node_name):
        """
        Returns a legal node name
        """
        node_name = re.sub(r'[^a-zA-Z0-9\[\]]','_', node_name)
        if not re.search('\d+$', node_name):
            node_name = '%s1' % node_name
        all_names = self._getNames()
        if node_name in all_names:
            node_num = int(re.search('\d+$', node_name).group())
            node_base = node_name.split(str(node_num))[0]
            for i in range(node_num+1, 9999):                
                if '%s%d' % (node_base, i) not in all_names:
                    node_name = '%s%d' % (node_base, i)
                    break
        return node_name
    
    def write(self, filename='/tmp/scene_graph_output.json'):
        """
        Write the graph to scene file
        """
        data = {}
        data.update(nodes={})
        data.update(connections={})
        conn_idx = 0
        for item in self.scene.items():
            if isinstance(item, core.nodes.NodeBase):
                data.get('nodes').update(**{item.node_name:item.data})
            elif isinstance(item, core.nodes.LineClass):
                startItem = str(item.myStartItem)
                endItem = str(item.myEndItem)
                data.get('connections').update(**{'connection%d' % conn_idx: {'start':startItem, 'end':endItem}})
                conn_idx+=1
        fn = open(filename, 'w')
        output_data=data
        json.dump(output_data, fn, indent=4)
        fn.close()
        
    def read(self, filename='/tmp/scene_graph_output.json'):
        """
        Read a graph from a saved scene
        """
        import os
        if os.path.exists(filename):
            raw_data = open(filename).read()
            tmp_data = json.loads(raw_data, object_pairs_hook=dict)
            node_data = tmp_data.get('nodes', {})
            conn_data = tmp_data.get('connections', {})
            
            # BUILD NODES
            for node in node_data.keys():
                logger.getLogger().info('building node: "%s"' % node)
                posx = node_data.get(node).pop('x')
                posy = node_data.get(node).pop('y')
                if node != 'Root':
                    myNode = self.createNode('generic', name=node, pos=[posx, posy], force=True)
                    node_attributes = dict()
                    if node_data.get(node):
                        for attr, val in node_data.get(node).iteritems():
                            attr = re.sub('^__', '', attr)
                            node_attributes.update({attr:val})
                        myNode.addNodeAttributes(**node_attributes)
                else:
                    # update root node
                    root_attributes = dict()
                    if not self.root_node:
                        self.createRootNode()
                    if node_data.get(node):
                        for attr, val in node_data.get(node).iteritems():
                            attr = re.sub('^__', '', attr)
                            root_attributes.update({attr:val})
                        self.root_node.addNodeAttributes(**root_attributes)
                    self.root_node.setX(posx)
                    self.root_node.setY(posy)

            # BUILD CONNECTIONS
            for conn in conn_data.keys():
                cdata = conn_data.get(conn)
                start_str = cdata.get('start')
                end_str = cdata.get('end')
                logger.getLogger().info('connecting: %s >> %s' % (start_str, end_str))
                self.connectNodes(start_str, end_str)
            
            self.viewport.setSceneRect(self.scene.itemsBoundingRect())
                    
        else:
            logger.getLogger().error('filename "%s" does not exist' % filename)
                
    
        