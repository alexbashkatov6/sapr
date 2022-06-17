from collections import OrderedDict
import xml.etree.ElementTree as ElTr

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class FileTPLHandler(QObject):
    dict_formed = pyqtSignal(OrderedDict)

    def __init__(self):
        super().__init__()
        self.t_objects: OrderedDict[str, list[str]] = OrderedDict()

    def handle_tpl(self, file_name: str):
        self.t_objects = OrderedDict()
        tree = ElTr.parse(file_name)
        root = tree.getroot()
        for child in root:
            type_ = child.attrib['Type']
            tag = child.attrib['Tag']
            if type_ not in self.t_objects:
                self.t_objects[type_] = []
            self.t_objects[type_].append(tag)
        self.dict_formed.emit(self.t_objects)
