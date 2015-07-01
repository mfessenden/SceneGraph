#!/usr/bin/env python
from PySide import QtCore, QtGui
from SceneGraph import util
from SceneGraph.core import log


class AttributeEditor(QtGui.QWidget):

    def __init__(self, parent=None, **kwargs):
        super(AttributeEditor, self).__init__(parent)
        from SceneGraph.core import metadata
        reload(metadata)

        self._nodes         = []
        self._parser        = metadata.DataParser()
        self._show_private  = False

        self.setObjectName("AttributeEditor")
        self.mainLayout = QtGui.QVBoxLayout(self)
        self.mainLayout.setObjectName("mainLayout")
        self.mainGroup = QtGui.QGroupBox(self)
        self.mainGroup.setObjectName("mainGroup")
        #self.mainGroup.setFlat(True)
        self.mainGroupLayout = QtGui.QVBoxLayout(self.mainGroup)
        self.mainGroupLayout.setObjectName("mainGroupLayout")

        # setup the main interface
        self.initializeUI()
        self.connectSignals()

    def initializeUI(self):
        self.mainGroup.setHidden(True)
        self.mainGroup.setTitle("Node:")

    def connectSignals(self):
        pass

    def buildLayout(self):
        """
        Build the layout dynamically
        """
        #self.clearLayout(self.mainGroupLayout)
        for grp_name in self.parser._data.keys():
            group = QtGui.QGroupBox(self.mainGroup)
            group.setTitle('%s:' % grp_name.title())
            group.setFlat(True)
            group.setObjectName("%s_group" % grp_name)
            grpLayout = QtGui.QFormLayout(group)
            grpLayout.setObjectName("%s_group_layout" % grp_name)
            
            attrs = self.parser._data.get(grp_name)
            row = 0
            for attr_name, attr_attrs in attrs.iteritems():           
                private = attr_attrs.pop('private', False)
                if not private or self._show_private:
                    attr_label = QtGui.QLabel('%s: ' % attr_name, parent=group)
                    attr_type = attr_attrs.pop('type')
                    default_value = attr_attrs.pop('default_value', None)
                    
                    editor = map_widget(attr_type, parent=group, name=attr_name)
                    if editor:
                        editor.setNodes(self.nodes)
                        grpLayout.setWidget(row, QtGui.QFormLayout.LabelRole, attr_label)
                        grpLayout.setWidget(row, QtGui.QFormLayout.FieldRole, editor)
                        row += 1     
            
            self.mainGroupLayout.addWidget(group)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.mainGroupLayout.addItem(spacerItem)
        self.mainLayout.addWidget(self.mainGroup)
        self.mainGroup.setHidden(False)

    @property
    def nodes(self):
        return self._nodes

    @property
    def parser(self):
        return self._parser
    
    def setNodes(self, dagnodes):
        """
        Add nodes to the current editor.
        """
        metadata=[]
        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)
                if d._metadata not in metadata:
                    metadata.append(d._metadata)
        
        if not metadata:
            return

        if len(metadata) != 1:
            return

        # build the UI
        self.clearLayout(self.mainGroupLayout)
        self.parser.read(metadata[0])
        self.buildLayout()
        self.mainGroup.setTitle("%s:" % self._nodes[0].name)

    def clearLayout(self, layout):
        """
        Clear the current grid
        """
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                #widget.setParent(None)
                widget.deleteLater()

# -sub widgets ---

class QFloat2Editor(QtGui.QWidget):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal()

    def __init__(self, parent=None, **kwargs):
        super(QFloat2Editor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(3, 3, 3, 3)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QFloatLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QFloatLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.get_value(), self.val2_edit.get_value())

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = (0,0)
        if node_values:
            if len(node_values) == 1:
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

                self.val1_edit.editingFinished.connect(self.updateNodeAction)
                self.val2_edit.editingFinished.connect(self.updateNodeAction)

    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                print 'updating node: "%s.%s" : %s ' % (node.name, self._attribute, str(self.value))
                setattr(node, self._attribute, self.value)


class QFloat3Editor(QtGui.QWidget):

    attr_type       = 'float'
    valueChanged    = QtCore.Signal()

    def __init__(self, parent=None, **kwargs):
        super(QFloat3Editor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(3, 3, 3, 3)
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

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.get_value(), self.val2_edit.get_value(), self.val3_edit.get_value())

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = (0,0)
        if node_values:
            if len(node_values) == 1:
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

                self.val1_edit.editingFinished.connect(self.updateNodeAction)
                self.val2_edit.editingFinished.connect(self.updateNodeAction)
                self.val3_edit.editingFinished.connect(self.updateNodeAction)

    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, self.value)


class QInt2Editor(QtGui.QWidget):

    attr_type       = 'int'
    valueChanged    = QtCore.Signal()

    def __init__(self, parent=None, **kwargs):
        super(QInt2Editor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(3, 3, 3, 3)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QIntLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QIntLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.get_value(), self.val2_edit.get_value())

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = (0,0)
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]

                # set the editor value
                self.val1_edit.blockSignals(True)
                self.val2_edit.blockSignals(True)

                # set the current node values.
                self.val1_edit.setText(str(editor_value[0]))
                self.val2_edit.setText(str(editor_value[1]))

                self.val1_edit.blockSignals(False)
                self.val2_edit.blockSignals(False)

                self.val1_edit.editingFinished.connect(self.updateNodeAction)
                self.val2_edit.editingFinished.connect(self.updateNodeAction)

    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                print 'updating node: "%s.%s" : %s ' % (node.name, self._attribute, str(self.value))
                setattr(node, self._attribute, self.value)


class QInt3Editor(QtGui.QWidget):

    attr_type       = 'in'
    valueChanged    = QtCore.Signal()

    def __init__(self, parent=None, **kwargs):
        super(QInt3Editor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(3)
        self.mainLayout.setContentsMargins(3, 3, 3, 3)
        self.mainLayout.setObjectName("mainLayout")

        # value 1 editor
        self.val1_edit = QIntLineEdit(self)
        self.val1_edit.setObjectName("val1_edit")        
        self.mainLayout.addWidget(self.val1_edit)

        # value 2 editor
        self.val2_edit = QIntLineEdit(self)
        self.val2_edit.setObjectName("val2_edit")
        self.mainLayout.addWidget(self.val2_edit)

        # value 3 editor
        self.val3_edit = QIntLineEdit(self)
        self.val3_edit.setObjectName("val3_edit")
        self.mainLayout.addWidget(self.val3_edit)

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return (self.val1_edit.get_value(), self.val2_edit.get_value(), self.val3_edit.get_value())

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = (0,0)
        if node_values:
            if len(node_values) == 1:
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

                self.val1_edit.editingFinished.connect(self.updateNodeAction)
                self.val2_edit.editingFinished.connect(self.updateNodeAction)
                self.val3_edit.editingFinished.connect(self.updateNodeAction)

    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, self.value)


class QBoolEditor(QtGui.QCheckBox):
    attr_type       = 'bool'
    valueChanged    = QtCore.Signal()
    def __init__(self, parent=None, **kwargs):
        super(QBoolEditor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')
        self.toggled.connect(self.updateNodeAction)

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return self.isChecked()

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = False
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]

                # set the editor value
                self.blockSignals(True)
                self.setChecked(editor_value)
                self.blockSignals(False)

    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, self.isChecked())



class StringEditor(QtGui.QLineEdit):
    attr_type       = 'str'
    valueChanged    = QtCore.Signal()
    def __init__(self, parent=None, **kwargs):
        super(StringEditor, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def value(self):
        """
        Get the current editor value.
        """
        return str(self.text())

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = ""
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]
                # set the editor value
                self.blockSignals(True)
                self.setText(editor_value)
                self.blockSignals(False)

                self.editingFinished.connect(self.updateNodeAction)
                self.returnPressed.connect(self.updateNodeAction)
                
    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, str(self.text()))


class QFloatLineEdit(QtGui.QLineEdit):
    attr_type       = 'float'
    valueChanged    = QtCore.Signal()
    def __init__(self, parent=None, **kwargs):
        super(QFloatLineEdit, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.returnPressed.connect(self.update)
        self.editingFinished.connect(self.update)

    def get_value(self):
        return float(self.text())

    def setText(self, text):
        super(QFloatLineEdit, self).setText('%.2f' % float(text))

    def update(self):
        if self.text():
            self.setText(self.text())
        self.updateNodeAction()
        super(QFloatLineEdit, self).update()

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = 0
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]

                # set the editor value
                self.blockSignals(True)
                self.setText(editor_value)
                self.blockSignals(False)


    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, self.get_value())



class QIntLineEdit(QtGui.QLineEdit):
    attr_type       = 'int'
    valueChanged    = QtCore.Signal()
    def __init__(self, parent=None, **kwargs):
        super(QIntLineEdit, self).__init__(parent)

        self._nodes     = []
        self._attribute = kwargs.get('name', 'array')

        self.returnPressed.connect(self.update)
        self.editingFinished.connect(self.update)

    def get_value(self):
        if self.text():
            return int(self.text())
        return 0

    def setText(self, text):
        if text:
            super(QIntLineEdit, self).setText('%d' % int(text))

    def update(self):
        if self.text():
            self.setText(self.text())
        self.updateNodeAction()
        super(QIntLineEdit, self).update()

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = 0
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]

                # set the editor value
                self.blockSignals(True)
                self.setText(editor_value)
                self.blockSignals(False)


    def updateNodeAction(self):
        """
        Update the current nodes with the revised value.
        """
        for node in self._nodes:
            if hasattr(node, self._attribute):
                setattr(node, self._attribute, self.get_value())



class ColorPicker(QtGui.QWidget):
    """ 
    Color picker widget, expects an RGB value as an argument.
    """
    valueChanged    = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None, **kwargs):
        super(ColorPicker, self).__init__(parent)

        self._nodes         = []
        self._attribute     = kwargs.get('name', 'color')

        self.normalized     = kwargs.get('norm', True)
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
        self.valueChanged.connect(self.updateNodeColor)

    def setNodes(self, dagnodes, name=None):
        """
        Set the widgets nodes values.
        """
        if name is not None:
            if name!=self._attribute:
                self._attribute = name

        nodesChanged = False
        for d in dagnodes:
            if d not in self._nodes:
                nodesChanged = True
                self._nodes.append(d)

        # set the nodes
        node_values = []
        if nodesChanged:
            for n in self._nodes:
                if hasattr(n, self.attribute):
                    nval = getattr(n, self.attribute)
                    if nval not in node_values:
                        node_values.append(nval)

        editor_value = [0, 0, 0]
        if node_values:
            if len(node_values) == 1:
                editor_value = node_values[0]

                # set the editor value
                self.colorSwatch.setColor(editor_value)

    def updateNodeColor(self, color):
        """
        Update the node color value.
        """
        rgb = (color.red(), color.green(), color.blue())
        for node in self._nodes:
            print 'node: ', node.name, color
            node.color = rgb

    @property
    def attribute(self):
        return self._attribute
    
    @property
    def nodes(self):
        return self._nodes
    
    def getValue(self):
        """
        Returns the current color's RGB values.

        returns:
            (list) - rgb color values.
        """
        return self.colorSwatch.color

    def setAttr(self, val):
        # 32 is the first user data role
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr

    def _update(self):
        self.colorSwatch._update()

    def sliderChangedAction(self):
        """ set the value """
        sval = float(self.slider.value())

        # normalize the slider value
        n = float(((sval - float(self.min)) / (float(self.max) - float(self.min))))

        red = float(self.color[0])
        green = float(self.color[1])
        blue = float(self.color[2])
        rgb = (red*n, green*n, blue*n)
        #rgb = expandNormRGB(red*n, green*n, blue*n)
        new_color = QtGui.QColor(*rgb)
        self.colorSwatch.qcolor = new_color
        self.colorSwatch._update()

    def sliderReleasedAction(self):
        """
        Update the items' color when the slider handle is released.
        """
        color = self.colorSwatch.color
        self.valueChanged.emit(self.colorSwatch.qcolor)
        self.colorSwatch._update()

    def colorPickedAction(self):
        """ 
        Action to call the color picker.
        """
        dialog=QtGui.QColorDialog(self.colorSwatch.qcolor, self)
        if dialog.exec_():
            self.colorSwatch.setPalette(QtGui.QPalette(dialog.currentColor()))
            self.colorSwatch.qcolor=dialog.currentColor()

            ncolor=expandNormRGB((self.colorSwatch.qcolor.red(), self.colorSwatch.qcolor.green(), self.colorSwatch.qcolor.blue()))
            self.valueChanged.emit(self.colorSwatch.qcolor)
            self.colorSwatch._update()

    def setMin(self, val):
        self.min = val
        self.slider.setMinimum(val)

    def setMax(self, val):
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


class ColorSwatch(QtGui.QToolButton):

    itemClicked = QtCore.Signal(bool)

    def __init__(self, parent=None, **kwargs):
        super(ColorSwatch, self).__init__(parent)

        self.normalized     = kwargs.get('norm', True)
        self.color          = kwargs.get('color', [1.0, 1.0, 1.0])
        self.qcolor         = QtGui.QColor()
        self.setColor(self.color)
        #self.setStyleSheet("font-size:40px;background-color:#%s;border: 0px solid #333333" % self.qcolor.name())

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
        self.setStyleSheet("QToolButton{background-color: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 rgb(%d, %d, %d), stop:1 rgb(%d, %d, %d))};" % (self.color[0]*.45, self.color[1]*.45, self.color[2]*.45, self.color[0], self.color[1], self.color[2]))

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


WIDGET_MAPPER = dict(
    float   = QFloatLineEdit,
    float2  = QFloat2Editor,
    float3  = QFloat3Editor,
    bool    = QBoolEditor,
    str     = StringEditor,
    int     = QIntLineEdit,
    int2    = QInt2Editor,
    int3    = QInt3Editor,
    int8    = QIntLineEdit,
    color   = ColorPicker,
    short2  = QFloat2Editor,
    )



def map_widget(typ, parent, name):
    typ=typ.replace(" ", "")
    if typ in WIDGET_MAPPER:
        cls = WIDGET_MAPPER.get(typ)
        return cls(parent, name=name)
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
