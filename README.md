#### branch: master

##### Usage:

###### Maya:

	from SceneGraph import SceneGraph
	sgui=SceneGraph.SceneGraph()
	sgui.show()
	
	# access the node graph
	graph = sgui.graph

	# list all node names
	node_names = graph.listNodeNames()

	# get all of the nodes (widgets)
	nodes = graph.getNodes()

	# get all of the nodes (dag nodes)
	dags = graph.getDagNodes()

	# return a named dag node
	node = graph.getDagNode('node1')

	# get node attributes
	node.getNodeAttributes()
		
	# set arbitrary attributes
	node.setNodeAttributes(env='maya', version='2014')


##### Dependencies:

- simplejson
- NetoworkX 1.9.1