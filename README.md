#### branch: master

##### Usage:

###### Maya:

	from SceneGraph import scenegraph
	sgui = scenegraph.SceneGraphUI()
	sgui.show()
	
	# access the node graph
	graph = sgui.graph

	# list all node names
	node_names = graph.listNodeNames()

	# get all of the nodes (widgets)
	nodes = graph.getSceneNodes()

	# get all of the nodes (dag nodes)
	dags = graph.getDagNodes()

	# return a named dag node
	dagnode = graph.getDagNode('node1')

	# get node attributes
	dagnode.getNodeAttributes()
		
	# set arbitrary attributes
	dagnode.setNodeAttributes(env='maya', version='2014')


###### API:

	# create a graph
	from SceneGraph import core
	g=core.Graph()

	# add a node
	node=g.addNode('default')

##### Dependencies:

- simplejson
- NetworkX 1.9.1