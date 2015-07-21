#!/usr/bin/env python
from collections import OrderedDict as dict
from PySide import QtCore, QtGui
from SceneGraph import util
from SceneGraph.core import log, MetadataParser
from SceneGraph.options import SCENEGRAPH_STYLESHEET_PATH, PLATFORM


class AttributeEditor(QtGui.QWidget):

    def __init__(self, parent=None, **kwargs):
        super(AttributeEditor, self).__init__(parent)
        from SceneGraph.icn import icons

        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

        self._nodes         = []
        self._sections      = []        # node metadata sections
        
        self._ui            = kwargs.get('ui')
        self._handler       = kwargs.get('handler', None)
        self._show_private  = self._ui._show_private
        self._graph         = self._handler.graph    
        self._add_dialog    = None
        self.icons          = self._handler.icons

        
        self.fonts          = self._ui.fonts

        self.setObjectName("AttributeEditor")
        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setContentsMargins(1, 1, 1, 1)

        self.mainGroup = QtGui.QGroupBox(self)
        self.mainGroup.setObjectName("mainGroup")
        self.mainGroup.setProperty("class", "AttributeEditor") 
        self.mainGroup.setFont(self.fonts.get("attr_editor"))
        self.mainGroup.setFlat(True)

        self.mainGroupLayout = QtGui.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.setObjectName("mainGroupLayout")
        self.mainGroupLayout.setContentsMargins(5, 15, 5, 5)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.createContextMenu)
        
        # setup the main interface
        self.initializeUI()
        self.connectSignals()      
        self.setFont(self.fonts.get("ui"))

    def initializeUI(self):
        """
        Initialize/reset the UI.
        """
        self.mainGroup.setHidden(True)
        self.clearLayout(self.mainGroupLayout)
        self._nodes = []       

    def initializeStylesheet(self):
        """
        Setup the stylehsheet.
        """
        import os        
        self.stylesheet = os.path.join(SCENEGRAPH_STYLESHEET_PATH, 'stylesheet.css')
        ssf = QtCore.QFile(self.stylesheet)
        ssf.open(QtCore.QFile.ReadOnly)
        self.setStyleSheet(str(ssf.readAll()))
        ssf.close()

    def buildLayout(self, verbose=False):
        """
        Build the layout dynamically
        """
        user_attributes = self.getUserAttributes()
        if user_attributes:
            self._sections.append("User")

        for section in self._sections:            
            
            group = QtGui.QGroupBox(self.mainGroup)
            group.setFont(self.fonts.get("attr_editor_group"))
            group.setTitle('%s' % section)
            group.setFlat(True)
            group.setObjectName("%s_group" % section)

            # build a formlayout
            formLayout = QtGui.QFormLayout(group)
            #formLayout.setFormAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            formLayout.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            formLayout.setObjectName("%s_group_layout" % section)
            formLayout.setContentsMargins(9, 15, 9, 9)

            # grab data from the metadata parser
            row = 0
            if section != 'User':
                attrs = self.getNodeSectionAttrs(section)
            else:
                attrs = user_attributes

            for attr_name, attr_attrs in attrs.iteritems():

                private = attr_attrs.get('private', False)
                attr_label = attr_attrs.get('label', None)
                desc = attr_attrs.get('desc', None)
                edges = attr_attrs.get('_edges', [])

                # use label from metadata, if available
                if not attr_label:
                    attr_label = attr_name

                if not private or self._show_private:

                    if 'attr_type' not in attr_attrs:
                        log.debug('attribute "%s.%s" has no type.' % (self._nodes[0].name, attr_name))
                        continue

                    attr_type = attr_attrs.get('attr_type')
                    log.info('building %s attribute: "%s"' % (attr_type, attr_name))

                    default_value = attr_attrs.get('default_value', None)

                    # map the correct editor widget
                    if attr_type is not None:
                        editor = map_widget(attr_type, parent=group, name=attr_name, ui=self, icons=self.icons)

                        if editor:
                            editor.setFont(self.fonts.get("attr_editor"))
                            if editor:
                                editor.initializeEditor()

                                formLayout.addRow("%s:" % attr_label, editor)
                                label_widget = formLayout.itemAt(row, QtGui.QFormLayout.LabelRole)

                                label = label_widget.widget()
                                label.setFont(self.fonts.get("attr_editor_label"))
                                formLayout.setAlignment(label, QtCore.Qt.AlignVCenter)
                                # add the description
                                if desc is not None:
                                    editor.setToolTip(desc)
                                    #attr_label.setToolTip(desc)
                                    
                                # signal here when editor changes
                                editor.valueChanged.connect(self.nodeAttributeChanged)
                                #editor.setEnabled(not locked)

                                # connected edges
                                if edges:
                                    for edge in edges:
                                        src_id, dest_id = edge.strip('()').split(',')
                                        if self._graph.get_edge(src_id, dest_id):
                                            src_id, dest_id, edge_attrs = self._graph.get_edge(src_id, dest_id)[0]
                                            dagnode = self._graph.get_node(src_id)[0]
                                            conn_str = '%s.%s' % (dagnode.name, edge_attrs.get('src_attr'))
                                            print 'connection: ', conn_str
                                            editor.setConnected(conn_str)

                                row += 1
                        else:
                            print 'No editor for type: "%s"' % attr_type
                    else:
                        print 'Attribute: "%s" has a type of: ' % attr_name, attr_type

            if row:
                self.mainGroupLayout.addWidget(group)
            else:
                group.deleteLater()
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.mainGroupLayout.addItem(spacerItem)
        self.mainLayout.addWidget(self.mainGroup)
        self.mainGroup.setHidden(False)

        group_title = self.getNodeGroupTitle()
        self.mainGroup.setTitle(group_title)
        self.initializeStylesheet()

    def updateChildEditors(self, attributes=[]):
        """
        Refresh the current editors. Optionally
        update certain named attributes (default is all)

        params:
            attributes (list) - list of attribute strings.
        """
        editors = self.childEditors()

        # add new attributes here
        if attributes:
            editors = []
            for attribute in attributes:
                editor = self.getEditor(attribute)
                if editor:
                    editors.append(editor)

        if editors:
            editors = list(set(editors))

            for e in editors:
                e.initializeEditor()



    def sizeHint(self):
        return QtCore.QSize(270, 550)

    def connectSignals(self):
        pass

    def createContextMenu(self):
        """
        Build a context menu at the current pointer pos.

        params:
            parent (QWidget) - parent widget.
        """
        popup_menu = QtGui.QMenu(self)
        popup_menu.clear()
        qcurs = QtGui.QCursor()
        add_action = QtGui.QAction('Add attribute', self) 
        add_action.triggered.connect(self.launchAddAttributeDialog)

        popup_menu.addAction(add_action)
        popup_menu.exec_(qcurs.pos())

    #- Events -----
    def nodeAttributeChanged(self, editor):
        """
        Runs when a child editor updates a node value.

        params:
            editor (QWidget) - node editor widget.

        returns:
            (list) - list of dag node objects that have been updated.
        """
        updated_nodes = []
        for node in self.nodes:
            if hasattr(node, editor.attribute):
                cur_val = getattr(node, editor.attribute)
                if cur_val != editor.value:
                    #print '# DEBUG: setting "%s": "%s": ' % (node.name, editor.attribute), editor.value
                    setattr(node, editor.attribute, editor.value)
                    updated_nodes.append(node)
        
        # update graph
        self.handler.dagNodesUpdatedAction(updated_nodes)
        return updated_nodes

    def launchAddAttributeDialog(self):
        """
        Launch the add attribute dialog.
        """
        try:
            self._add_dialog.close()
        except:
            self._add_dialog = AddAttributeDialog(self, nodes=self._nodes)
            self._add_dialog.show()

    @property
    def nodes(self):
        return self._nodes

    def nodeValues(self, attr):
        """
        Returns a list of values for the given attribute.

        params:
            attr (str) - attribute to query for each node.
        """
        # set the nodes
        node_values = []
        for n in self.nodes:
            if hasattr(n, attr):
                cur_val = getattr(n, attr)
                if cur_val not in node_values:
                    node_values.append(cur_val)
        return node_values

    @property
    def handler(self):
        return self._handler
        
    def setNodes(self, dagnodes, clear=False):
        """
        Add nodes to the current editor.

        params:
            dagnodes (list) - list of dag node objects.
        """
        self._sections=[]
        if clear:
            self._nodes = []

        for d in dagnodes:
            for section in d.metadata.sections():
                if section not in self._sections:
                    self._sections.append(section)

        self._nodes = dagnodes
        self.clearLayout(self.mainGroupLayout)
        self.buildLayout()

    def getUserAttributes(self):
        """
        Return the current user attribute data from the nodes.

        returns:
            (dict) - dictionary of user attributes.
        """
        attributes = dict()
        for node in self._nodes:
            for name in node._attributes:

                attribute = node._attributes.get(name)

                if attribute.user:
                    print '# user attribute: "%s"' % name
                    if name not in attributes:
                        attributes[name] = dict()

                    for pname, pval in attribute.data.iteritems():
                        if pname not in attributes.get(name):
                            print '# adding user property: "%s": %s' % (pname, pval)
                            attributes.get(name)[pname]=pval

        return attributes

    def getNodeSectionAttrs(self, section):
        """
        Return the current section data from the nodes.

        params:
            section (str) - node metadata section name.

        returns:
            (dict) - dictionary of section sub-attributes.
        """
        result = dict()
        for node in self._nodes:
            if section in node.metadata.data:

                attributes = node.metadata.data.get(section)

                for attribute in attributes:

                    if attribute not in result:
                        properties = attributes.get(attribute)
                        attr_dict = dict()
                        print '%s properties: ' % attribute, properties.keys()
                        # TODO: need to figure this out
                        attr_dict['attr_type'] = properties.get('type', None)
                        attr_dict['default_value'] = properties.get('value', None)

                        #print

                        if 'default' in properties:
                            defaults = properties.get('default')
                            attr_dict['attr_type'] = defaults.get('type')
                            attr_dict['default_value'] = defaults.get('value')


                        attr_dict['private'] = properties.get('private', False)
                        attr_dict['label'] = properties.get('label', {}).get('value', None)
                        attr_dict['desc'] = properties.get('desc', {}).get('value', None)
                        attr_dict['_edges'] = properties.get('_edges', [])
                        
                        
                        # need: private, label, desc, _edges
                        result[attribute] = attr_dict
        return result

    def getNodeGroupTitle(self):
        """
        Returns a title string for the main attribute group.
        """
        # update the main group title
        node_types = list(set([x.node_type for x in self._nodes]))
        node_type = None
        group_title = '( %d nodes )' % len(self._nodes)
        if len(node_types) == 1:
            node_type = node_types[0]
            group_title = '( %d %s nodes )' % (len(self._nodes), node_type)

        if len(self._nodes) == 1:
            group_title = '%s: %s:' % (node_type, self._nodes[0].name)
        return group_title

    def childEditors(self):
        """
        Returns all of the current child editor widgets.

        returns:
            (list) - list of node editor widgets.
        """
        editors = []
        for w in self.findChildren(QtGui.QWidget):
            if hasattr(w, 'nodes'):
                editors.append(w)
        return editors

    def getEditor(self, attribute):
        """
        Return a named editor widget.

        params:
            attribute (str) - attribute name.

        returns:
            (QWidget) - attribute editor widget.
        """
        for editor in self.childEditors():
            if hasattr(editor, 'attribute'):
                if editor.attribute == attribute:
                    return editor
        return

    def clearLayout(self, layout):
        """
        Removes all of the child layouts/widgets
        """
        while layout.count():
            child = layout.takeAt(0)
            if child.widget() is not None:
                child.widget().deleteLater()
            elif child.layout() is not None:
                self.clearLayout(child.layout())


class AddAttributeDialog(QtGui.QDialog):

    def __init__(self, parent=None, nodes=[]):
        QtGui.QDialog.__init__(self, parent)

        self._nodes     = nodes

        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.setObjectName("mainLayout")
        self.mainLayout.setContentsMargins(6, 6, 6, 6)

        # main group
        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setObjectName("groupBox")
        self.groupBoxLayout = QtGui.QFormLayout(self.groupBox)
        self.groupBoxLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.groupBoxLayout.setFormAlignment(QtCore.Qt.AlignCenter)
        self.groupBoxLayout.setObjectName("groupBoxLayout")
        self.groupBox.setProperty("class", "AttributeEditor")
        self.groupBoxLayout.setContentsMargins(3, 15, 3, 3)

        # name editor
        self.nameLabel = QtGui.QLabel(self.groupBox)
        self.nameLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.nameLabel.setObjectName("nameLabel")
        self.groupBoxLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.nameLabel)
        self.nameLineEdit = QtGui.QLineEdit(self.groupBox)
        self.nameLineEdit.setObjectName("nameLineEdit")
        self.groupBoxLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.nameLineEdit)
        
        # id (nyi)
        self.iDLabel = QtGui.QLabel(self.groupBox)
        self.iDLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.iDLabel.setObjectName("iDLabel")
        self.groupBoxLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.iDLabel)
        self.iDLineEdit = QtGui.QLineEdit(self.groupBox)
        self.iDLineEdit.setObjectName("iDLineEdit")
        self.groupBoxLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.iDLineEdit)
        
        # attribute type
        self.typeLabel = QtGui.QLabel(self.groupBox)
        self.typeLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.typeLabel.setObjectName("typeLabel")
        self.groupBoxLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.typeLabel)
        self.typeComboBox = QtGui.QComboBox(self.groupBox)
        self.typeComboBox.setObjectName("typeComboBox")
        self.groupBoxLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.typeComboBox)
        self.checkbox_connectable = QtGui.QCheckBox(self.groupBox)
        self.checkbox_connectable.setObjectName("checkbox_connectable")
        self.groupBoxLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.checkbox_connectable)
        
        # connection type
        self.connectionTypeLabel = QtGui.QLabel(self.groupBox)
        self.connectionTypeLabel.setMinimumSize(QtCore.QSize(110, 0))
        self.connectionTypeLabel.setObjectName("connectionTypeLabel")
        self.groupBoxLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.connectionTypeLabel)
        self.connectionTypeMenu = QtGui.QComboBox(self.groupBox)
        self.connectionTypeMenu.setObjectName("connectionTypeMenu")
        self.groupBoxLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.connectionTypeMenu)
        self.mainLayout.addWidget(self.groupBox)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.mainLayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.mainLayout.addWidget(self.buttonBox)

        # signals/slots
        self.checkbox_connectable.toggled.connect(self.connectionTypeMenu.setVisible)
        self.checkbox_connectable.toggled.connect(self.connectionTypeLabel.setVisible)
        self.buttonBox.accepted.connect(self.acceptedAction)
        self.buttonBox.rejected.connect(self.close)
        self.initializeUI()

    def initializeUI(self):
        """
        Set up the main UI.
        """
        self.setWindowTitle("Add Node Attribute")
        self.groupBox.setTitle("Create Attribute")
        self.nameLabel.setText("Name:")
        self.iDLabel.setText("ID:")
        self.typeLabel.setText("Type:")
        self.checkbox_connectable.setText('Connectable:')
        self.connectionTypeLabel.setText("Connection type:")

        self.typeComboBox.clear()
        self.typeComboBox.addItems(sorted(WIDGET_MAPPER.keys()))

        self.connectionTypeMenu.clear()
        self.connectionTypeMenu.addItems(['input', 'output'])

        self.connectionTypeMenu.setVisible(False)
        self.connectionTypeLabel.setVisible(False)

    def acceptedAction(self):
        """
        Runs when the OK button is clicked.
        """
        attr_name = self.nameLineEdit.text()
        attr_type = self.typeComboBox.currentText()
        def_value = ATTRIBUTE_DEFAULTS.get(attr_type)
        connectable = self.checkbox_connectable.isChecked()
        connection_type = self.connectionTypeMenu.currentText()
        if attr_name:
            for node in self._nodes:
                log.info('adding "%s" to node "%s" (%s)' % (attr_name, node.name, attr_type))
                node.add_attr(attr_name, value=def_value, attr_type=attr_type, connectable=connectable, 
                                connection_type=connection_type)

        #self.parent().updateChildEditors([attr_name])
        self.parent().clearLayout(self.parent().mainGroupLayout)
        self.parent().buildLayout()
        self.parent().handler.dagNodesUpdatedAction(self._nodes)
        self.close()

    def sizeHint(self):
        return QtCore.QSize(315, 190)

# -sub widgets ---

class QFloatEditor(QtGui.QWidget):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QFloatEditor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = 0.0
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QFloatLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return self.val1_edit.value

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value))
                self.val1_edit.blockSignals(False)
                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")


class QIntEditor(QtGui.QWidget):
    
    attr_type       = 'int'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QIntEditor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = 0
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QFloatLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return self.val1_edit.value

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value))
                self.val1_edit.blockSignals(False)
                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")


class QFloat2Editor(QtGui.QWidget):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QFloat2Editor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = (0,0)
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QFloatLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QFloatLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val2_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.value, self.val2_edit.value)

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)
                self.val2_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value[0]))
                self.val2_edit.setText(str(editor_value[1]))

                self.val1_edit.blockSignals(False)
                self.val2_edit.blockSignals(False)

                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val2_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val2_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")
            self.val2_edit.setProperty("class", "Connected")


class QFloat3Editor(QtGui.QWidget):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QFloat3Editor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = (0.0, 0.0, 0.0)

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QFloatLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QFloatLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

        # value 3 editor
        self.val3_edit = QFloatLineEdit(self)
        self.val3_edit.setObjectName("val3_edit")
        self.mainLayout.addWidget(self.val3_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val2_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val3_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.value, self.val2_edit.value, self.val3_edit.value)

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)
                self.val2_edit.blockSignals(True)
                self.val3_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value[0]))
                self.val2_edit.setText(str(editor_value[1]))
                self.val3_edit.setText(str(editor_value[2]))

                self.val1_edit.blockSignals(False)
                self.val2_edit.blockSignals(False)
                self.val3_edit.blockSignals(False)

                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val2_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val3_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val2_edit.setEnabled(False)
            self.val3_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")
            self.val2_edit.setProperty("class", "Connected")
            self.val3_edit.setProperty("class", "Connected")


class QInt2Editor(QtGui.QWidget):

    attr_type       = 'int'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QInt2Editor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = (0, 0)
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QIntLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QIntLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val2_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.value, self.val2_edit.value)

    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)
                self.val2_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value[0]))
                self.val2_edit.setText(str(editor_value[1]))

                self.val1_edit.blockSignals(False)
                self.val2_edit.blockSignals(False)

                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val2_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val2_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")
            self.val2_edit.setProperty("class", "Connected")


class QInt3Editor(QtGui.QWidget):

    attr_type       = 'int'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QInt3Editor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = False

        self._default_value = (0, 0, 0)
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QIntLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QIntLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

        # value 2 editor
        self.val3_edit = QIntLineEdit(self)
        self.val3_edit.setObjectName("val3_edit")
        self.mainLayout.addWidget(self.val3_edit)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val2_edit.setFont(self._ui.fonts.get("attr_editor"))
        self.val3_edit.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.value, self.val2_edit.value, self.val3_edit.value)

    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.value, self.val2_edit.value, self.val3_edit.value)

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)
                self.val2_edit.blockSignals(True)
                self.val3_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value[0]))
                self.val2_edit.setText(str(editor_value[1]))
                self.val3_edit.setText(str(editor_value[2]))

                self.val1_edit.blockSignals(False)
                self.val2_edit.blockSignals(False)
                self.val3_edit.blockSignals(False)

                self.val1_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val2_edit.valueChanged.connect(self.valueUpdatedAction)
                self.val3_edit.valueChanged.connect(self.valueUpdatedAction)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val2_edit.setEnabled(False)
            self.val3_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")
            self.val2_edit.setProperty("class", "Connected")
            self.val3_edit.setProperty("class", "Connected")


class QBoolEditor(QtGui.QCheckBox):

    attr_type       = 'bool'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(QBoolEditor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = False
        self._current_value = None

        self.toggled.connect(self.valueUpdatedAction)
        self.setFont(self._ui.fonts.get("attr_editor"))

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []      

    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return self.isChecked()

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.blockSignals(True)
                self.setChecked(editor_value)
                self.blockSignals(False)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.setEnabled(False)
            self.setProperty("class", "Connected")


class StringEditor(QtGui.QWidget):

    attr_type       = 'str'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(StringEditor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'array')
        self._connection    = None

        self._default_value = ""
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QtGui.QLineEdit(self)
        regexp = QtCore.QRegExp('^([a-zA-Z0-9_]+)')
        validator = QtGui.QRegExpValidator(regexp)
        self.val1_edit.setValidator(validator)

        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        self.val1_edit.textEdited.connect(self.validate_text)
        self.val1_edit.editingFinished.connect(self.valueUpdatedAction)
        self.val1_edit.returnPressed.connect(self.valueUpdatedAction)

        self.val1_edit.setFont(self._ui.fonts.get("attr_editor"))

    def validate_text(self, text):
        validator = self.val1_edit.validator()
        state, txt, pos = validator.validate(self.val1_edit.text(), 0)
        if state == QtGui.QValidator.State.Acceptable:
            pass
        if state == QtGui.QValidator.State.Invalid:
            print 'invalid: ', txt

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return str(self.val1_edit.text())

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value))
                self.val1_edit.blockSignals(False)                

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.val1_edit.setText(conn)
            self.val1_edit.setEnabled(False)
            self.val1_edit.setProperty("class", "Connected")


class FileEditor(QtGui.QWidget):

    attr_type       = 'file'
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(FileEditor, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self.icons          = kwargs.get('icons')
        self._attribute     = kwargs.get('name', 'file')
        self._connection    = None

        self._default_value = ""
        self._current_value = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(1, 1, 1, 1)
        self.mainLayout.setObjectName("mainLayout")
        
        self.file_edit = QtGui.QLineEdit(self)
        self.file_edit.setObjectName("file_edit")
        self.mainLayout.addWidget(self.file_edit)
        self.button_browse = QtGui.QToolButton(self)
        self.button_browse.setObjectName("button_browse")
        self.mainLayout.addWidget(self.button_browse)

        # set the completion model
        self._completer = QtGui.QCompleter(self)
        model = QtGui.QDirModel(self._completer)
        self._completer.setModel(model)
        self.file_edit.setCompleter(self._completer)

        self.button_browse.setAutoRaise(True)
        self.button_browse.setIcon(self.icons.get("folder_horizontal_open"))
        self.button_browse.clicked.connect(self.browseAction)

        self.mainLayout.setAlignment(self.file_edit, QtCore.Qt.AlignVCenter)
        self.file_edit.setFont(self._ui.fonts.get("attr_editor"))


    def browseAction(self):
        """
        Open a file dialog.
        """
        filename, filters = QtGui.QFileDialog.getOpenFileName(self, caption='Open file...', filter="All Files (*.*)")
        if not filename:
            return

        self.file_edit.setText(filename)
        self.valueUpdatedAction()

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    @property
    def value(self):
        """
        Get the current editor value.
        """
        return str(self.file_edit.text())

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return
        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.file_edit.blockSignals(True)

                # set the current node values.
                self.file_edit.setText(str(editor_value))
                self.file_edit.blockSignals(False)                

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.file_edit.setText(conn)
            self.file_edit.setEnabled(False)
            self.button_browse.setEnabled(False)
            self.file_edit.setProperty("class", "Connected")


class ColorPicker(QtGui.QWidget):
    """ 
    Color picker widget, expects an RGB value as an argument.
    """
    valueChanged    = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        super(ColorPicker, self).__init__(parent)

        self._ui            = kwargs.get('ui', None)
        self._attribute     = kwargs.get('name', 'color')
        self._connection    = None

        self._default_value = (125, 125, 125)
        self._current_value = None

        self.normalized     = kwargs.get('norm', False)
        self.min            = kwargs.get('min', 0)
        self.max            = kwargs.get('max', 99)
        self.color          = kwargs.get('color', [1.0, 1.0, 1.0])
        self.mult           = kwargs.get('mult', 0.1)

        # Env Attribute attrs
        self.attr           = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setContentsMargins(4, 2, 2, 2)
        self.mainLayout.setSpacing(1)

        # color swatch widget
        self.colorSwatch = ColorSwatch(self, color=self.color, norm=self.normalized )
        self.colorSwatch.setMaximumSize(QtCore.QSize(75, 20))
        self.colorSwatch.setMinimumSize(QtCore.QSize(75, 20))
        self.mainLayout.addWidget(self.colorSwatch)
        self.slider = QtGui.QSlider(self)

        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.mainLayout.addWidget(self.slider)
        self.colorSwatch.setColor(self.color)

        self.setMax(self.max)
        self.setMin(self.min)
        self.slider.setValue(self.max)

        # SIGNALS/SLOTS
        self.slider.valueChanged.connect(self.sliderChangedAction)
        self.colorSwatch.clicked.connect(self.colorPickedAction)
        self.slider.sliderReleased.connect(self.sliderReleasedAction)

        #print 'initial color: ', self.colorSwatch.color
        #print 'cached:        ', self._current_value

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        if self._ui is not None:
            if hasattr(self._ui, '_nodes'):
                return self._ui._nodes
        return []
    
    @property
    def value(self):
        """
        Returns the current color's RGB values.

        returns:
            (list) - rgb color values.
        """
        return self.colorSwatch.color

    @property
    def values(self):
        """
        Returns a list of the current node values.

        returns:
            (list) - list of node values for the editor's attribute.
        """
        if self._ui is not None:
            if hasattr(self._ui, 'nodeValues'):
                return self._ui.nodeValues(self.attribute)
        return []
    
    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, val):
        if val != self._default_value:
            self._default_value = val
            return True
        return False

    def initializeEditor(self):
        """
        Set the widgets nodes values.
        """
        if not self.nodes or not self.attribute:
            return

        editor_value = self.default_value

        node_values = self.values
        if node_values:
            if len(node_values) > 1:
                pass

            elif len(node_values) == 1:
                if node_values[0]:
                    editor_value = node_values[0]

                # set the editor value
                self.colorSwatch.setColor(editor_value)

    def valueUpdatedAction(self):
        """
        Update the current nodes with the revised value.
        """
        if self.value != self._current_value:
            self._current_value = self.value
            self.valueChanged.emit(self)

    def setConnected(self, conn):
        """
        Indicates the input is connected.
        """
        if conn != self._connection:
            self._connection = conn
            self.colorSwatch.setEnabled(False)

    def setAttr(self, val):
        # 32 is the first user data role
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr

    def _update(self):
        self.colorSwatch._update()

    def sliderChangedAction(self):
        """ 
        Set the value.
        """
        sval = float(self.slider.value())

        if not self._current_value:
            log.debug('caching color: (%d, %d, %d)' %(self.colorSwatch.color[0], self.colorSwatch.color[1], self.colorSwatch.color[2]))
            self._current_value = self.colorSwatch.color

        current_color = QtGui.QColor(*self._current_value)

        darker = 200-sval
        #print 'darker: ', darker
        new_color = current_color.darker(darker)
        self.colorSwatch.qcolor = new_color
        self.colorSwatch._update()

    def sliderReleasedAction(self):
        """
        Update the items' color when the slider handle is released.
        """
        color = self.colorSwatch.color        
        self.colorSwatch._update()
        self.valueUpdatedAction()

    def colorPickedAction(self):
        """ 
        Action to call the color picker.
        """
        dialog=QtGui.QColorDialog(self.colorSwatch.qcolor, self)
        if dialog.exec_():
            self.colorSwatch.setPalette(QtGui.QPalette(dialog.currentColor()))
            self.colorSwatch.qcolor=dialog.currentColor()

            ncolor=expandNormRGB((self.colorSwatch.qcolor.red(), self.colorSwatch.qcolor.green(), self.colorSwatch.qcolor.blue()))
            
            self.colorSwatch._update()
            self.valueUpdatedAction()

    def setMin(self, val):
        """
        Set the slider minimum value.

        params:
            val (int) - slider minimum.
        """
        self.min = val
        self.slider.setMinimum(val)

    def setMax(self, val):
        """
        Set the slider maximum value.

        params:
            val (int) - slider maximum.
        """
        self.max = val
        self.slider.setMaximum(val)

    def sizeHint(self):
        return QtCore.QSize(350, 27)

    def getQColor(self):
        return self.colorSwatch.qcolor

    def setColor(self, val):
        return self.colorSwatch.setColor(val)

    @property
    def rgb(self):
        return self.colorSwatch.qcolor.getRgb()[0:3]

    @property
    def rgbF(self):
        return self.colorSwatch.qcolor.getRgbF()[0:3]

    @property
    def hsv(self):
        return self.colorSwatch.qcolor.getHsv()[0:3]

    @property
    def hsvF(self):
        return self.colorSwatch.qcolor.getHsvF()[0:3]

#- Sub-Widgets ----

class ColorSwatch(QtGui.QToolButton):

    itemClicked = QtCore.Signal(bool)

    def __init__(self, parent=None, **kwargs):
        super(ColorSwatch, self).__init__(parent)

        self.normalized     = kwargs.get('norm', True)
        self.color          = kwargs.get('color', [1.0, 1.0, 1.0])
        self.qcolor         = QtGui.QColor()
        self.setColor(self.color)

    def setColor(self, color):
        """
        Set an RGB color value. 

        params:
            color (list) - list of rgb values.
        """
        rgbf = False
        if type(color[0]) is float:
            self.qcolor.setRgbF(*color)
            rgbf = True
            self.setToolTip("%.2f, %.2f, %.2f" % (color[0], color[1], color[2])) 
        else:
            self.qcolor.setRgb(*color)
            self.setToolTip("%d, %d, %d" % (color[0], color[1], color[2]))  
        self._update()
        return self.color

    def getColor(self):
        """
        Returns the current color's RGB values.

        returns:
            (list) - rgb color values.
        """
        return self.color

    def _update(self):
        """ 
        Update the widget color. 
        """
        self.color = self.qcolor.getRgb()[0:3]
        self.setStyleSheet("QToolButton{background-color: qlineargradient(spread:pad, \
            x1:0, y1:1, x2:0, y2:0, stop:0 rgb(%d, %d, %d), stop:1 rgb(%d, %d, %d))};" % 
            (self.color[0]*.45, self.color[1]*.45, self.color[2]*.45, self.color[0], self.color[1], self.color[2]))

    def _getHsvF(self):
        return self.qcolor.getHsvF()

    def _setHsvF(self, color):
        """
        Set the current color (HSV - normalized).

        params:
            color (tuple) - tuple of HSV values.
        """
        self.qcolor.setHsvF(color[0], color[1], color[2], 255)

    def _getHsv(self):
        return self.qcolor.getHsv()

    def _setHsv(self, color):
        """ 
        Set the current color (HSV).
        
        params:
            color (tuple) - tuple of HSV values (normalized).
        """
        self.qcolor.setHsv(color[0], color[1], color[2], 255)

    def getRGB(self, norm=True):
        """ 
        Returns a tuple of RGB values.

        params:
            norm (bool) - normalized color. 

        returns:
            (tuple) - RGB color values.
        """
        if not norm:
            return (self.qcolor.toRgb().red(), self.qcolor.toRgb().green(), self.qcolor.toRgb().blue())
        else:
            return (self.qcolor.toRgb().redF(), self.qcolor.toRgb().greenF(), self.qcolor.toRgb().blueF())


class QFloatLineEdit(QtGui.QLineEdit):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal(float)

    def __init__(self, parent=None, **kwargs):
        super(QFloatLineEdit, self).__init__(parent)

        self.returnPressed.connect(self.update)
        self.editingFinished.connect(self.update)

    @property
    def value(self):
        if not self.text():
            return 0.0
        return float(self.text())

    def setText(self, text):
        super(QFloatLineEdit, self).setText('%.2f' % float(text))

    def update(self):
        if self.text():
            self.setText(self.text())
        super(QFloatLineEdit, self).update()
        self.valueChanged.emit(float(self.text()))
        

class QIntLineEdit(QtGui.QLineEdit):

    attr_type       = 'int'
    valueChanged    = QtCore.Signal(int)

    def __init__(self, parent=None, **kwargs):
        super(QIntLineEdit, self).__init__(parent)

        self.returnPressed.connect(self.update)
        self.editingFinished.connect(self.update)

    @property
    def value(self):
        if not self.text():
            return 0
        return float(self.text())

    def setText(self, text):
        super(QIntLineEdit, self).setText('%s' % text)

    def update(self):
        if self.text():
            self.setText(self.text())        
        super(QIntLineEdit, self).update()
        self.valueChanged.emit(int(self.text()))


WIDGET_MAPPER = dict(
    float       = QFloatEditor,
    float2      = QFloat2Editor,
    float3      = QFloat3Editor,
    bool        = QBoolEditor,
    str         = StringEditor,
    string      = StringEditor,
    file        = FileEditor,
    dir         = FileEditor,
    int         = QIntEditor,
    int2        = QInt2Editor,
    int3        = QInt3Editor,
    int8        = QIntEditor,
    color       = ColorPicker,
    short2      = QFloat2Editor,
    )


ATTRIBUTE_DEFAULTS = dict(
    float       = 0.0,
    float2      = [0.0, 0.0],
    float3      = [0.0, 0.0, 0.0],
    bool        = False,
    str         = "",
    string      = "",
    file        = "",
    dir         = "",
    int         = 0,
    int2        = [0,0],
    int3        = [0,0,0],
    int8        = 0,
    color       = [172, 172, 172, 255],
    short2      = [0.0, 0.0],
    )


def map_widget(typ, parent, name, ui, icons):
    """
    Map the widget to the attribute type.
    """
    typ=typ.replace(" ", "")
    typ=typ.lower()
    if typ not in WIDGET_MAPPER:
        log.warning('invalid editor class: "%s" ("%s")' % (typ, name))
    if typ in WIDGET_MAPPER:
        cls = WIDGET_MAPPER.get(typ)
        return cls(parent, name=name, ui=ui, icons=icons)
    return


#- COLOR UTILITIES ----

def expandNormRGB(nrgb):
    return tuple([float(nrgb[0])*255, float(nrgb[1])*255, float(nrgb[2])*255])


def normRGB(rgb):
    return tuple([float(rgb[0])/255, float(rgb[1])/255, float(rgb[2])/255])


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))
