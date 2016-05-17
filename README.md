SceneGraph
----------
![Alt text](/doc/images/intro.png?raw=true "SceneGraph")

**SceneGraph** is a fast & flexible framework for visualizing node graphs using in visual effects DCCs using PySide. Scenes can be saved and loaded in a variety of applications, and users can easily add their own nodes to suit their needs.

=====
Usage
=====

**Launching the interface:**

```python
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

```

**Maya Usage:**

```python

    from SceneGraph import scenegraph_maya
    scenegraph_maya.main()

```

**Nuke Usage:**

```python

    from SceneGraph import scenegraph_nuke
    scenegraph_nuke.main()

```

**SceneGraph API:**

```python

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

```

**Advanced API:**

```python
    # add attributes to a dag node, flag it as an input connection
    attr=n1.addAttr('env', value='maya', input=True)

    # set the value via the node
    n1.env = 'nuke'

    # set the value via the attribute instance
    attr.value = 'houdini'

```

**Dependencies:**

* Python 2.7
* simplejson
* NetworkX 1.9.1

