from collections import OrderedDict
from functools import partial, partialmethod
from typing import Union, Any
import os

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QToolBar, QTreeView, QVBoxLayout, QHBoxLayout, QLabel, \
    QLineEdit, QWidget, QScrollArea, QComboBox, QCompleter, QMenu, QPushButton, QSizePolicy, QAbstractScrollArea, \
    QDialog, QFrame, QGroupBox, QStyleOptionGroupBox, QCheckBox, QRadioButton, QActionGroup, QAction
from PyQt5.QtGui import QWindow
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QModelIndex
from PyQt5.Qt import QStandardItemModel, QStandardItem, QMouseEvent, QContextMenuEvent

from file_object_conversions import attr_name_from_object_to_file
from project_properties_dialog import ProjectPropertiesDialog
from config import MAIN_CLASSES_TREE, SPACED_STARTS, ONE_LINE_HEIGHT, SINGLE_ATTRIBUTE_PROPERTIES, \
    NAMED_ATTRIBUTE_PROPERTIES, ADDRESS, PROPERTIES, INTERNAL_STRUCTURE, LINE_EDIT_STYLESHEET, \
    FILE_NAME_TO_CLASSES, DEFAULT_EXPORT_FORMAT

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
    input_config_file_opened = pyqtSignal(str)
    tpl_opened = pyqtSignal(str)
    obj_id_opened = pyqtSignal(str)
    template_directory_selected = pyqtSignal(str)
    config_directory_selected = pyqtSignal(str)
    generate_file = pyqtSignal(str)
    export_format = pyqtSignal(str)
    clear_objects = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setGeometry(-1000, 50, 800, 900)
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

        gen_menu = menu_bar.addMenu('&Import/export')
        obj_types_menu = gen_menu.addMenu("Export to file")
        for file_name in FILE_NAME_TO_CLASSES:
            obj_types_menu.addAction(file_name).triggered.connect(partial(self.gen_single_file, obj_group_name=file_name))
        gen_menu.addAction("&Export all").triggered.connect(self.gen_all_files)
        format_menu = gen_menu.addMenu("Export format")
        ag = QActionGroup(format_menu)
        for format_str in ["json", "xml"]:
            act = format_menu.addAction(format_str)
            act.triggered.connect(partial(self.set_export_format, format_str=format_str))
            act.setCheckable(True)
            ag.addAction(act)
            if format_str == DEFAULT_EXPORT_FORMAT:
                act.setChecked(True)

        gen_menu.addSeparator()

        gen_menu.addAction("&Import...").triggered.connect(self.import_config_file)
        gen_menu.addAction("&Clear objects").triggered.connect(self.clear_objects)
        # import_menu = gen_menu.addMenu("Import")

        # dialogs
        self.ppd = ProjectPropertiesDialog(self)

        self.show()

    def set_export_format(self, format_str: str):
        self.export_format.emit(format_str)

    def open_prop_window(self):
        self.ppd.show()

    def import_config_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', './config_examples/ribatskoe_json', 'json, xml Files (*.xml *.json)')
        if not file_name:
            return
        self.input_config_file_opened.emit(file_name)

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
        for file_name in FILE_NAME_TO_CLASSES:
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

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.LeftButton:
            data = self.indexAt(a0.localPos().toPoint()).data()
            if not (data is None):
                self.send_attrib_request.emit(data)

    def contextMenuEvent(self, a0: QContextMenuEvent):
        data = self.indexAt(a0.pos()).data()
        if data and (not data.isspace()) and ("OBJECTS" not in data):
            contextMenu = QMenu(self)
            contextMenu.setStyleSheet(LINE_EDIT_STYLESHEET)
            if data in self.class_items:
                contextMenu.addAction("Add new object").triggered.\
                    connect(partial(self.send_add_new_, val=self.indexAt(a0.pos()).data()))
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
        self.send_rename.emit(self.index_to_obj_name[item.index()], item.text())

    def send_add_new_(self, val: str):
        self.add_expanded_index(self.cls_name_to_index[val])
        self.save_scrollbar_state()
        self.send_add_new.emit(val)

    def send_attrib_request_(self, val: str):
        self.send_attrib_request.emit(val)

    def send_remove_request_(self, val: str):
        self.save_scrollbar_state()
        self.send_remove_request.emit(val)

    def send_change_class_request_(self, val: str, cls_to: str):
        self.save_scrollbar_state()
        self.send_change_class_request.emit(val, cls_to)

    def save_scrollbar_state(self):
        vsb = self.verticalScrollBar()
        self.old_slider_position = vsb.sliderPosition()
        self.old_slider_range = (vsb.minimum(), vsb.maximum())

    def restore_scrollbar_state(self):
        vsb = self.verticalScrollBar()
        vsb.setSliderPosition(self.old_slider_position)


class TreeToolBar(QToolBar):
    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.setMinimumWidth(500)
        self.tree_view = TreeToolBarWidget()
        self.addWidget(self.tree_view)


class CustomAttributeLineEdit(QLineEdit):
    get_suggested_value = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.address = None

    def contextMenuEvent(self, a0: QContextMenuEvent) -> None:
        contextMenu = QMenu(self)
        contextMenu.setStyleSheet(LINE_EDIT_STYLESHEET)
        contextMenu.addAction("Get suggestion").triggered.\
            connect(self.send_get_suggested_value)
        contextMenu.exec_(self.mapToGlobal(a0.pos()))

    def send_get_suggested_value(self):
        self.get_suggested_value.emit(self.address)


def store_v_scrollbar_position(func):
    def internal(*args, **kwargs):
        args[0].old_slider_position = args[0].scroll_widget.verticalScrollBar().sliderPosition()
        func(*args, **kwargs)
    return internal


class AttributeWidget(QWidget):
    attr_edited = pyqtSignal(list, str)
    add_element_request = pyqtSignal(list)
    remove_element_request = pyqtSignal(list)
    get_suggested_value = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        self.external_layout = QVBoxLayout()
        self.internal_widget = QWidget()
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

    @store_v_scrollbar_position
    def edit_finished(self, address):
        line_edit: QLineEdit = self.sender()
        if line_edit.completer():
            completer = line_edit.completer()
            completer.popup().setVisible(False)
        self.attr_edited.emit(address, line_edit.text())

    @store_v_scrollbar_position
    def add_element(self, address, boolean_clicked):
        self.add_element_request.emit(address)

    @store_v_scrollbar_position
    def remove_element(self, address, boolean_clicked):
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
        if attr_dict:
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

    def add_label_with_line_edit(self, label_text: str, address: list) -> tuple[QLabel, CustomAttributeLineEdit]:
        """ single handling """
        horizontal_layout = self.generate_horizontal_widget()
        label = QLabel(attr_name_from_object_to_file(label_text))
        label.setMinimumHeight(20)
        label.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(label)

        line_edit = CustomAttributeLineEdit()
        line_edit.setParent(self.internal_widget)
        line_edit.setMinimumHeight(20)
        line_edit.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(line_edit)

        line_edit.returnPressed.connect(partial(self.edit_finished, address))
        line_edit.textEdited.connect(self.reset_color_editing)
        line_edit.address = address
        line_edit.get_suggested_value.connect(self.save_scrollbar_position_and_get_suggested_value)

        return label, line_edit

    @store_v_scrollbar_position
    def save_scrollbar_position_and_get_suggested_value(self, addr: list):
        self.get_suggested_value.emit(addr)

    def add_label_with_add_button(self, label_text: str, address: list) -> QLabel:
        """ list handling """
        horizontal_layout = self.generate_horizontal_widget()
        label = QLabel(label_text)
        label.setMinimumHeight(20)
        label.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(label)

        button = QPushButton("Add")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button)

        button.clicked.connect(partial(self.add_element, address))

        return label

    def add_line_edit_with_remove_button(self, elem: dict, address: list) -> CustomAttributeLineEdit:  # , label_text: str
        """ simple list handling """
        horizontal_layout = self.generate_horizontal_widget()
        line_edit = CustomAttributeLineEdit()
        line_edit.setParent(self.internal_widget)
        line_edit.setMinimumHeight(20)
        line_edit.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(line_edit)

        button = QPushButton("Remove")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button)

        line_edit.returnPressed.connect(partial(self.edit_finished, address))
        line_edit.textEdited.connect(self.reset_color_editing)
        line_edit.address = address
        button.clicked.connect(partial(self.remove_element, address))

        return line_edit

    def add_central_remove_button(self, address: list):
        """ object list handling """
        horizontal_layout = self.generate_horizontal_widget()
        button = QPushButton("Remove")
        button.setMinimumHeight(20)
        button.setContentsMargins(2, 2, 2, 2)
        horizontal_layout.addWidget(button, alignment=Qt.AlignCenter)

        button.clicked.connect(partial(self.remove_element, address))

    def decorate_line_edit_and_label_by_properties(self, le: QLineEdit, label: QLabel, prop: dict):
        print("decor_line_edit_by_properties", prop)
        text = prop['displaying_value']
        is_suggested = prop['is_suggested']
        error_message = prop['error_message']
        possible_values = prop['possible_values']
        is_required = prop['is_required']
        le.setText(text)
        if error_message:
            le.setStyleSheet("background-color: #f00")
        elif is_suggested:
            le.setStyleSheet("background-color: #ff0")
        elif text:
            le.setStyleSheet("background-color: #0f0")
        else:
            le.setStyleSheet("background-color: white")
        if possible_values:
            completer = QCompleter(possible_values, self)
            le.setCompleter(completer)
        tooltip = ""
        if error_message:
            tooltip += "Error: " + error_message
        if possible_values:
            if error_message:
                tooltip += "\n"
            pos_val_str = "Possible values: "
            if len(possible_values) < 8:
                tooltip += pos_val_str + "\n" + "\n".join(possible_values)
            else:
                tooltip += pos_val_str + "\n" + "\n".join(possible_values[:8]) + "\n..."
        le.setToolTip(tooltip)
        if is_required:
            current_label_text = label.text()
            if current_label_text.strip()[-1] != "*":
                label.setText(current_label_text + "*")
                label.setToolTip("Required attribute")

    def spaces_append_handling(self, attr_name: str, set_kw_applied):
        for spaced_start in SPACED_STARTS:
            if attr_name.startswith(spaced_start) and (spaced_start not in set_kw_applied):
                set_kw_applied.add(spaced_start)
                self.space_indexes.append(self.column_layout.count())
                self.column_layout.addSpacing(ONE_LINE_HEIGHT)
                self.row_count += 1

    def dict_of_attributes_handling(self, d: dict):
        space_keywords_applied = set()
        for attr_name, attr_dict in d.items():
            attr_name: str
            named_attr_props = attr_dict[NAMED_ATTRIBUTE_PROPERTIES]
            named_attr_address = named_attr_props["address"]
            named_attr_is_list = named_attr_props["is_list"]
            named_attr_obj_type = named_attr_props["obj_type"]
            single_attr_props = attr_dict[SINGLE_ATTRIBUTE_PROPERTIES]
            self.spaces_append_handling(attr_name, space_keywords_applied)
            if not named_attr_is_list:
                if named_attr_obj_type == "str":
                    address = single_attr_props[ADDRESS]
                    props = single_attr_props[PROPERTIES]
                    label, line_edit = self.add_label_with_line_edit(attr_name, address)
                    self.decorate_line_edit_and_label_by_properties(line_edit, label, props)
                else:
                    self.add_central_label(attr_name)
                    internal_structure = single_attr_props[INTERNAL_STRUCTURE]
                    self.dict_of_attributes_handling(internal_structure)
            else:
                if named_attr_obj_type == "str":
                    label = self.add_label_with_add_button(attr_name, named_attr_address)
                    for single_attr in single_attr_props:
                        address = single_attr[ADDRESS]
                        props = single_attr[PROPERTIES]
                        line_edit = self.add_line_edit_with_remove_button(props, address)
                        self.decorate_line_edit_and_label_by_properties(line_edit, label, props)
                else:
                    self.add_label_with_add_button(attr_name, named_attr_address)
                    for single_attr in single_attr_props:
                        address = single_attr[ADDRESS]
                        internal_structure = single_attr[INTERNAL_STRUCTURE]
                        self.dict_of_attributes_handling(internal_structure)
                        self.add_central_remove_button(address)
        self.scroll_widget.verticalScrollBar().setSliderPosition(self.old_slider_position)

    def attr_dict_expansion(self, attr_dict: dict):
        self.row_count = 0
        tag = attr_dict["tag"]
        data: dict[str, Any] = attr_dict["data"]
        self.add_central_label(tag)
        self.dict_of_attributes_handling(data)
        self.space_indexes.append(self.column_layout.count())
        self.column_layout.addStretch(1)
        self.internal_widget.setMinimumHeight(self.row_count * ONE_LINE_HEIGHT)


class AttributeToolBar(QToolBar):
    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.setMinimumWidth(300)
        self.column_wgt = AttributeWidget()
        self.addWidget(self.column_wgt)


if __name__ == "__main__":
    print(camelcase_to_downcase("IObjectsCodeGenerator"))
