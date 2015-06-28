#!/usr/bin/env python
from SceneGraph.core import log


class NodeManager(object):
	def __init__(self, parent):
		self.graph = parent

	def updateGraph(self, msg):
		print '[NodeManager]: %s' % msg