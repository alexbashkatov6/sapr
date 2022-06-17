from collections import OrderedDict
import xml.etree.ElementTree as ElTr

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class FileIdHandler(QObject):
    dict_formed = pyqtSignal(OrderedDict)

    def __init__(self):
        super().__init__()
        self.id_objects: OrderedDict[str, list[str]] = OrderedDict()

    def handle_objects_id(self, file_name: str):
        self.id_objects = OrderedDict()
        tree = ElTr.parse(file_name)
        root = tree.getroot()
        for child in root:
            type_ = child.attrib['Type']
            tag = child.attrib['Tag']
            if type_ not in self.id_objects:
                self.id_objects[type_] = []
            self.id_objects[type_].append(tag)
        self.dict_formed.emit(self.id_objects)
        # print(self.id_objects)
