#### branch: development

##### Usage:

###### UI:

    from SceneGraph import scenegraph
    sgui = scenegraph.SceneGraphUI()
    sgui.show()
    
    # access the node graph
    graph = sgui.graph

    # list all node names
    node_names = graph.node_names()

    # get all of the node widgets from the GraphicsScene
    scene = sgui.view.scene()
    nodes = scene.nodes()

    # query all of the current dag nodes
    dags = graph.nodes()

    # return a named dag node
    dagnode = graph.get_node('node1')

    # get node attributes
    dagnode.getNodeAttributes()
        
    # set arbitrary attributes
    dagnode.setNodeAttributes(env='maya', version='2014')

    # querying widgets

    # get an output connection widget
    c_output=n1.get_connection('output')

    # query an edge 
    e1=scene.get_edge('node1.output', 'node2.input')[0]

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
    n1 = g.add_node('default', name='node1')
    n2 = g.add_node('default', name='node2')

    # query node connections
    if n1.is_input_connection:
        conn = n1.output_connections()

    # add a new input and output attribute
    n1.add_input(name='fileIn')

    # connect the nodes (default output/inputs assumed)
    e1 = g.add_edge(n1, n2)

    # connect with a connection string
    e1 = g.connect('node1.output', 'node2.input')

    # write the graph
    g.write('~/graphs/my_graph.json')

    # query all nodes in the graph
    print g.nodes()

    # query all node names
    print g.node_names()

    # query all connections
    print g.connections()

    # Updating Attributes
    from SceneGraph import core
    g = core.Graph()
    d = g.add_node('default')
    m = g.add_node('merge')
    g.add_edge(d, m, dest_attr='inputA')
    m.rename_connection('inputA', 'newInput')

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
pyside-rcc ~/git/SceneGraph/icn/scenegraph.qrc -o ~/git/SceneGraph/icn/scenegraph_rc.py
icn_build -f ~/git/SceneGraph/icn/scenegraph.qrc -o ~/git/SceneGraph/icn/icons.py

# scratch
from SceneGraph import core
g=core.Graph(debug=True)
g.edge_nice_name('732e7908-6264-4e96-b95b-1fe72c9e2f61', '0abdbeaf-681c-4d85-a712-7b3bd7e7a8d4')
pm=g.pmanager
m1=g.get_node('merge1')[0]
e1=g.edges()[0]
c=m1.get_input('input')

