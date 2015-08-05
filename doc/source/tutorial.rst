========
Tutorial
========

Getting started
===============

To start using SceneGraph, simply run the appropriate launcher from a shell. For Linux & OSX, run the **/bin/SceneGraph** launcher, for Windows run **/bin/SceneGraph.bat**.

DCC Applications
----------------

SceneGraph contains modules for Maya, Nuke & Houdini (todo).

Maya
^^^^
::

    from SceneGraph import scenegraph_maya
    scenegraph_maya.main()


Nuke
^^^^
::

    from SceneGraph import scenegraph_nuke
    scenegraph_nuke.main()


Other Applications
^^^^^^^^^^^^^^^^^^
To use SceneGraph in another application, simply import the UI from the standard module: 
::

    from SceneGraph import scenegraph
    sgui = scenegraph.SceneGraphUI()
    sgui.show()

Node Types
==========

Default
-------

Merge
-----

Note
-----

Dot
---

Creating Nodes
==============

There are several ways to create a node in the graph:

- right-click the mouse in the graph area to open the **Add node** menu.
- press the **tab button** to open the **Add node** menu.
- choose a node type from the **Nodes>Add node** menu.

Choose a node type and it will be placed near where your mouse is positioned.

.. image:: ../images/add_node_menu.png

Connecting Nodes
================

To connect two nodes, click on a green output terminal of one node, and drag the mouse to the yellow input terminal of another node.

.. image:: ../images/drag_edge01.png

Saving & Loading Scenes
=======================

Saving and loading is managed through the **File** menu. If the user attempts to close the application when a file has not been saved, they will be prompted to close the appliation without saving.

Autosaving
----------
**SceneGraph** autosaves after a predetermined amount of time. If the user attempts to open a scene that has a newer autosave, they will be prompted to choose opening either the original, or the autosave file (useful in the event of a crash).

Attribute Editor
================

Keyboard Commands
=================

+------------+------------+-----------+-------------------------------+
| Key        | Modifier   | Modifier  | Description                   |
+============+============+===========+===============================+ 
| A          |            |           | fit all nodes in the graph    |
+------------+------------+-----------+-------------------------------+
| D          |            |           | disable selected nodes        |
+------------+------------+-----------+-------------------------------+
| E          |            |           | toggle edge types             |
+------------+------------+-----------+-------------------------------+
| F          |            |           | fit selected nodes in graph   |
+------------+------------+-----------+-------------------------------+
| Tab        |            |           | open the **Add node** menu    |
+------------+------------+-----------+-------------------------------+
| Option     |            |           | split edge with a dot node*   |
+------------+------------+-----------+-------------------------------+
| O          | Ctrl       |           | open a scene from disk        |
+------------+------------+-----------+-------------------------------+
| S          | Ctrl       |           | save the current scene        |
+------------+------------+-----------+-------------------------------+
| Z          | Ctrl       |           | undo the last action          |
+------------+------------+-----------+-------------------------------+
| Z          | Ctrl       | Shift     | redo the last action          |
+------------+------------+-----------+-------------------------------+

\* mouse must be hovering over the middle of an edge.


Plugins
=======

Node types are loaded as plugins. New plugins can be added via the SCENEGRAPH_PLUGIN_PATH_. variable.

.. _SCENEGRAPH_PLUGIN_PATH_:

Enabling/disabling plugins
--------------------------

To open the :ref:`PluginManager`, select the **Windows>Plugins...** menu.

.. image:: ../images/plugins_menu.png

The **PluginManager** interface allows the user to enable, disable or load new plugins. The current plugin configuration will be saved to the user's preferences, so on the next launch, **SceneGraph** will only load the current plugins.

.. image:: ../images/plugins_manager.png

Extending SceneGraph
====================

Environment Variables
---------------------

SCENEGRAPH_PLUGIN_PATH
^^^^^^^^^^^^^^^^^^^^^^

SCENEGRAPH_CONFIG_PATH
^^^^^^^^^^^^^^^^^^^^^^

SCENEGRAPH_STYLESHEET_PATH
^^^^^^^^^^^^^^^^^^^^^^^^^^

Writing your own plugins
------------------------

To write your own plugins, you'll need three things:

- DagNode object file
- NodeWidget object file
- Metadata attribute description file (optional)

You'll need to subclass the default :ref:`DagNode` object type, as well as a corresponding widget type.


Plugin Files
^^^^^^^^^^^^

Metadata Description Files
^^^^^^^^^^^^^^^^^^^^^^^^^^
The metadata is used to describe your node's parameters to the application. You'll need to define attributes and groups. Private attributes will not show in the UI by default. Each node will inherit all of its parent classes metadata descriptors, so you won't have to manage parent attributes unless you choose to.

::

    # dot node attributes
    [group Node Transform]

        [attr width]
            default             FLOAT     8.0
            required            BOOL      true
            private             BOOL      true   

        [attr radius]
            default             FLOAT    8.0
            label               STRING   "dot radius"
            required            BOOL     true


The above metadata is the builtin **Dot** node's description. Rendered in the **AttributeEditor**, it looks like this:

.. image:: ../images/attr_editor_dot.png

Under the **Node Transform** group, we see the **Position** attribute. That attribute is inherited from the parent :ref:`DagNode` object. If we add it to the descriptor above and set the **private** paremeter, it will no longer render in the **AttributeEditor**:

::

    # dot node attributes
    [group Node Transform]

        [attr pos]
            private             BOOL      true

        [attr width]
            default             FLOAT     8.0
            required            BOOL      true
            private             BOOL      true   

        [attr radius]
            default             FLOAT    8.0
            label               STRING   "dot radius"
            required            BOOL     true


The **group** determines which group the attributes will be grouped under. Note that the **width** attribute is not shown, while the **radius** is. Setting the **width.private** paramenter to **false** will allow the user to change it. 

Warning: exposing private :ref:`DagNode` attributes can lead to system unstability. It is strongly recommended that you do not do that.

Preferences
===========

**SceneGraph** includes a robust preferences system. Users can save and load UI layouts, as well as customize the graph drawing style to suit their preference.

Render FX
---------
Unchecking this will turn off FX like dropshadows and glows on nodes, labels and edges. Can be used to increase draw performance.

.. image:: ../images/render_fx.png

Viewport Mode
-------------

Changing the drawing style can increase draw performance. Options are **full**, **smart** and **minimal**. **Full** will look best, while **minimal** will draw faster, but might briefly display some artifacts when updating the scene. **Smart** is the default.

Edge Types
----------

Edges can be rendered as **bezier** or **polygon**. Use polygon mode to increase draw performance.

.. image:: ../images/edge_type.png

OpenGL
------

Enable the **OpenGL** option to use OpenGL to render the node graph. 

Stylesheets
-----------

Layouts
-------

Autosave
--------