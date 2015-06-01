#### branch: master

##### Usage:

###### Maya:

	from SceneGraph import SceneGraph
	sgui=SceneGraph.SceneGraph()
	sgui.show()
	
	# work with the graph
	from SceneGraph.core import nodes
	
	# access the node graph
	graph = sgui.graph

	# return a named node
	node = graph.getNode('node1')

	# get node attributes
	node.getNodeAttributes()
		
	# set arbitrary attributes
	node.setNodeAttributes(env='maya', version='2014')


##### Dependencies:

- simplejson
- NetoworkX 1.9.1