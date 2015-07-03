#### branch: development

##### Usage:

###### UI:

    from SceneGraph import scenegraph
    sgui = scenegraph.SceneGraphUI()
    sgui.show()
    
    # access the node graph
    graph = sgui.graph

    # list all node names
    node_names = graph.listNodeNames()

    # get all of the node widgets from the GraphicsScene
    scene = sgui.view.scene()
    nodes = scene.getNodes()

    # query all of the current dag nodes
    dags = graph.getNodes()

    # return a named dag node
    dagnode = graph.getNode('node1')

    # get node attributes
    dagnode.getNodeAttributes()
        
    # set arbitrary attributes
    dagnode.setNodeAttributes(env='maya', version='2014')

    # querying widgets

    # get an output connection widget
    c_output=n1.getConnection('output')

    # query an edge 
    e1=scene.getEdge('node1.output', 'node2.input')[0]

    # get edge source item (Connection)
    e1.source_item

    # get connected nodes from an edge
    e1.listConnections()


###### API:

    # create a graph
    from SceneGraph import core
    g=core.Graph()

    # query the currently loaded node types
    node_types = g.node_types()

    # add some default nodes
    n1 = g.addNode('default', name='node1')
    n2 = g.addNode('default', name='node2')

    # connect the nodes (default output/inputs assumed)
    e1 = g.addEdge(n1, n2)

    # connect with a connection string
    e1 = g.connectNodes('node1.output', 'node2.input')

    # write the graph
    g.write('~/graphs/my_graph.json')

    # query all nodes in the graph
    print g.getNodes()

    # query all node names
    print g.allNodes()

    # query all connections
    print g.allConnections()


####### Advanced API:

    # add attributes to a dag node, flag it as an input connection
    attr=n1.addAttr('env', value='maya', input=True)

    # set the value via the node
    n1.env = 'nuke'

    # set the value via the attribute instance
    attr.value = 'houdini'


###### Maya:
    from SceneGraph import scenegraph_maya
    scenegraph_maya.main()



####### To Do:
###### API:
- Node defaults, private attributes not yet re-implemented in new API
- Node.__setstate__, __getstate__ not yet re-implemented

##### Dependencies:
- Python 2.7
- simplejson
- NetworkX 1.9.1
- matplotlib


####### Admin:
pyside-rcc ~/git/SceneGraph/ui/scenegraph.qrc -o ~/git/SceneGraph/ui/icons_rc.py