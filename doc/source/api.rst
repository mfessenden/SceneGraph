SceneGraph API
==============

The SceneGraph API allows you to interact with graphs without using the UI.

Graph
-----
The Graph class is a wrapper for a networkx.MultiDiGraph graph.

.. automodule:: core.graph
.. autoclass:: Graph
    :members:

.. automodule:: core.nodes


DAG Nodes
---------

SimpleNode
^^^^^^^^^^
The SimpleNode class contains basic DAG node attributes.

.. autoclass:: SimpleNode
    :members:

.. _DagNode:

DagNode
^^^^^^^
The DagNode class is the base class for all nodes.

.. autoclass:: DagNode
    :members:

.. automodule:: ui

Qt Graphics
-----------
Custom QGraphics classes for managing nodes.


GraphicsView
^^^^^^^^^^^^
The GraphicsView class is a custom QGraphicsView.

.. autoclass:: GraphicsView
    :members:

GraphicsScene
^^^^^^^^^^^^^
The GraphicsScene class is a custom QGraphicsView.

.. autoclass:: GraphicsScene
    :members:

.. _GraphicsScene:

Widgets
-------
Node/Edge widgets.

NodeWidget
^^^^^^^^^^
.. autoclass:: NodeWidget
    :members:

EdgeWidget
^^^^^^^^^^
.. autoclass:: EdgeWidget
    :members:

Connection
^^^^^^^^^^
.. autoclass:: Connection
    :members:

Scene Handler
-------------
The SceneHandlder is responsible from sending and recieving signals from the API to the UI.

SceneHandler
^^^^^^^^^^^^
.. autoclass:: SceneHandler
    :members:

Attribute Editor
----------------
The node AttributeEditor is a dynamically-generated UI that allows the user to display, add & edit node properties.

AttributeEditor
^^^^^^^^^^^^^^^
.. autoclass:: AttributeEditor
    :members:

Undo/Redo Commands
------------------
Commands to handle undo & redo in the UI.

SceneNodesCommand
^^^^^^^^^^^^^^^^^
.. autoclass:: SceneNodesCommand
    :members:

SceneChangedCommand
^^^^^^^^^^^^^^^^^^^
.. autoclass:: SceneChangedCommand
    :members:

Stylesheet Manager
------------------
The Stylesheet manager manages the application stylesheets, and dynamically substitutes user-defined font & color preferences.

StylesheetManager
^^^^^^^^^^^^^^^^^
.. autoclass:: StylesheetManager
    :members:


.. automodule:: ui.PluginManager

PluginManager
-------------
.. _PluginManager:

PluginManager
^^^^^^^^^^^^^

.. autoclass:: PluginManager
    :members:
