import sys
import traceback

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject

from main_window import MainWindow
from file_tpl_handler import FileTPLHandler
from file_id_handler import FileIdHandler
# from objects_handler import ObjectsHandler
from nv_oh import ObjectsHandler  # nv_oh_backup nv_oh


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("Oбнаружена ошибка !:", tb)


sys.excepthook = excepthook


class Director(QObject):
    def __init__(self):
        super().__init__()
        self.mw = MainWindow()
        self.file_tpl_handler = FileTPLHandler()
        self.file_id_handler = FileIdHandler()
        self.objects_handler = ObjectsHandler()

        self.mw.tpl_opened.connect(self.file_tpl_handler.handle_tpl)
        self.mw.tree_toolbar.tree_view.send_attrib_request.connect(self.objects_handler.got_object_name)
        self.mw.tree_toolbar.tree_view.send_add_new.connect(self.objects_handler.got_add_new)
        self.mw.tree_toolbar.tree_view.send_rename.connect(self.objects_handler.got_rename)
        self.mw.tree_toolbar.tree_view.send_change_class_request.connect(self.objects_handler.got_change_cls_request)
        self.mw.tree_toolbar.tree_view.send_remove_request.connect(self.objects_handler.got_remove_object_request)
        self.mw.obj_id_opened.connect(self.file_id_handler.handle_objects_id)
        self.objects_handler.send_attrib_dict.connect(self.mw.attribute_toolbar.column_wgt.attrib_dict_handling)
        self.mw.ppd.checkbox_auto_add_interface_object.connect(self.objects_handler.set_auto_add_interface_objects)
        self.mw.ppd.radio_signal_interface_type.connect(self.objects_handler.set_signal_interface_type)
        self.mw.ppd.radio_point_interface_type.connect(self.objects_handler.set_point_interface_type)
        self.mw.ppd.radio_derail_interface_type.connect(self.objects_handler.set_derail_interface_type)

        self.file_tpl_handler.dict_formed.connect(self.objects_handler.file_tpl_got)
        self.objects_handler.send_objects_tree.connect(self.mw.tree_toolbar.tree_view.from_dict)
        self.file_id_handler.dict_formed.connect(self.objects_handler.file_obj_id_got)
        self.mw.attribute_toolbar.column_wgt.attr_edited.connect(self.objects_handler.attr_changed)
        self.mw.attribute_toolbar.column_wgt.add_element_request.connect(self.objects_handler.add_attrib_list_element)
        self.mw.attribute_toolbar.column_wgt.remove_element_request.connect(self.objects_handler.remove_attrib_list_element)
        self.mw.attribute_toolbar.column_wgt.get_suggested_value.connect(self.objects_handler.get_suggested_value)

        self.mw.generate_file.connect(self.objects_handler.generate_file)
        self.mw.export_format.connect(self.objects_handler.set_export_format)
        self.mw.input_config_file_opened.connect(self.objects_handler.input_config_file_opened)
        self.mw.clear_objects.connect(self.objects_handler.clear_objects)

        # self.mw.auto_open_tpl()
        self.objects_handler.send_objects_tree.emit(self.objects_handler.str_objects_tree)
        self.mw.ppd.init_buttons_state()
        # self.mw.open_prop_window()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    d = Director()
    sys.exit(app.exec_())
