#### branch: development

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
	dags = graph.getNodes()

	# return a named dag node
	dagnode = graph.getNode('node1')

	# get node attributes
	dagnode.getNodeAttributes()
		
	# set arbitrary attributes
	dagnode.setNodeAttributes(env='maya', version='2014')


###### API:

	# create a graph
	from SceneGraph import core
	g=core.Graph()

	# add some default nodes
	n1 = g.addNode('default', name='node1')
	n2 = g.addNode('default', name='node2')

	# connect the nodes (default output/inputs assumed)
	e1 = g.addEdge(n1, n2)

	# connect with a connection string
	e1 = g.connectNodes('node1.output', 'node2.input')

	# write the graph
	g.write('~/my_graph.json')

	# query all nodes in the graph
	print g.getDagNodes()

	# query all node names
	print g.allNodes()

	# query all connections
	print g.allConnections()


####### Advanced API:

	# add attributes to a dag node, flag it as an input connection
	n1.addAttr(name='env', value='maya', input=True)




##### Dependencies:

- simplejson
- NetworkX 1.9.1
- matplotlib