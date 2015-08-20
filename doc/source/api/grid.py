 #!/usr/bin/env python
 from SceneGraph.core.graph import Grid
 g = Grid(10, 10, width=100, height=100)
 print g.coords
 g.next()
 print g.coords