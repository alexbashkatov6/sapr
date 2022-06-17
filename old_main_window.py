from collections import OrderedDict
from functools import partial
from typing import Union, Any
import os

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QToolBar, QTreeView, QVBoxLayout, QHBoxLayout, QLabel, \
    QLineEdit, QWidget, QScrollArea, QComboBox, QCompleter, QMenu, QPushButton, QSizePolicy, QAbstractScrollArea, \
    QDialog, QFrame, QGroupBox, QStyleOptionGroupBox, QCheckBox, QRadioButton
from PyQt5.QtGui import QWindow
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QModelIndex
from PyQt5.Qt import QStandardItemModel, QStandardItem, QMouseEvent, QContextMenuEvent

from project_properties_dialog import ProjectPropertiesDialog
from config import MAIN_CLASSES_TREE, SPACED_STARTS, SINGLE_ATTRIBUTE_KEY

CONFIG_FILE_JSON_NAMES = ["Border", "Equipment", "IObjectsCodeGenerator", "IObjectsEncodingPoint",
                          "IObjectsPoint", "IObjectsRelay", "IObjectsSignal", "IObjectsTrack",
                          "Operator", "RailWarningArea", "Telesignalization",
                          "TObjectsPoint", "TObjectsSignal", "TObjectsTrack"]

CONFIG_FILE_XML_NAMES = ["TrainRoute", "ShuntingRoute", "PpoSystemEnv"]


def camelcase_to_downcase(s: str, skip_first_underscore: bool = True):
    result_str_symbols = []
    for i, symbol in enumerate(s):
        if symbol.isupper():
            if (not skip_first_underscore) or i != 0:
                result_str_symbols.append("_")
            result_str_symbols.append(symbol.lower())
        else:
            result_str_symbols.append(symbol)
    return "".join(result_str_symbols)


class MainWindow(QMainWindow):
    tpl_opened = pyqtSignal(str)
    obj_id_opened = pyqtSignal(str)
    template_directory_selected = pyqtSignal(str)
    config_directory_selected = pyqtSignal(str)
    generate_file = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setGeometry(1000, 50, 800, 900)
        # self.setFixedSize(600, 300)
        self.setWindowTitle('Main window')

        # toolbars
        self.tree_toolbar = TreeToolBar()
        self.addToolBar(Qt.LeftToolBarArea, self.tree_toolbar)
        self.attribute_toolbar = AttributeToolBar()
        self.addToolBar(Qt.RightToolBarArea, self.attribute_toolbar)

        # menus
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction("&Open TPL").triggered.connect(self.open_tpl)
        file_menu.addAction("&Open Obj Id").triggered.connect(self.open_obj_id)
        file_menu.addAction("&Save Template").triggered.connect(self.save_template)
        file_menu.addAction("&Save config").triggered.connect(self.save_config)

        proj_prop_menu = menu_bar.addMenu('&Project')
        proj_prop_menu.addAction("&Properties").triggered.connect(self.open_prop_window)

        gen_menu = menu_bar.addMenu('&Generators')
        obj_types_menu = gen_menu.addMenu("Objects")
        for file_name in CONFIG_FILE_JSON_NAMES:
            obj_types_menu.addAction(file_name).triggered.connect(partial(self.gen_single_file, obj_group_name=file_name))
        gen_menu.addAction("&Generate all").triggered.connect(self.gen_all_files)

        # dialogs
        self.ppd = ProjectPropertiesDialog(self)

        self.show()

    def open_prop_window(self):
        self.ppd.show()

    def open_tpl(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', './input/', 'xml Files (*.xml)')
        if not file_name:
            return
        self.tpl_opened.emit(file_name)

    def open_obj_id(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', './input/', 'xml Files (*.xml)')
        if not file_name:
            return
        self.obj_id_opened.emit(file_name)

    def auto_open_tpl(self):
        file_name = os.path.join(os.getcwd(), "input", "TPL.xml")
        self.tpl_opened.emit(file_name)

    def save_template(self):
        dir_name = QFileDialog.getExistingDirectory(self, 'Save', './output/')
        if not dir_name:
            return
        self.template_directory_selected.emit(dir_name)

    def save_config(self):
        dir_name = QFileDialog.getExistingDirectory(self, 'Save', './output/')
        if not dir_name:
            return
        self.config_directory_selected.emit(dir_name)

    def gen_single_file(self, obj_group_name: str):
        self.generate_file.emit(obj_group_name)

    def gen_all_files(self):
        for file_name in CONFIG_FILE_JSON_NAMES:
            self.generate_file.emit(file_name)


class TreeToolBarWidget(QTreeView):
    send_add_new = pyqtSignal(str)
    send_rename = pyqtSignal(str, str)
    send_attrib_request = pyqtSignal(str)
    send_remove_request = pyqtSignal(str)
    send_change_class_request = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        # print("init")
        self.tree_model = QStandardItemModel()
        self.tree_model.itemChanged.connect(self.item_changed)
        self.root_node = self.tree_model.invisibleRootItem()
        self.setModel(self.tree_model)
        self.setHeaderHidden(True)
        self.class_names: set[str] = set()
        self.simple_shunting_names: set[str] = set()
        self.adj_point_shunting_names: set[str] = set()
        self.obj_names: set[str] = set()
        self.index_to_obj_name: dict[QModelIndex, str] = {}
        self.cls_name_to_index: dict[str, QModelIndex] = {}
        self.expanded_indexes: set[QModelIndex] = set()
        self.expanded.connect(self.add_expanded_index)
        self.collapsed.connect(self.remove_expanded_index)
        self.old_slider_position = 0
        self.old_slider_range = (0, 0)
        # self.verticalScrollBar().setTracking(False)
        self.class_items: dict[str, QStandardItem] = {}
        self.init_classes_tree()

    def add_expanded_index(self, idx: QModelIndex):
        self.expanded_indexes.add(idx)

    def remove_expanded_index(self, idx: QModelIndex):
        self.expanded_indexes.remove(idx)

    def init_classes_tree(self):
        self.root_node.removeRows(0, self.root_node.rowCount())
        self.root_node.emitDataChanged()
        for partition in MAIN_CLASSES_TREE:
            item_partition = QStandardItem(partition)
            item_partition.setEditable(False)
            item_partition.setSelectable(False)
            self.root_node.appendRow(QStandardItem(""))
            self.root_node.appendRow(item_partition)
            self.root_node.appendRow(QStandardItem(""))
            for class_group in MAIN_CLASSES_TREE[partition]:
                item_group = QStandardItem(class_group)
                item_group.setEditable(False)
                item_group.setSelectable(False)
                item_partition.appendRow(item_group)
                class_names_list = MAIN_CLASSES_TREE[partition][class_group]
                for cls_name in class_names_list:
                    item_class = QStandardItem(cls_name)
                    item_class.setEditable(False)
                    item_class.setSelectable(False)
                    item_group.appendRow(item_class)
                    self.class_items[item_class.text()] = item_class
                    self.cls_name_to_index[cls_name] = item_class.index()
        self.expandAll()
        for class_item in self.class_items.values():
            self.collapse(class_item.index())

    def from_dict(self, d: OrderedDict[str, list[str]]):
        self.obj_names.clear()
        self.simple_shunting_names.clear()
        self.adj_point_shunting_names.clear()
        for class_name in d:
            class_item = self.class_items[class_name]
            class_item.removeRows(0, class_item.rowCount())
            for obj_name in d[class_name]:
                if class_name == "PpoShuntingSignal":
                    self.simple_shunting_names.add(obj_name)
                if class_name == "PpoShuntingSignalWithTrackAnD":
                    self.adj_point_shunting_names.add(obj_name)
                self.obj_names.add(obj_name)
                item_obj = QStandardItem(obj_name)
                class_item.appendRow(item_obj)
                self.index_to_obj_name[item_obj.index()] = obj_name
        for idx in self.expanded_indexes:
            self.expand(idx)

    def old_from_dict(self, d: OrderedDict[str, list[str]]):
        self.class_names.clear()
        self.obj_names.clear()
        self.simple_shunting_names.clear()
        self.adj_point_shunting_names.clear()

        self.root_node.removeRows(0, self.root_node.rowCount())
        self.root_node.emitDataChanged()
        for class_name in d:
            self.class_names.add(class_name)
            item_class = QStandardItem(class_name)
            item_class.setEditable(False)
            item_class.setSelectable(False)
            self.root_node.appendRow(item_class)
            self.cls_name_to_index[class_name] = item_class.index()
            for obj_name in d[class_name]:
                if class_name == "PpoShuntingSignal":
                    self.simple_shunting_names.add(obj_name)
                if class_name == "PpoShuntingSignalWithTrackAnD":
                    self.adj_point_shunting_names.add(obj_name)
                self.obj_names.add(obj_name)
                item_obj = QStandardItem(obj_name)
                item_class.appendRow(item_obj)
                self.index_to_obj_name[item_obj.index()] = obj_name
        for idx in self.expanded_indexes:
            self.expand(idx)
        self.restore_scrollbar_state()
        print("restore state", self.verticalScrollBar().sliderPosition(), self.old_slider_position)

    # def mouseDoubleClickEvent(self, a0: QMouseEvent) -> None:
    #     data = self.indexAt(a0.localPos().toPoint()).data()
    #     if data:
    #         self.send_attrib_request.emit(data)

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.LeftButton:
            data = self.indexAt(a0.localPos().toPoint()).data()
            if not (data is None):
                self.send_attrib_request.emit(data)

    def contextMenuEvent(self, a0: QContextMenuEvent):
        data = self.indexAt(a0.pos()).data()
        if data and (not data.isspace()) and ("OBJECTS" not in data):
            contextMenu = QMenu(self)
            if data in self.class_items:
                contextMenu.addAction("Add new object").triggered.\
                    connect(partial(self.send_add_new_, val=self.indexAt(a0.pos()).data()))

                # internalMenu = QMenu("Default type of interface", contextMenu)
                # internalMenu.addAction("Ci")
                # internalMenu.addAction("Ri")
                # contextMenu.addMenu(internalMenu)

            elif data in self.obj_names:
                contextMenu.addAction("Get attributes").triggered.\
                    connect(partial(self.send_attrib_request_, val=self.indexAt(a0.pos()).data()))
                contextMenu.addAction("Remove").triggered.\
                    connect(partial(self.send_remove_request_, val=self.indexAt(a0.pos()).data()))
                if data in self.simple_shunting_names:
                    contextMenu.addAction("Move to adj point shunting").triggered.\
                        connect(partial(self.send_change_class_request_,
                                        val=self.indexAt(a0.pos()).data(),
                                        cls_to="PpoShuntingSignalWithTrackAnD"))
                if data in self.adj_point_shunting_names:
                    contextMenu.addAction("Move to simple shunting").triggered.\
                        connect(partial(self.send_change_class_request_,
                                        val=self.indexAt(a0.pos()).data(),
                                        cls_to="PpoShuntingSignal"))

            contextMenu.exec_(self.mapToGlobal(a0.pos()))

    def item_changed(self, item: QStandardItem):
        self.save_scrollbar_state()
        print("save state in item_changed", self.verticalScrollBar().sliderPosition(), self.old_slider_position)
        self.send_rename.emit(self.index_to_obj_name[item.index()], item.text())

    def send_add_new_(self, val: str):
        self.add_expanded_index(self.cls_name_to_index[val])
        self.save_scrollbar_state()
        print("save state in send_add_new_", self.verticalScrollBar().sliderPosition())
        self.send_add_new.emit(val)

    def send_attrib_request_(self, val: str):
        # self.save_scrollbar_state()
        self.send_attrib_request.emit(val)

    def send_remove_request_(self, val: str):
        self.save_scrollbar_state()
        print("save state in send_remove_request_", self.verticalScrollBar().sliderPosition())
        self.send_remove_request.emit(val)

    def send_change_class_request_(self, val: str, cls_to: str):
        self.save_scrollbar_state()
        print("save state in send_change_class_request_", self.verticalScrollBar().sliderPosition())
        self.send_change_class_request.emit(val, cls_to)

    def save_scrollbar_state(self):
        vsb = self.verticalScrollBar()
        # print("ver sc b in save = ", self.verticalScrollBar())
        # print("max, min in save", self.verticalScrollBar().maximum(), self.verticalScrollBar().minimum())
        self.old_slider_position = vsb.sliderPosition()
        self.old_slider_range = (vsb.minimum(), vsb.maximum())
        # self.old_slider_position = self.verticalScrollBar().value()

    def restore_scrollbar_state(self):
        vsb = self.verticalScrollBar()
        # print("ver sc b in restore = ", self.verticalScrollBar())
        # print("max, min in restore", self.verticalScrollBar().maximum(), self.verticalScrollBar().minimum())
        # vsb.setMinimum(self.old_slider_range[0])
        # vsb.setMaximum(self.old_slider_range[1])
        vsb.setSliderPosition(self.old_slider_position)
        # print("after restore str", self.verticalScrollBar().sliderPosition(), self.old_slider_position)
        # self.verticalScrollBar().setValue(self.old_slider_position)


class TreeToolBar(QToolBar):
    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.setMinimumWidth(500)
        self.tree_view = TreeToolBarWidget()
        self.addWidget(self.tree_view)


class AttributeWidget(QWidget):
    attr_edited = pyqtSignal(list, str)
    add_element_request = pyqtSignal(list)
    remove_element_request = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        self.external_layout = QVBoxLayout()
        self.internal_widget = QWidget()
        # self.internal_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.scroll_widget = QScrollArea()
        self.scroll_widget.setWidgetResizable(True)
        self.external_layout.addWidget(self.scroll_widget)
        self.scroll_widget.setWidget(self.internal_widget)
        self.column_layout = QVBoxLayout()
        self.column_layout.setSpacing(0)
        self.column_layout.setContentsMargins(0, 0, 0, 0)
        self.internal_widget.setLayout(self.column_layout)
        self.setLayout(self.external_layout)
        self.space_indexes = []
        self.last_clicked_index = 0
        self.widget_indexes = {}
        self.last_clicked_point = (0, 0)
        self.old_slider_position = 0
        self.row_count = 0

    def edit_finished(self, address):
        line_edit: QLineEdit = self.sender()
        self.old_slider_position = self.scroll_widget.verticalScrollBar().sliderPosition()
        if line_edit.completer():
            completer = line_edit.completer()
            completer.popup().setVisible(False)
        self.attr_edited.emit(address, line_edit.text())

    def add_element(self, address):
        self.old_slider_position = self.scroll_widget.verticalScrollBar().sliderPosition()
        self.add_element_request.emit(address)

    def remove_element(self, address):
        self.old_slider_position = self.scroll_widget.verticalScrollBar().sliderPosition()
        self.remove_element_request.emit(address)

    def reset_color_editing(self, s: str):
        line_edit: QLineEdit = self.sender()
        line_edit.setStyleSheet("background-color: white")

    def recursive_remove_widget(self, start_widget: QWidget):
        for child in start_widget.children():
            if isinstance(child, QWidget):
                self.recursive_remove_widget(child)
            if not (start_widget is self.internal_widget):
                start_widget.setParent(None)

    def attrib_dict_handling(self, attr_dict: dict):
        for idx in reversed(self.space_indexes):
            self.column_layout.removeItem(self.column_layout.itemAt(idx))
        self.space_indexes = []
        self.recursive_remove_widget(self.internal_widget)
        self.attr_dict_expansion(attr_dict)

    def generate_horizontal_widget(self) -> QHBoxLayout:
        horizontal_wgt = QWidget(self)
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(2, 2, 2, 2)
        horizontal_wgt.setLayout(horizontal_layout)
        self.column_layout.addWidget(horizontal_wgt)
        self.row_count += 1
        return horizontal_layout

    def add_central_label(self, text: str):
        """ title tag handling """
        horizontal_layout = self.generate_horizontal_widget()
        label = QLabel(text)
        label.setMinimumHeight(20)
        label.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(label, alignment=Qt.AlignCenter)

    def add_label_with_line_edit(self, label_text: str) -> QLineEdit:
        """ single handling """
        horizontal_layout = self.generate_horizontal_widget()
        label = QLabel(label_text)
        label.setMinimumHeight(20)
        label.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(label)  # , alignment=Qt.AlignCenter

        line_edit = QLineEdit()
        line_edit.setParent(self.internal_widget)
        line_edit.setMinimumHeight(20)
        line_edit.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(line_edit)
        return line_edit

    def add_label_with_add_button(self, label_text: str):
        """ list handling """
        horizontal_layout = self.generate_horizontal_widget()
        label = QLabel(label_text)
        label.setMinimumHeight(20)
        label.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(label)  # , alignment=Qt.AlignCenter

        button = QPushButton("Add")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button)

    def add_line_edit_with_remove_button(self):  # , label_text: str
        """ simple list handling """
        horizontal_layout = self.generate_horizontal_widget()
        line_edit = QLineEdit()
        line_edit.setParent(self.internal_widget)
        line_edit.setMinimumHeight(20)
        line_edit.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(line_edit)

        button = QPushButton("Remove")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button)

    def add_central_remove_button(self):
        """ object list handling """
        horizontal_layout = self.generate_horizontal_widget()
        button = QPushButton("Remove")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button, alignment=Qt.AlignCenter)

    def decorate_line_edit_by_properties(self, le: QLineEdit, prop: dict):
        print("decor_line_edit_by_properties", prop)

    def dict_of_attributes_handling(self, d: dict):
        for attr_name, attr_value in d.items():
            if isinstance(attr_value, dict):
                if SINGLE_ATTRIBUTE_KEY in attr_value:
                    line_edit = self.add_label_with_line_edit(attr_name)
                    self.decorate_line_edit_by_properties(line_edit, attr_value[SINGLE_ATTRIBUTE_KEY])
                else:
                    self.add_central_label(attr_name)
                    self.dict_of_attributes_handling(attr_value)
                    print("in else 1 for elem:", attr_value)
            elif isinstance(attr_value, list):
                self.add_label_with_add_button(attr_name)
                for elem in attr_value:
                    elem: dict
                    if SINGLE_ATTRIBUTE_KEY in elem:
                        self.add_line_edit_with_remove_button()
                    else:
                        self.dict_of_attributes_handling(elem)
                        self.add_central_remove_button()
                        print("in else 2 for elem:", elem)

    def attr_dict_expansion(self, attr_dict: dict):
        self.row_count = 0
        tag = attr_dict["tag"]
        data: dict[str, Any] = attr_dict["data"]
        # SPACED_STARTS
        self.add_central_label(tag)
        self.dict_of_attributes_handling(data)
        self.space_indexes.append(self.column_layout.count())
        self.column_layout.addStretch(1)
        self.internal_widget.setMinimumHeight(self.row_count*28)

    def list_expansion(self, info_list: list):
        self.internal_widget.setMinimumHeight(len(info_list)*28)
        for row in info_list:
            if row[0][0] == "Spacing":
                self.space_indexes.append(self.column_layout.count())
                self.column_layout.addSpacing(int(row[0][1]))
                continue
            else:
                horizontal_wgt = QWidget(self)
                horizontal_layout = QHBoxLayout()
                horizontal_layout.setContentsMargins(2, 2, 2, 2)
                horizontal_wgt.setLayout(horizontal_layout)
                for elem in row:
                    elem: tuple[str, Any]
                    if elem[0] == "Label":
                        od: OrderedDict[str, Any] = elem[1]
                        label = QLabel(od["current_value"])
                        label.setMinimumHeight(20)
                        label.setContentsMargins(2, 2, 2, 2)
                        if od["is_centered"]:
                            horizontal_layout.addWidget(label, alignment=Qt.AlignCenter)
                        else:
                            horizontal_layout.addWidget(label)
                    if elem[0] == "Button":
                        od: OrderedDict[str, Any] = elem[1]
                        if od["is_add_button"]:
                            button = QPushButton("Add")
                            button.setMinimumHeight(20)
                            button.setContentsMargins(2, 2, 2, 2)
                            button.clicked.connect(partial(self.add_element, address=od["address"]))
                        else:
                            button = QPushButton("Remove")
                            button.setMinimumHeight(20)
                            button.setContentsMargins(2, 2, 2, 2)
                            button.clicked.connect(partial(self.remove_element, address=od["address"]))
                        horizontal_layout.addWidget(button)
                    if elem[0] == "LineEdit":
                        od: OrderedDict[str, Any] = elem[1]
                        line_edit = QLineEdit(od["current_value"])
                        line_edit.setParent(self.internal_widget)
                        line_edit.setMinimumHeight(20)
                        line_edit.setContentsMargins(2, 2, 2, 2)
                        possible_values = od["possible_values"]
                        if possible_values:
                            completer = QCompleter(possible_values, self)
                            line_edit.setCompleter(completer)
                        line_edit.returnPressed.connect(partial(self.edit_finished, address=od["address"]))
                        line_edit.textEdited.connect(self.reset_color_editing)
                        check_status = od["check_status"]
                        if check_status:
                            line_edit.setStyleSheet("background-color: #f00")
                        elif od["current_value"]:
                            line_edit.setStyleSheet("background-color: #0f0")
                        else:
                            line_edit.setStyleSheet("background-color: white")
                        horizontal_layout.addWidget(line_edit)
                self.column_layout.addWidget(horizontal_wgt)
        self.space_indexes.append(self.column_layout.count())
        self.column_layout.addStretch(1)
        self.scroll_widget.verticalScrollBar().setSliderPosition(self.old_slider_position)


class AttributeToolBar(QToolBar):
    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.setMinimumWidth(300)
        self.column_wgt = AttributeWidget()
        self.addWidget(self.column_wgt)

        # label = QLabel("LALA")
        # label.setFixedSize(1000, 1000)
        # label.setStyleSheet("font-size: 320px")
        # self.scroll_area = QScrollArea()
        # self.scroll_area.setWidget(label)
        # self.scroll_area.ensureWidgetVisible(label)
        # self.addWidget(self.scroll_area)


if __name__ == "__main__":
    print(camelcase_to_downcase("IObjectsCodeGenerator"))
