#!/usr/bin/env python
from . import logger
log = logger.myLogger()


from . import attributes
from . import nodes
from . import manager
from . import metadata


# attributes
Attribute           = attributes.Attribute


# nodes
DagNode             = nodes.DagNode
DagEdge             = nodes.DagEdge
Connection          = nodes.Connection


# Observers/Managers
NodeManager         = manager.NodeManager
DataParser          = metadata.DataParser 


# Plugin Manager
from . import plugins
PluginManager       = plugins.PluginManager


from . import graph
# graph class
Graph               = graph.Graph
