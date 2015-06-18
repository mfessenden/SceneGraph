#!/usr/bin/env xpython
from PySide import QtGui, QtCore
from functools import partial
import re
import numpy



class AttributeEditor(QtGui.QWidget):

    def __init__(self, parent=None, **kwargs):
        QtGui.QWidget.__init__(self, parent)
        
        self._gui           = kwargs.get('gui', None)
        self.manager        = kwargs.get('manager')
        self._current_node  = None    # the currently selected node

        self.gridLayout     = QtGui.QGridLayout(self)
        self.gridLayout.setContentsMargins(9, 2, 9, 9)
        self.setObjectName('AttributeEditor')

    def initializeMenubar(self):
        """
        Initialize the widget's menubar.
        """
        # menubar
        self.menubar = QtGui.QMenuBar(self)
        self.menubar.setProperty('class', 'AttributeMenu')
        attrMenu = self.menubar.addMenu('Attributes')

        # actions
        addAttrAction = QtGui.QAction('Add attributes...', self)        
        attrMenu.addAction(addAttrAction)

        # actions
        deleteAttrAction = QtGui.QAction('Delete attributes...', self)        
        attrMenu.addAction(deleteAttrAction)

    def setNode(self, node_item, force=False):
        """
        Set the currently focused node.
        """
        if node_item:
            if node_item != self._current_node:
                # removed for testing
                #node_item.nodeChanged.connect(partial(self.setNode, node_item))
                self._current_node = node_item
                
                # clear the layout
                self._clearGrid()                  
                self.__current_row = 0
               
                for attr, val in node_item.getNodeAttributes().iteritems():
                    editable = True
                    if attr in node_item.PRIVATE:
                        editable = False

                    # create an attribute label
                    attr_label = QtGui.QLabel(self)
                    attr_label.setObjectName('%s_label' % attr)
                    self.gridLayout.addWidget(attr_label, self.__current_row, 0, 1, 1)

                    # create an attribute editor
                    if attr != 'color':
                        val_edit = QtGui.QLineEdit(self)
                        val_edit.setText(str(val))
                        val_edit.editingFinished.connect(partial(self.updateNodeAttribute, val_edit, attr))

                    else:
                        val_edit = ColorPicker(self, color=node_item.color, norm=False)
                        val_edit.colorChanged.connect(self.updateNodeColor)

                    val_edit.setObjectName('%s_edit' % attr)
                    self.gridLayout.addWidget(val_edit, self.__current_row, 1, 1, 1)
                    
                    attr_label.setText('%s: ' % attr)
                    attr_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
                    
                    val_edit.setEnabled(editable)

                    if not force:
                        attr_label.setHidden(not editable)
                        val_edit.setHidden(not editable)

                    self.__current_row+=1                    
                    
                spacerItem = QtGui.QSpacerItem(20, 178, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
                self.gridLayout.addItem(spacerItem, self.__current_row, 1, 1, 1)

            else:
                # update existing attribute editors
                for attr, val in node_item.getNodeAttributes().iteritems():
                    editor = self.findChild(QtGui.QLineEdit, '%s_edit' % attr)
                    if editor:
                        editor.blockSignals(True)
                        if attr not in ['color']:
                            editor.setText(str(val))
                        editor.blockSignals(False)
    
    def getColorEditor(self):
        """
        Return the current color editor widget.
        """
        return self.findChild(ColorPicker)

    def updateAttributes(self):
        """
        Dynamically add attributes from a node
        """
        self.deleteGridWidget(self.__current_row, 1)

    def nodeUpdateAction(self):
        """
        Update the current node
        """
        new_name = str(self.nameEdit.text())
        if self._current_node:
            node = self.manager.renameNode(self._current_node.name, new_name)
            if node:
                self.setNode(node)
                node._widget.update()
    
    def updateNodeAttribute(self, lineEdit, attribute):
        """
        Update the node from an attribute
        """
        new_value = str(lineEdit.text())
        try:
            new_value = eval(new_value)
        except:
            pass
        self._current_node.addNodeAttributes(**{attribute:new_value})
        self.setNode(self._current_node)
    
    def updateNodeColor(self, color):
        """
        Update the node olor value.
        """
        rgb = (color.red(), color.green(), color.blue())
        self._current_node.color = rgb

    def nodeUpdatedFilter(self):
        """
        Runs when the task description (token) is updated
        """
        cur_val = re.sub('^_', '', str(self.nameEdit.text()).replace(' ', '_'))
        cur_val = re.sub('__', '_', cur_val)
        self.nameEdit.setText(cur_val)

    def nodeFinalizedFilter(self):
        """
        Runs when the task description (token) editing is finished
        """
        cur_val = str(self.nameEdit.text())
        cur_val = re.sub('^_', '', cur_val)
        cur_val = re.sub('_$', '', cur_val)        
        self.nameEdit.setText(cur_val)
        self.nodeUpdateAction()

    def _clearGrid(self):
        """
        Clear the current grid
        """
        if self.gridLayout:
            for r in range(self.gridLayout.rowCount()):
                self.deleteGridWidget(r, 0)
                self.deleteGridWidget(r, 1)

    def deleteGridWidget(self, row, column):
        """
        Remove a widget
        """
        item = self.gridLayout.itemAtPosition(row, column)
        if item is not None:
            widget = item.widget()
            if widget is not None:
                self.gridLayout.removeWidget(widget)
                widget.deleteLater()


class ColorPicker(QtGui.QWidget):

    """ color picker widget, expects an RGB value as am argument """
    colorChanged    = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None, **kwargs):
        super(ColorPicker, self).__init__(parent)

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

    def getValue(self):
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
        import colorsys
        slider_value = self.slider.value()
        hsv=self.colorSwatch.qcolor.getHsvF()
        #self.colorSwatch.qcolor.setHsv(hsv[0], hsv[1], new_hsv[2], 255)
        #self.colorSwatch._update()
        new_rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], (hsv[2]*(self.mult*slider_value)))
        #print new_rgb
        self.colorSwatch.setColor(new_rgb)

    def colorPickedAction(self):
        """ action to call the color picker """
        dialog=QtGui.QColorDialog(self.colorSwatch.qcolor, self)
        if dialog.exec_():
            self.colorSwatch.setPalette(QtGui.QPalette(dialog.currentColor()))
            self.colorSwatch.qcolor=dialog.currentColor()

            ncolor=expandNormRGB((self.colorSwatch.qcolor.red(), self.colorSwatch.qcolor.green(), self.colorSwatch.qcolor.blue()))
            self.colorChanged.emit(self.colorSwatch.qcolor)
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
        #self.colorHSV       = None
        self.qcolor         = QtGui.QColor()
        self.setColor(self.color)
        #self.setStyleSheet("font-size:40px;background-color:#%s;border: 0px solid #333333" % self.qcolor.name())

    def setColor(self, val):
        """ set an RGB color value """
        rgbf = False
        if type(val[0]) is float:
            self.qcolor.setRgbF(*val)
            rgbf = True
            self.setToolTip("%.2f, %.2f, %.2f" % (val[0], val[1], val[2])) 
        else:
            self.qcolor.setRgb(*val)
            self.setToolTip("%d, %d, %d" % (val[0], val[1], val[2]))  
        self._update()
        return self.color

    def getColor(self):
        return self.color

    def _update(self):
        """ update the button color """
        self.color = self.qcolor.getRgb()[0:3]
        self.setStyleSheet("QToolButton{background-color: rgb(%d, %d, %d)}" % (self.color[0], self.color[1], self.color[2]))        

    def _getHsvF(self):
        return self.qcolor.getHsvF()

    def _setHsvF(self, color):
        """ takes a tuple of HSV (normalized)"""
        self.qcolor.setHsvF(color[0], color[1], color[2], 255)
        #self._update()

    def _getHsv(self):
        return self.qcolor.getHsv()

    def _setHsv(self, color):
        """ takes a tuple of HSV (normalized)"""
        self.qcolor.setHsv(color[0], color[1], color[2], 255)
        #self._update()

    def getRGB(self, norm=True):
        """ returns rgb tuple """
        if not norm:
            return (self.qcolor.toRgb().red(), self.qcolor.toRgb().green(), self.qcolor.toRgb().blue())
        else:
            return (self.qcolor.toRgb().redF(), self.qcolor.toRgb().greenF(), self.qcolor.toRgb().blueF())

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


class FloatSlider(QtGui.QWidget):
    def __init__(self, parent=None, **kwargs):
        super(FloatSlider, self).__init__(parent)

        self.min          = kwargs.get('min', 0)
        self.max          = kwargs.get('max', 99)
        self.current_val  = kwargs.get('value', 0.0)
        self.attr         = None
        self.attrtype     = kwargs.get('attrtype', 'float')

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(1)
        self.mainLayout.setMargin(1)
        self.lineEdit = LineEdit(self, attrtype=self.attrtype)
        self.lineEdit.setMaximumSize(QtCore.QSize(85, 16777215))
        self.mainLayout.addWidget(self.lineEdit)
        self.slider = QtGui.QSlider(self)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.mainLayout.addWidget(self.slider)

        self.lineEdit.editingFinished.connect(self.lineChanged)
        self.lineEdit.focusChanged.connect(self.lineFocusChanged)
        self.slider.valueChanged.connect(self.sliderChangedAction)

        # initial setup
        self._setLine(self.current_val)
        self.setMin(self.min)
        self.setMax(self.max)

    def getValue(self):
        return float(self.lineEdit.getValue())

    def setAttr(self, val):
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr

    def _setLine(self, val):
        """ convert a value and set it to the lineEdit """
        floatval = None
        try:
            if self.attrtype == 'float':
                floatval = str(float(val))

            elif self.attrtype == 'int':
                floatval = str(int(val))
        except:
            pass
        if floatval:
            self.lineEdit.blockSignals(True)
            self.lineEdit.setText(floatval)
            self.lineEdit.blockSignals(False)

    def lineFocusChanged(self):
        self.lineChanged()

    def lineChanged(self):
        """ set the value """
        slider_value = self.slider.value()
        self.slider.blockSignals(True)
        val = self.current_val
        try:
            if self.attrtype == 'float':
                val = float(val)

            elif self.attrtype == 'int':
                val = int(val)
        except:
            pass
        self.slider.setValue(val)
        self._setLine(val)
        self.slider.blockSignals(False)

    def sliderChangedAction(self):
        """ set the value """
        slider_value = self.slider.value()
        self.lineEdit.blockSignals(True)
        self._setLine(slider_value)
        self.lineEdit.blockSignals(False)
        self.current_val = slider_value

    def setMin(self, val):
        self.min = val
        self.slider.setMinimum(val)

    def setMax(self, val):
        self.max = val
        self.slider.setMaximum(val)

    def sizeHint(self):
        return QtCore.QSize(350, 27)


class IntSlider(FloatSlider):
    def __init__(self, parent=None, attrtype='int', **kwargs):
        super(IntSlider, self).__init__(parent)

    def getValue(self):
        return int(self.lineEdit.getValue())


class LineEdit(QtGui.QLineEdit):

    focusChanged = QtCore.Signal(bool)

    def __init__(self, parent=None, **kwargs):
        super(LineEdit, self).__init__(parent)

        self.attrtype = kwargs.get('attrtype', 'string')
        self.attr = None

    def getValue(self):
        if self.attrtype == 'string':
            return str(self.text())
        if self.attrtype == 'float':
            return float(self.text())
        if self.attrtype == 'int':
            return int(self.text())

    @QtCore.Slot()
    def focusOutEvent(self, event):
        self.focusChanged.emit(True)
        super(LineEdit, self).focusOutEvent( QtGui.QFocusEvent(QtCore.QEvent.FocusOut))

    def focusInEvent(self, event):
        super(LineEdit, self).focusInEvent( QtGui.QFocusEvent(QtCore.QEvent.FocusIn))

    def setAttr(self, val):
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr


class MiniBrowserEdit(QtGui.QWidget):
    def __init__(self, parent=None, **kwargs):
        super(MiniBrowserEdit, self).__init__(parent)

        self.show_button   = kwargs.get('show_button', False)
        self.attr          = None
        self.style         = kwargs.get('style', 'default')
        global iconpath

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(2)
        self.mainLayout.setMargin(2)
        self.mainLayout.setContentsMargins(8, 2, 2, 2)

        self.lineEdit = LineEdit(self)
        self.mainLayout.addWidget(self.lineEdit)
        self.browseButton = QtGui.QToolButton(self)
        self.mainLayout.addWidget(self.browseButton)
        #self.browseButton.setText("...")
        icon_browse = QtGui.QIcon()
        icon_browse.addPixmap(QtGui.QPixmap(os.path.join(iconpath, self.style, 'folder_small_horiz_16px.png')), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.browseButton.setIcon(icon_browse)
        self.setButtonVisible(self.show_button)

        # set the completion model
        self.completer = QtGui.QCompleter(self)
        model = QtGui.QDirModel(self.completer)
        self.completer.setModel(model)
        self.lineEdit.setCompleter(self.completer)

    def getValue(self):
        return self.lineEdit.getValue()

    def setButtonVisible(self, val):
        self.browseButton.setHidden(val)

    def setAttr(self, val):
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr


class EnumValue(QtGui.QWidget):
    def __init__(self, parent=None, **kwargs):
        super(EnumValue, self).__init__(parent)
        self._type='enum'
        self._value=None
        self._values=[]

        self.horizontalLayout = QtGui.QHBoxLayout(self)
        self.enumValue = QtGui.QComboBox(self)
        self.horizontalLayout.addWidget(self.enumValue)
        self.enumValue.currentIndexChanged.connect(self.getValue)

    def addValue(self, val):
        self.enumValue.blockSignals(True)
        if val not in self._values:
            self._values.append(val)
            self.enumValue.clear()
            self.enumValue.addItems(sorted(self._values))

        self.enumValue.blockSignals(False)

    def getValue(self):
        self._value=str(self.enumValue.currentText())
        return self._value

    def setAttr(self, data=None, role=32 ):
        # 32 is the first user data role
        if data:
            self.enumValue.setData(role, QtCore.QVariant(data))

    def getAttr(self, role=32):
        return str(self.enumValue.data(role).toString())


class ArrayValue(QtGui.QWidget):
    def __init__(self, parent=None, **kwargs):
        super(ArrayValue, self).__init__(parent)

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.arrayValue1 = QtGui.QLineEdit(self)
        self.mainLayout.addWidget(self.arrayValue1)
        self.arrayValue2 = QtGui.QLineEdit(self)
        self.mainLayout.addWidget(self.arrayValue2)
        self.arrayValue3 = QtGui.QLineEdit(self)
        self.mainLayout.addWidget(self.arrayValue3)

    def setValue(self, val):
        self.arrayValue1.setText()

    def round(val, dp=3):
        flstr='%.'+str(dp)+'f'
        return flstr % val

    def setAttr(self, data=None, role=32 ):
        # 32 is the first user data role
        if data:
            self.setData(role, QtCore.QVariant(data))

    def getAttr(self, role=32):
        return str(self.data(role).toString())


class BoolValue(QtGui.QWidget):
    def __init__(self, parent=None, **kwargs):
        super(BoolValue, self).__init__(parent)

        self.label  = kwargs.get('label', 'checkbox')
        self.attr   = None

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.mainLayout.setSpacing(2)
        self.mainLayout.setMargin(2)
        self.boolValue = QtGui.QCheckBox(self)
        self.mainLayout.addWidget(self.boolValue)
        self.setText(self.label)

    def setText(self, val):
        self.boolValue.setText(val)

    def setValue(self, val):
        self.boolValue.setChecked(val)

    def getValue(self):
        return bool(self.boolValue.isChecked())

    def setAttr(self, val):
        # 32 is the first user data role
        self.attr = val
        return self.attr

    def getAttr(self):
        return self.attr


class StringValue(QtGui.QWidget):
    def __init__(self, parent=None, typ='string', **kwargs):
        super(StringValue, self).__init__(parent)

        self._type=typ
        self._value=None
        self._pad=3

        self.mainLayout = QtGui.QHBoxLayout(self)
        self.valueLine = QtGui.QLineEdit(self)
        self.mainLayout.addWidget(self.valueLine)

    def setValue(self, val):
        self._value=val
        if type(val) is float:
            val=self.round(val, self.pad)
        self.valueLine.setText(str(val))

    def getValue(self):
        if self._type=='string':
            return str( self.valueLine.text() )
        elif self._type=='int':
            return int( self.valueLine.text() )
        elif self._type=='int':
            return int( self.valueLine.text() )

    @property
    def pad(self):
        return self._pad

    @pad.setter
    def pad(self, val):
        self._pad=val
        self.setValue(self._value)
        return self._pad

    def round(self, val, dp=3):
        flstr='%.'+str(dp)+'f'
        return flstr % val

    def setAttr(self, data=None, role=32 ):
        # 32 is the first user data role
        if data:
            self.setData(role, QtCore.QVariant(data))

    def getAttr(self, role=32):
        return str(self.data(role).toString())


class FloatValue(StringValue):
    def __init__(self, parent=None, typ='float', **kwargs):
        super(FloatValue, self).__init__(parent)


class IntValue(StringValue):
    def __init__(self, parent=None, typ='int', **kwargs):
        super(IntValue, self).__init__(parent)