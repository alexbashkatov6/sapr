from PyQt5.QtWidgets import QDialog, QFrame, QGroupBox, QStyleOptionGroupBox, QCheckBox, QRadioButton, QVBoxLayout
from PyQt5.QtCore import pyqtSignal


class ProjectPropertiesDialog(QDialog):
    checkbox_auto_add_interface_object = pyqtSignal(bool)
    radio_signal_interface_type = pyqtSignal(str)
    radio_point_interface_type = pyqtSignal(str)
    radio_derail_interface_type = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Project properties")
        self.setMinimumWidth(300)
        self.setMinimumHeight(200)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.auto_add_checkbox = QCheckBox("Auto add interface objects")
        self.auto_add_checkbox.clicked.connect(self.checkbox_auto_add_interface_object)
        main_layout.addWidget(self.auto_add_checkbox)

        gb_signal = QGroupBox("Signal options", self)
        gb_signal.setGeometry(10, 10, 290, 190)
        main_layout.addWidget(gb_signal)

        gb_point = QGroupBox("Point options", self)
        gb_point.setGeometry(10, 10, 290, 190)
        main_layout.addWidget(gb_point)

        gb_derail = QGroupBox("Derail options", self)
        gb_derail.setGeometry(10, 10, 290, 190)
        main_layout.addWidget(gb_derail)

        main_layout.addStretch(1)

        gb_signal_itype = QGroupBox("Default IO type", self)
        gb_signal_itype.setGeometry(20, 20, 270, 50)
        self.signal_radio_ci = QRadioButton("&Ci")
        self.signal_radio_ri = QRadioButton("&Ri")
        self.signal_radio_ci.clicked.connect(self.clicked_signal_ci_radio)
        self.signal_radio_ri.clicked.connect(self.clicked_signal_ri_radio)

        vbox_signal_itype = QVBoxLayout()
        vbox_signal_itype.addWidget(self.signal_radio_ci)
        vbox_signal_itype.addWidget(self.signal_radio_ri)
        gb_signal_itype.setLayout(vbox_signal_itype)

        vbox_signal_options = QVBoxLayout()
        vbox_signal_options.addWidget(gb_signal_itype)
        vbox_signal_options.addStretch(1)
        gb_signal.setLayout(vbox_signal_options)

        gb_point_itype = QGroupBox("Default IO type", self)
        gb_point_itype.setGeometry(20, 20, 270, 50)
        self.point_radio_ci = QRadioButton("&Ci")
        self.point_radio_ri = QRadioButton("&Ri")
        self.point_radio_ci.clicked.connect(self.clicked_point_ci_radio)
        self.point_radio_ri.clicked.connect(self.clicked_point_ri_radio)

        vbox_point_itype = QVBoxLayout()
        vbox_point_itype.addWidget(self.point_radio_ci)
        vbox_point_itype.addWidget(self.point_radio_ri)
        gb_point_itype.setLayout(vbox_point_itype)

        vbox_point_options = QVBoxLayout()
        vbox_point_options.addWidget(gb_point_itype)
        vbox_point_options.addStretch(1)
        gb_point.setLayout(vbox_point_options)

        gb_derail_itype = QGroupBox("Default IO type", self)
        gb_derail_itype.setGeometry(20, 20, 270, 50)
        self.derail_radio_ci = QRadioButton("&Ci")
        self.derail_radio_ri = QRadioButton("&Ri")
        self.derail_radio_ci.clicked.connect(self.clicked_derail_ci_radio)
        self.derail_radio_ri.clicked.connect(self.clicked_derail_ri_radio)

        vbox_derail_itype = QVBoxLayout()
        vbox_derail_itype.addWidget(self.derail_radio_ci)
        vbox_derail_itype.addWidget(self.derail_radio_ri)
        gb_derail_itype.setLayout(vbox_derail_itype)

        vbox_derail_options = QVBoxLayout()
        vbox_derail_options.addWidget(gb_derail_itype)
        vbox_derail_options.addStretch(1)
        gb_derail.setLayout(vbox_derail_options)

    def init_buttons_state(self):
        self.auto_add_checkbox.setChecked(True)
        self.auto_add_checkbox.clicked.emit(True)

        self.signal_radio_ci.setChecked(True)
        self.signal_radio_ci.clicked.emit(True)

        self.point_radio_ci.setChecked(True)
        self.point_radio_ci.clicked.emit(True)

        self.derail_radio_ci.setChecked(True)
        self.derail_radio_ci.clicked.emit(True)

    def clicked_signal_ci_radio(self, cl: bool):
        if cl:
            self.radio_signal_interface_type.emit("Ci")

    def clicked_signal_ri_radio(self, cl: bool):
        if cl:
            self.radio_signal_interface_type.emit("Ri")

    def clicked_point_ci_radio(self, cl: bool):
        if cl:
            self.radio_point_interface_type.emit("Ci")

    def clicked_point_ri_radio(self, cl: bool):
        if cl:
            self.radio_point_interface_type.emit("Ri")

    def clicked_derail_ci_radio(self, cl: bool):
        if cl:
            self.radio_derail_interface_type.emit("Ci")

    def clicked_derail_ri_radio(self, cl: bool):
        if cl:
            self.radio_derail_interface_type.emit("Ri")