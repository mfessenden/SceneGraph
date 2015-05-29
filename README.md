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
	
	# access the root node
	root = graph.root_node
	
	# select it
	root.setSelected(True)
	
	# get node attributes
	node.getNodeAttributes()
	
	# return a named node
	node = graph.getNode('node1')
	
	# set arbitrary attributes
	node.setNodeAttributes(env='maya', version='2014')


##### Dependencies:

- simplejson