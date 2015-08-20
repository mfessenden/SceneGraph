Core Modules
============

The core modules represent the core of the application (duh). The graph, plugins and node types are all accessible from here. Node widgets and other UI modules are intentially separate so that the core module can be manipulated indepedantly of the user interface.

::

 from SceneGraph import core
 g=core.Graph()

 n1=g.addNode('default')
 n2=g.addNode('default')

 e1=g.addEdge(n1, n2)


.. automodule:: core.graph

core.graph
----------

.. _Graph:

Graph
^^^^^

The Graph class is a wrapper for a networkx.MultiDiGraph graph. The Graph can be fully manipulated without ever opening the UI. Under the hood, the Graph stores nodes as queryable :ref:`DagNode` objects. Edges are stored a little differently; they are stored as NetworkX graph edges only.

.. autoclass:: Graph
    :members:


.. _Grid:

Grid
^^^^

Defines a two-dimensional grid used by the graph to auto-space new nodes. If the graph is in UI mode, the grid is not used, relying on the mouse position to determine the initial value of a new node.

To setup a new Grid, initialize an instance with 5 rows & 5 columns, with a row width & height of 100:


.. testsetup::
    
    from SceneGraph.core.graph import Grid

.. testcode::
    
    from SceneGraph.core.graph import Grid
    g = Grid(5, 5, width=100, height=100)
    print g.coords

Printing the :func:`Graph.coords <core.graph.Grid.coords>` will give you the current coordinates.

.. testoutput::

    (0, 0)

To advance to the next cell, simple call the :func:`Graph.next() <core.graph.Grid.next>` method:

.. testcode::

    g.next()
    print g.coords

Print the :func:`Graph.coords <core.graph.Grid.coords>` again to see the new coordinates:


.. testoutput::

    (0, 100)

.. autoclass:: Grid
    :members:


core.attributes
---------------

.. _Attribute:

Attribute
^^^^^^^^^

The :ref:`Attribute` class is a generic connection node for DagNode objects. To query a node's connections:
::

 #!/usr/bin/env python
 node = g.get_node('model1')[0]
 conn = node.getConnection('output')
 output = node.dagnode.attributes('output')

Attributes are stored as dictionaries of connection name/connection attributes. Attributes are stored in a special dictionary in the scene:
::

 "output": {
     "value": null,
     "_edges": [],
     "attr_type": "null",
     "connectable": true,
     "connection_type": "output"
 }

The name of this connection is **output** and the **connection_type** denotes it as an output connection. Therefore it will be rendered as a green output node on the right side of the parent node.

.. automodule:: core.attributes
.. autoclass:: Attribute
    :members:


core.plugins    
------------

.. _PluginManager:

PluginManager
^^^^^^^^^^^^^
The PluginManager manages how SceneGraph finds and loads plugins.

.. automodule:: core.plugins
.. autoclass:: PluginManager
    :members:


core.metadata
-------------

.. _MetadataParser:

MetadataParser
^^^^^^^^^^^^^^
The MetadataParser reads and translates metadata to the widget.

.. automodule:: core.metadata
.. autoclass:: MetadataParser
    :members:


core.nodes
----------
.. automodule:: core.nodes
    :members:
    :undoc-members:
    :show-inheritance:

.. _Node:

Node
^^^^
The basic DAG node type. Represents a dag node that has attributes, but no connections. Currently, the only node
that utilizes this type is the Note.

.. autoclass:: Node
    :members:

.. _DagNode:

DagNode
^^^^^^^
The DagNode class is the base class for all nodes. Allows for custom attributes to be added, as well as connections.

.. autoclass:: DagNode
    :members:

.. _DefaultNode:

DefaultNode
^^^^^^^^^^^
The DefaultNode is a standard node with one input and one output.

.. autoclass:: DefaultNode
    :members:


.. _DotNode:

DotNode
^^^^^^^
The DotNode is a standard node with one input and one output. Useful for directing the graph in different directions. Dot nodes don't accept new attributes nor do they expand.

.. autoclass:: DotNode
    :members:


.. _NoteNode:

NoteNode
^^^^^^^^
The NoteNode is a standard node with one no inputs or outputs. It simply displays a single text string attribute. Useful for adding notes to other users opening scenes.

.. autoclass:: NoteNode
    :members:


.. _Metadata:

Metadata
^^^^^^^^
The Metadata parses node metadata on disk.

.. autoclass:: Metadata
    :members:


core.events 
-----------
.. automodule:: core.events

.. _EventHandler:

EventHandler
^^^^^^^^^^^^
The EventHandler object is a flexible class to manage any object's callbacks. The primary useage is to send updates from the :ref:`Graph` object to the :ref:`SceneEventHandler` object.

To create a signal, simply create an object and add an EventHandler as an attribute. Make sure to pass the parent object as the first object as the parent is **always** the first argument passed to the callback functions.


.. testsetup::
    
    from SceneGraph.core.events import EventHandler

.. testcode::
    
    from SceneGraph.core.events import EventHandler
    from SceneGraph.core.graph import Graph

    g = Graph()
    g.evaluated = EventHandler(g)


    # create a callback function
    def evaluatedCallback(graph, evaluated):
        if evaluated:
            print '# graph evaluated.'

    # create a callback function
    def anotherCallback(graph, evaluated):
        if evaluated:
            print '# graph nodes: ', len(graph.nodes())

    # connect the callbacks to the handler
    g.evaluated += evaluatedCallback
    g.evaluated += anotherCallback


Calling the signal runs any connected callbacks:

.. testcode::

    # call the signal to update all of the connected functions
    g.evaluated(True)


.. testoutput::

    # graph evaluated.
    # graph nodes:  0


To temporarily block the callback from signalling its observers, call the :func:`EventHandler.blockSignals() <core.events.EventHandler.blockSignals>` method:

.. testcode::
    
    g.evaluated.blockSignals(True)


.. autoclass:: EventHandler
    :members: