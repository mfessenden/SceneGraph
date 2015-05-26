#### branch: master

##### Usage:

###### Maya:

	from SceneGraph import SceneGraph
	sgui=SceneGraph.SceneGraph()
	sgui.show()
	
	# work with the graph
	from SceneGraph.core import nodes
	
	# access the node manager
	nodemgr = sgui.nodeManager
	
	# access the root node
	root = nodemgr.root_node
	
	# select it
	root.setSelected(True)
	
	# get node attributes
	node.getNodeAttributes()
	
	# return a named node
	node=nodemgr.getNode('Node1')
	
	# set arbitrary attributes
	node.setNodeAttributes(env='maya', version='2014')


##### Dependencies:

- simplejson