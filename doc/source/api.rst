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


.. _Metadata:

Metadata
--------
The Metadata parses node metadata on disk.

.. autoclass:: Metadata
    :members:


Events & Observables
====================
.. automodule:: core.observable
.. autoclass:: Observable
    :members:

.. _Observable:

Observable
----------

The Observable class is the basis of all of our core node types, providing simple callbacks.

.. automodule:: core.events

.. _Event:

Event
-----
Event base class.

.. autoclass:: Event
    :members:

NodePositionChanged
-------------------
Called when a DagNode's position is updated.

.. autoclass:: NodePositionChanged
    :members:

NodeNameChanged
---------------
Called when a DagNode's name changes.

.. autoclass:: NodeNameChanged
    :members:

AttributeUpdatedEvent
---------------------
Generic DagNode attribute changed event.

.. autoclass:: AttributeUpdatedEvent
    :members:

MouseHoverEvent
---------------
**Qt**: Mouse hover event.

.. autoclass:: MouseHoverEvent
    :members:

MouseMoveEvent
--------------
**Qt**: Mouse move event.

.. autoclass:: MouseMoveEvent
    :members:

MousePressEvent
---------------
**Qt**: Mouse button press event.


.. autoclass:: MousePressEvent
    :members:

UI Modules
==========

.. automodule:: ui

.. _SceneHandler:

SceneHandler
------------
The SceneHandler connects the Graph to the UI

.. autoclass:: SceneHandler
    :members:

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

.. automodule:: ui.node_widgets
.. autoclass:: NodeWidget
    :members:


NodeLabel
^^^^^^^^^
The NodeLabel draws the node name.

.. autoclass:: NodeLabel
    :members:

.. _NodeBackground:

NodeBackground
^^^^^^^^^^^^^^
The :ref:`NodeBackground` draws the node background.

.. autoclass:: NodeBackground
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


Utilities
=========

.. _utils:

.. automodule:: util
