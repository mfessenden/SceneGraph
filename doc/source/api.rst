==============
SceneGraph API
==============

The SceneGraph API allows you to interact with graphs without using the UI.

Core Modules
============

.. _Graph:

Graph
-----

The Graph class is a wrapper for a networkx.MultiDiGraph graph.

.. automodule:: core.graph
.. autoclass:: Graph
    :members:

.. _PluginManager:

PluginManager
-------------
The PluginManager manages how SceneGraph finds and loads plugins.


.. automodule:: core.plugins
.. autoclass:: PluginManager
    :members:

.. _MetadataParser:

MetadataParser
--------------
The MetadataParser reads and translates metadata to the widget.


.. automodule:: core.metadata
.. autoclass:: MetadataParser
    :members:


Core Nodes
==========
.. automodule:: core.nodes

.. _SimpleNode:

SimpleNode
----------
The SimpleNode class contains basic DAG node attributes.

.. autoclass:: SimpleNode
    :members:

.. _DagNode:

DagNode
-------
The DagNode class is the base class for all nodes.

.. autoclass:: DagNode
    :members:


UI Modules
==========

.. automodule:: ui


StylesheetManager
-----------------
The StylesheetManager parses stylesheets and font/color preferences.

.. autoclass:: StylesheetManager
    :members:

.. _NodeWidget:

NodeWidget
----------
The NodeWidget is the base class for node widgets. NodeWidgets are custom QtGui.QGraphicsObjects that contain a reference to their referenced DagNode. The NodeWidget *must* be instantiated with the DagNode as the first argument:

::

    g = core.Graph()
    dag = g.add_node('default')
    widget = NodeWidget(dag)


The NodeWidget reads its base attributes from the DagNode, and conversely, updates are passed back to the DagNode.

.. autoclass:: NodeWidget
    :members:


EdgeWidget
----------
The EdgeWidget is the base class for edge widgets.

.. autoclass:: EdgeWidget
    :members:


Connection
----------
The Connection defines connections between nodes.

.. autoclass:: Connection
    :members: