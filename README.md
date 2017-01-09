# SceneGraph

![Alt text](/doc/images/intro.png?raw=true "SceneGraph")

**SceneGraph** is a fast & flexible framework for visualizing node graphs in visual effects CC applications using PySide. Scenes can be saved and loaded in a variety of environments, and users can easily extend the toolset to include their own node types.

## Requirements

* [PySide][pyside-url]
* [NetworkX 1.9.1][networkx-url]
* [simplejson][simplejson-url]


## Installation

Clone the repository and ensure that the directory is included on your `PYTHONPATH`:

```bash
git clone git@github.com:mfessenden/SceneGraph.git
```

For Linux/macOS, symlink the launcher `bin/SceneGraph` somewhere on your `PATH`. For Windows, symlink `bin/SceneGraph.bat`.

## Usage

To launch the UI via the command line (Linux/macOS), simply call:

```bash
$ SceneGraph
```

(For Windows, double-click the `SceneGraph.bat` shortcut).



## SceneGraph API

```python
from SceneGraph import scenegraph

# show the UI
sgui = scenegraph.SceneGraphUI()
sgui.show()

# access the node graph instance
graph = sgui.graph

# list all node names
node_names = graph.node_names()

# query all of the node widgets from the `GraphicsScene`
scene = sgui.view.scene()
nodes = scene.nodes()

# query all of the current DAG nodes
dags = graph.nodes()

# return a named DAG node
dagnode = graph.get_node('node1')

# query node attributes
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

### Maya Usage

```python

from SceneGraph import scenegraph_maya
scenegraph_maya.main()

```

### Nuke Usage

```python

from SceneGraph import scenegraph_nuke
scenegraph_nuke.main()

```

## API

```python
# create a graph
from SceneGraph import core
g = core.Graph()

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

# connect two nodes via a connection string
e1 = g.connect('node1.output', 'node2.input')

# write the current graph to disk
g.write('~/graphs/my_graph.json')

# dump all nodes in the graph
print g.nodes()

# dump all node names
print g.node_names()

# dump all connections
print g.connections()

# updating attributes
d1 = g.add_node('default')
m1 = g.add_node('merge')

# connect two nodes via a named attribute
g.add_edge(d1, m1, dest_attr='inputA')

# change the input name
m1.rename_connection('inputA', 'newInput')

# add attributes to a dag node & flag it as an input connection
attr = n1.addAttr('env', value='maya', input=True)

# set an attribute value via the node
n1.env = 'nuke'

# set an attribute value via the attribute instance
attr.value = 'houdini'
```


[pyside-url]:https://pypi.org/project/PySide/
[simplejson-url]:https://simplejson.readthedocs.io/en/latest/
[networkx-url]:https://networkx.org
