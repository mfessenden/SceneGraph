#!/usr/bin/env python
from PySide import QtCore, QtGui
from SceneGraph import core
from SceneGraph import util


class GraphAttributes(QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        verticalLayout = QtGui.QVBoxLayout(self)
        self.setLayout(verticalLayout)

        self.groupBox = QtGui.QGroupBox(self)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.desc_label = QtGui.QLabel(self.groupBox)
        self.desc_label.setObjectName("desc_label")
        self.gridLayout.addWidget(self.desc_label, 0, 0, 1, 2)
        
        self.atttr_name_label = QtGui.QLabel(self.groupBox)
        self.atttr_name_label.setObjectName("atttr_name_label")
        self.gridLayout.addWidget(self.atttr_name_label, 1, 0, 1, 1)
        self.attr_name_edit = QtGui.QLineEdit(self.groupBox)
        self.attr_name_edit.setObjectName("attr_name_edit")
        self.gridLayout.addWidget(self.attr_name_edit, 1, 1, 1, 1)
        
        self.atttr_value_label = QtGui.QLabel(self.groupBox)
        self.atttr_value_label.setObjectName("atttr_value_label")
        self.gridLayout.addWidget(self.atttr_value_label, 2, 0, 1, 1)
        self.attr_value_edit = QtGui.QLineEdit(self.groupBox)
        self.attr_value_edit.setObjectName("attr_value_edit")
        self.gridLayout.addWidget(self.attr_value_edit, 2, 1, 1, 1)

        self.type_label = QtGui.QLabel(self.groupBox)
        self.type_label.setObjectName("type_label")
        self.gridLayout.addWidget(self.type_label, 3, 1, 1, 1)

        self.type_menu = QtGui.QComboBox(self.groupBox)
        self.type_menu.setObjectName("type_menu")
        self.gridLayout.addWidget(self.type_menu, 3, 1, 1, 1)

        self.dagnodes_rb = QtGui.QRadioButton(self.groupBox)
        self.dagnodes_rb.setObjectName("dagnodes_rb")
        self.gridLayout.addWidget(self.dagnodes_rb, 4, 1, 1, 1)
        verticalLayout.addWidget(self.groupBox)
        
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        verticalLayout.addWidget(self.buttonBox)

        self.initializeUI()

        # signals
        self.buttonBox.accepted.connect(self.acceptedAction)
        self.buttonBox.rejected.connect(self.rejectedAction)

    def initializeUI(self):
        self.groupBox.setTitle("Update Attributes")
        self.desc_label.setText("Pass attributes directly into the graph.")
        self.type_label.setText("Type:")
        self.atttr_name_label.setText("Attribute:")
        self.atttr_value_label.setText("Value:")
        self.dagnodes_rb.setText("dag nodes")

    def sizeHint(self):
        return QtCore.QSize(294, 212)

    def acceptedAction(self):
        attr_name = self.attr_name_edit.text()
        attr_val = self.attr_value_edit.text()

        if not attr_name or not attr_val:
            return

        value_type = util.attr_type(attr_val)
        attr_val = util.auto_convert(attr_val)

        self.parent().handler.scene.updateNodes(**{attr_name:attr_val})
        self.close()

    def rejectedAction(self):
        self.close()
