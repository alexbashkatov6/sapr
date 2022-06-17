from __future__ import annotations

import os.path
from collections import OrderedDict
from typing import Type, Iterable, Optional, Any, Callable, Union
import json

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject

from config import FILE_NAME_TO_CLASSES, MAIN_CLASSES_TREE, TPL_TO_OBJ_ID, \
    DEFAULT_SIGNAL_I_TYPE, DEFAULT_POINT_I_TYPE, DEFAULT_DERAIL_I_TYPE, DEFAULT_AUTO_ADD_IO, DEFAULT_EXPORT_FORMAT
from attribute_management import AttributeAddress, AttributeCommand, \
    ComplexAttributeManagementCommand, StrSingleAttribute, UnaryAttribute
from aar_descriptor import AttributeAccessRulesDescriptor
from descr_value_checkers import ValueInSetChecker
from ppo_object import set_tag, get_tag, PpoObject, PpoAnDtrack, PpoLightSignalCi, PpoLightSignalRi, PpoRoutePointer, \
    PpoRoutePointerRi, PpoPoint, PpoPointMachineCi, PpoAutomaticBlockingSystem, PpoAutomaticBlockingSystemRi, \
    PpoSemiAutomaticBlockingSystem, PpoSemiAutomaticBlockingSystemRi, PpoRailCrossing, PpoRailCrossingRi, \
    PpoTrackCrossroad, PpoTrackUnit, PpoTrackEncodingPoint, PpoTrainSignal, PpoWarningSignal, PpoRepeatSignal, PpoTrack, \
    PpoTrackAnDwithPoint, PpoLineEnd, AdditionalSwitch, SectionAndIgnoreCondition, PpoControlDeviceDerailmentStockCi, \
    PpoCodeEnablingRelayALS, PpoCabinetUsoBk, PpoInsulationResistanceMonitoring, PpoPointMachinesCurrentMonitoring, \
    PpoControlAreaBorder, PpoShuntingSignal, PpoPointSection, PpoTrackSection

""" ------------------------------------- Globals ------------------------------------ """

RELATED_INTERFACE_CLASSES = {"PpoTrainSignal": "PpoLightSignal",
                             "PpoShuntingSignal": "PpoLightSignal",
                             "PpoRoutePointer": "PpoRoutePointer",
                             "PpoAutomaticBlockingSystem": "PpoAutomaticBlockingSystem",
                             "PpoSemiAutomaticBlockingSystem": "PpoSemiAutomaticBlockingSystem"}


class TagRepeatingError(Exception):
    pass


class ObjectsHandler(QObject):
    send_objects_tree = pyqtSignal(dict)
    send_attrib_dict = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.objects_tree: OrderedDict[str, OrderedDict[str, PpoObject]] = OrderedDict()  # output structure
        self.init_obj_tree()
        self.bind_checkers_storages()

        self.current_object: Optional[PpoObject] = None

        self.tech_to_interf_dict: dict[PpoObject, PpoObject] = {}
        self.interf_to_tech_dict: dict[PpoObject, PpoObject] = {}

        self.bool_tpl_got = False
        self.bool_obj_id_got = False
        self.tpl_dict: OrderedDict[str, list[str]] = OrderedDict()  # input structure from tpl
        self.obj_id_dict: OrderedDict[str, list[str]] = OrderedDict()

        self.auto_add_io: bool = DEFAULT_AUTO_ADD_IO
        self.signal_itype: str = DEFAULT_SIGNAL_I_TYPE
        self.point_itype: str = DEFAULT_POINT_I_TYPE
        self.derail_itype: str = DEFAULT_DERAIL_I_TYPE

        self.export_format = DEFAULT_EXPORT_FORMAT

    def set_export_format(self, format_str: str):
        self.export_format = format_str

    def input_config_file_opened(self, file_name: str):
        if file_name.endswith("json"):
            with open(file_name, "r") as f:
                d = json.load(f)
                for obj_d in d:
                    self.make_ppo_obj_from_dict(obj_d)

    def make_ppo_obj_from_dict(self, d: dict):
        cls_name = d["class"]
        obj: PpoObject = eval(cls_name)()
        obj.from_dict(d)
        self.insert_to_objects_tree(cls_name, get_tag(obj), obj)
        self.send_objects_tree.emit(self.str_objects_tree)

    def init_obj_tree(self):
        for partition in MAIN_CLASSES_TREE:
            for class_group in MAIN_CLASSES_TREE[partition]:
                class_names_list = MAIN_CLASSES_TREE[partition][class_group]
                for cls_name in class_names_list:
                    self.objects_tree[cls_name] = OrderedDict()

    def clear_objects(self):
        for cls_name in self.objects_tree:
            self.objects_tree[cls_name] = OrderedDict()
        self.send_objects_tree.emit(self.str_objects_tree)

    def bind_checkers_storages(self):
        PpoRoutePointer.routePointer.value_checkers = ValueInSetChecker(self.objects_tree["PpoRoutePointerRi"])
        PpoTrainSignal.routePointer.value_checkers = ValueInSetChecker(self.objects_tree["PpoRoutePointerRi"])
        PpoTrainSignal.groupRoutePointers.value_checkers = ValueInSetChecker(self.objects_tree["PpoRoutePointerRi"])
        PpoTrainSignal.uksps.value_checkers = ValueInSetChecker(self.objects_tree["PpoControlDeviceDerailmentStock"])
        PpoWarningSignal.signalTag.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrainSignal"])
        PpoRepeatSignal.signalTag.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrainSignal"])
        PpoTrack.trackUnit.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrackUnit"])
        PpoTrackAnDwithPoint.oppositeTrackAnDwithPoint.value_checkers = ValueInSetChecker(
            self.objects_tree["PpoTrackAnDwithPoint"])
        PpoLineEnd.trackUnit.value_checkers = ValueInSetChecker([self.objects_tree["PpoTrackUnit"], "nullptr"])
        AdditionalSwitch.point.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        SectionAndIgnoreCondition.section.value_checkers = ValueInSetChecker(self.objects_tree["PpoPointSection"])
        SectionAndIgnoreCondition.point.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoPoint.section.value_checkers = ValueInSetChecker(self.objects_tree["PpoPointSection"])
        PpoPoint.guardPlusPlus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoPoint.guardPlusMinus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoPoint.guardMinusPlus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoPoint.guardMinusMinus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoPoint.lockingPlus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPointSection"])
        PpoPoint.lockingPlusSignal.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrainSignal"])
        PpoPoint.lockingMinus.value_checkers = ValueInSetChecker(self.objects_tree["PpoPointSection"])
        PpoPoint.lockingMinusSignal.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrainSignal"])
        PpoPoint.pairPoint.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoAutomaticBlockingSystemRi.adjEnterSig.value_checkers = ValueInSetChecker(
            self.objects_tree["PpoLightSignalRi"])
        PpoTrackCrossroad.iObjTag.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrainNotificationRi"])
        PpoTrackCrossroad.railCrossing.value_checkers = ValueInSetChecker(self.objects_tree["PpoRailCrossingRi"])
        PpoRailCrossing.crossroad.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrackCrossroad"])
        PpoControlDeviceDerailmentStockCi.enterSignal.value_checkers = ValueInSetChecker(
            self.objects_tree["PpoTrainSignal"])
        PpoTrackUnit.iObjsTag.value_checkers = ValueInSetChecker([self.objects_tree["PpoTrackSection"],
                                                                  self.objects_tree["PpoPointSection"],
                                                                  self.objects_tree["PpoTrackAnDwithPoint"],
                                                                  self.objects_tree["PpoTrackAnD"]])
        PpoTrackUnit.evenTag.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrackEncodingPoint"])
        PpoTrackUnit.oddTag.value_checkers = ValueInSetChecker(self.objects_tree["PpoTrackEncodingPoint"])
        PpoCodeEnablingRelayALS.okv.value_checkers = ValueInSetChecker(
            self.objects_tree["PpoGeneralPurposeRelayOutput"])
        PpoTrackEncodingPoint.encUnitALS.value_checkers = ValueInSetChecker(
            self.objects_tree["PpoCodeEnablingRelayALS"])
        PpoTrackEncodingPoint.own.value_checkers = ValueInSetChecker([self.objects_tree["PpoTrackSection"],
                                                                      self.objects_tree["PpoPointSection"],
                                                                      self.objects_tree["PpoTrackAnDwithPoint"],
                                                                      self.objects_tree["PpoTrackAnD"]])
        PpoTrackEncodingPoint.freeState.value_checkers = ValueInSetChecker([self.objects_tree["PpoTrackSection"],
                                                                            self.objects_tree["PpoPointSection"],
                                                                            self.objects_tree["PpoTrackAnDwithPoint"],
                                                                            self.objects_tree["PpoTrackAnD"]])
        PpoTrackEncodingPoint.plusPoints.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoTrackEncodingPoint.minusPoints.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoCabinetUsoBk.lightSignals.value_checkers = ValueInSetChecker([self.objects_tree["PpoTrainSignal"],
                                                                         self.objects_tree["PpoWarningSignal"],
                                                                         self.objects_tree["PpoRepeatSignal"],
                                                                         self.objects_tree["PpoShuntingSignal"],
                                                                         self.objects_tree[
                                                                             "PpoShuntingSignalWithTrackAnD"]])
        PpoCabinetUsoBk.hiCratePointMachines.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoCabinetUsoBk.loCratePointMachines.value_checkers = ValueInSetChecker(self.objects_tree["PpoPoint"])
        PpoCabinetUsoBk.controlDeviceDerailmentStocks.value_checkers = \
            ValueInSetChecker(self.objects_tree["PpoControlDeviceDerailmentStockCi"])
        PpoInsulationResistanceMonitoring.cabinets.value_checkers = \
            ValueInSetChecker(self.objects_tree["PpoCabinetUsoBk"])
        PpoPointMachinesCurrentMonitoring.cabinets.value_checkers = \
            ValueInSetChecker(self.objects_tree["PpoCabinetUsoBk"])

    @property
    def obj_name_to_cls_name_dict(self):
        result: OrderedDict[str, str] = OrderedDict()
        for cls_name in self.objects_tree:
            result.update(OrderedDict.fromkeys(self.objects_tree[cls_name], cls_name))
        return result

    @property
    def str_objects_tree(self) -> OrderedDict[str, list[str]]:
        result: OrderedDict[str, list[str]] = OrderedDict()
        for cls_name in self.objects_tree:
            result[cls_name] = list(self.objects_tree[cls_name].keys())
        return result

    @property
    def name_to_obj_dict(self) -> OrderedDict[str, PpoObject]:
        result: OrderedDict[str, PpoObject] = OrderedDict()
        for cls_name in self.objects_tree:
            result.update(self.objects_tree[cls_name])
        return result

    def insert_to_objects_tree(self, cls_name: str, obj_name: str, obj: PpoObject, to_begin: bool = True):
        if cls_name not in self.objects_tree:
            self.objects_tree[cls_name] = OrderedDict()
        self.objects_tree[cls_name][obj_name] = obj
        self.objects_tree[cls_name].move_to_end(obj_name, not to_begin)

    def init_object(self, cls_name, obj_name):
        if cls_name == "PpoTrackAnD":
            cls_ = PpoAnDtrack
            obj = cls_()
            set_tag(obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, obj)

        elif cls_name in ["PpoTrainSignal", "PpoShuntingSignal"]:
            tpo_cls_ = eval(cls_name)
            tpo_obj = tpo_cls_()
            set_tag(tpo_obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, tpo_obj)

            if self.auto_add_io:
                if self.signal_itype == "Ci":
                    inter_cls_ = PpoLightSignalCi
                    inter_obj = inter_cls_()
                    set_tag(inter_obj, obj_name + "_Ci")
                    self.insert_to_objects_tree("PpoLightSignalCi", get_tag(inter_obj), inter_obj)
                    self.tech_to_interf_dict[tpo_obj] = inter_obj
                elif self.signal_itype == "Ri":
                    inter_cls_ = PpoLightSignalRi
                    inter_obj = inter_cls_()
                    set_tag(inter_obj, obj_name + "_Ri")
                    self.insert_to_objects_tree("PpoLightSignalRi", get_tag(inter_obj), inter_obj)
                    self.tech_to_interf_dict[tpo_obj] = inter_obj
                else:
                    assert False

        elif cls_name == "PpoRoutePointer":
            tpo_cls_ = PpoRoutePointer
            tpo_obj = tpo_cls_()
            set_tag(tpo_obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, tpo_obj)

            if self.auto_add_io:
                inter_cls_ = PpoRoutePointerRi
                inter_obj = inter_cls_()
                set_tag(inter_obj, obj_name + "_Ri")
                self.insert_to_objects_tree("PpoRoutePointerRi", get_tag(inter_obj), inter_obj)
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoPoint":
            tpo_cls_ = PpoPoint
            tpo_obj = tpo_cls_()
            set_tag(tpo_obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, tpo_obj)

            if self.auto_add_io:
                inter_cls_ = PpoPointMachineCi
                inter_obj = inter_cls_()
                set_tag(inter_obj, obj_name + "_Ci")
                self.insert_to_objects_tree("PpoPointMachineCi", get_tag(inter_obj), inter_obj)
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoAutomaticBlockingSystem":
            tpo_cls_ = PpoAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            set_tag(tpo_obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, tpo_obj)

            if self.auto_add_io:
                inter_cls_ = PpoAutomaticBlockingSystemRi
                inter_obj = inter_cls_()
                set_tag(inter_obj, obj_name + "_Ri")
                self.insert_to_objects_tree("PpoAutomaticBlockingSystemRi", get_tag(inter_obj), inter_obj)
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoSemiAutomaticBlockingSystem":
            tpo_cls_ = PpoSemiAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            set_tag(tpo_obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, tpo_obj)

            if self.auto_add_io:
                inter_cls_ = PpoSemiAutomaticBlockingSystemRi
                inter_obj = inter_cls_()
                set_tag(inter_obj, obj_name + "_Ri")
                self.insert_to_objects_tree("PpoSemiAutomaticBlockingSystemRi", get_tag(inter_obj), inter_obj)
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoTrackCrossroad":
            first_symbols = obj_name[:2]
            if first_symbols not in self.name_to_obj_dict:
                crossing_cls_ = PpoRailCrossing
                crossing_obj = crossing_cls_()
                set_tag(crossing_obj, first_symbols)
                self.insert_to_objects_tree("PpoRailCrossing", get_tag(crossing_obj), crossing_obj)

                if self.auto_add_io:
                    ri_crossing_cls_ = PpoRailCrossingRi
                    ri_crossing_obj = ri_crossing_cls_()
                    set_tag(ri_crossing_obj, first_symbols + "_Ri")
                    self.insert_to_objects_tree("PpoRailCrossingRi", get_tag(ri_crossing_obj), ri_crossing_obj)
                    self.tech_to_interf_dict[crossing_obj] = ri_crossing_obj

            cls_ = PpoTrackCrossroad
            obj = cls_()
            set_tag(obj, obj_name)
            self.insert_to_objects_tree("PpoTrackCrossroad", obj_name, obj)
        else:
            cls_: Type[PpoObject] = eval(cls_name)
            obj = cls_()
            set_tag(obj, obj_name)
            self.insert_to_objects_tree(cls_name, obj_name, obj)

    def attr_changed(self, address: list, new_attr_value: str):
        # print("attr changed", address, new_attr_value)
        obj = self.current_object
        attr_name = address[0][0]
        setattr(obj, attr_name, ComplexAttributeManagementCommand(AttributeCommand.set_single,
                                                                  AttributeAddress.from_list(address),
                                                                  new_attr_value))
        self.got_object_name(get_tag(self.current_object))

    def add_attrib_list_element(self, address: list):
        # print("add_attrib_list", address)
        obj = self.current_object
        attr_name = address[0][0]
        setattr(obj, attr_name, ComplexAttributeManagementCommand(AttributeCommand.append,
                                                                  AttributeAddress.from_list(address)))
        self.got_object_name(get_tag(self.current_object))

    def remove_attrib_list_element(self, address: list):
        # print("remove_attrib_list", address)
        obj = self.current_object
        attr_name = address[0][0]
        setattr(obj, attr_name, ComplexAttributeManagementCommand(AttributeCommand.remove,
                                                                  AttributeAddress.from_list(address)))
        self.got_object_name(get_tag(self.current_object))

    def got_change_cls_request(self, obj_name: str, to_cls_name: str):
        # 1. create new obj in new class
        new_name = self.got_add_new(to_cls_name)
        # 2. remove obj in old class
        self.got_remove_object_request(obj_name)
        # 3. rename obj in new class
        self.got_rename(new_name, obj_name)

        self.send_objects_tree.emit(self.str_objects_tree)

    def got_remove_object_request(self, name: str):
        cls_name = self.obj_name_to_cls_name_dict[name]
        tpo_obj = self.name_to_obj_dict[name]
        self.objects_tree[cls_name].pop(name)
        if tpo_obj in self.tech_to_interf_dict:
            i_obj = self.tech_to_interf_dict[tpo_obj]
            i_obj_name = get_tag(i_obj)
            cls_i_name = self.obj_name_to_cls_name_dict[i_obj_name]
            self.objects_tree[cls_i_name].pop(i_obj_name)

        self.send_objects_tree.emit(self.str_objects_tree)
        self.send_attrib_dict.emit({})

    def got_add_new(self, cls_name: str) -> str:
        i = 1
        while True:
            name_candidate = "{}_{}".format(cls_name, i)
            if name_candidate not in self.name_to_obj_dict:
                break
            i += 1
        self.init_object(cls_name, name_candidate)
        self.send_objects_tree.emit(self.str_objects_tree)
        return name_candidate

    def got_rename(self, old_name: str, new_name: str):
        if (not new_name) or new_name.isspace():
            self.rename_rejected_empty(old_name, new_name)
            self.send_objects_tree.emit(self.str_objects_tree)
            return
        if new_name in self.name_to_obj_dict:
            self.rename_rejected_existing(old_name, new_name)
            self.send_objects_tree.emit(self.str_objects_tree)
        else:
            obj = self.name_to_obj_dict[old_name]
            set_tag(obj, new_name)

            cls_name = self.obj_name_to_cls_name_dict[old_name]
            keys_list = list(self.objects_tree[cls_name].keys())
            index = keys_list.index(old_name)
            self.objects_tree[cls_name][new_name] = obj
            for key_index in range(index, len(keys_list)):
                self.objects_tree[cls_name].move_to_end(keys_list[key_index])
            self.objects_tree[cls_name].pop(old_name)
            self.send_objects_tree.emit(self.str_objects_tree)
            if obj in self.tech_to_interf_dict:
                interf_obj = self.tech_to_interf_dict[obj]
                str_tag = get_tag(interf_obj)
                if old_name in str_tag:
                    new_interf_name = str_tag.replace(old_name, new_name)
                    self.got_rename(str_tag, new_interf_name)

            # print("here")
        self.got_object_name(get_tag(self.current_object))

    def rename_rejected_existing(self, old_name: str, new_name: str):
        print("Rename from {} to {} rejected, name already exists".format(old_name, new_name))

    def rename_rejected_empty(self, old_name: str, new_name: str):
        print("Rename from {} to {} rejected, name is empty".format(old_name, new_name))

    def generate_file(self, file_name: str):
        objs = []
        for cls_name in FILE_NAME_TO_CLASSES[file_name]:
            objs.extend(reversed(self.objects_tree[cls_name].values()))
        obj_jsons = [obj.to_json_dict(True, True) for obj in objs]
        with open(os.path.join("output", "config", "{}.json".format(file_name)), "w") as write_file:
            json.dump(obj_jsons, write_file, indent=4)

    def got_object_name(self, name: str):
        print(f"got_object_name {name}")
        if name in self.obj_name_to_cls_name_dict:
            obj = self.name_to_obj_dict[name]
            self.current_object = obj
            self.send_attrib_dict.emit(obj.to_json_dict(to_file=False, is_base_object=True))

    def get_suggested_value(self, address: list):
        print("get_suggested_value", address)
        obj = self.current_object
        attr_name = address[0][0]
        named_attr: UnaryAttribute = getattr(obj, attr_name)
        single_attr: StrSingleAttribute = named_attr.single_attribute
        single_attr.needs_in_suggestion = True
        setattr(obj, attr_name, ComplexAttributeManagementCommand(AttributeCommand.set_single,
                                                                  AttributeAddress.from_list(address),
                                                                  ""))
        self.got_object_name(get_tag(self.current_object))

    ''' --------------------- TPL and OBJ-ID files operations --------------------- '''

    def init_objects_from_tpl(self):
        for cls_name in self.tpl_dict:
            for obj_name in self.tpl_dict[cls_name]:
                self.init_object(cls_name, obj_name)
        self.send_objects_tree.emit(self.str_objects_tree)

    def init_bounded_tpl_descriptors(self):
        pass

    def init_bounded_obj_id_descriptors(self):
        pass

    @staticmethod
    def check_not_repeating_names(odict):
        names = []
        for cls_name in odict:
            for obj_name in odict[cls_name]:
                if obj_name in names:
                    raise TagRepeatingError("Tag {} repeats".format(obj_name))
                names.append(obj_name)

    def file_tpl_got(self, d: OrderedDict[str, list[str]]):
        # print("tpl_got")
        self.bool_tpl_got = True
        self.check_not_repeating_names(d)
        self.tpl_dict = d
        if self.bool_obj_id_got:
            self.compare_tpl_and_obj_id_file()
        self.init_bounded_tpl_descriptors()

        self.init_objects_from_tpl()

    def file_obj_id_got(self, d: OrderedDict[str, list[str]]):
        # print("obj_id_got")
        self.bool_obj_id_got = True
        self.check_not_repeating_names(d)
        self.obj_id_dict = d
        if self.bool_tpl_got:
            self.compare_tpl_and_obj_id_file()
        self.init_bounded_obj_id_descriptors()
        if self.current_object:
            self.got_object_name(get_tag(self.current_object))

    def compare_tpl_and_obj_id_file(self):
        differences = {'tpl': [], 'obj_id': []}

        # cycle of append
        for cls_name in self.tpl_dict:
            if cls_name in TPL_TO_OBJ_ID:
                tpl_list = self.tpl_dict[cls_name]
                obj_id_list = self.obj_id_dict[TPL_TO_OBJ_ID[cls_name]]
                for tag in tpl_list:
                    if (cls_name, tag) not in differences['tpl']:
                        differences['tpl'].append((cls_name, tag))
                for tag in obj_id_list:
                    if (TPL_TO_OBJ_ID[cls_name], tag) not in differences['obj_id']:
                        differences['obj_id'].append((TPL_TO_OBJ_ID[cls_name], tag))

        # cycle of remove
        for cls_name in self.tpl_dict:
            if cls_name in TPL_TO_OBJ_ID:
                tpl_list = self.tpl_dict[cls_name]
                obj_id_list = self.obj_id_dict[TPL_TO_OBJ_ID[cls_name]]
                for tag in tpl_list:
                    if (TPL_TO_OBJ_ID[cls_name], tag) in differences['obj_id']:
                        differences['obj_id'].remove((TPL_TO_OBJ_ID[cls_name], tag))
                for tag in obj_id_list:
                    if (cls_name, tag) in differences['tpl']:
                        differences['tpl'].remove((cls_name, tag))

        print("Differences between tpl and objects_id")
        print("Tpl:")
        for elem in differences['tpl']:
            print(elem)
        print("Obj_id:")
        for elem in differences['obj_id']:
            print(elem)

    ''' ------------------------ Config menu properties setters ------------------------ '''

    def set_auto_add_interface_objects(self, ch: bool):
        self.auto_add_io = ch

    def set_signal_interface_type(self, itype: str):
        self.signal_itype = itype

    def set_point_interface_type(self, itype: str):
        self.point_itype = itype

    def set_derail_interface_type(self, itype: str):
        self.derail_itype = itype


if __name__ == '__main__':
    test_1 = False
    if test_1:
        pass
        # cell_obj = CompositeObjectCell()
        # cell_1 = ElementaryObjectCell()
        # cell_1.input_value = 1
        # cell_2 = ElementaryObjectCell()
        # cell_2.input_value = 2
        # cell_3 = ElementaryObjectCell()
        # cell_3.input_value = 3
        # cell_4 = ElementaryObjectCell()
        # cell_4.input_value = 4
        # cell_obj.mapping["1"] = cell_1
        # cell_obj.mapping["2"] = cell_2
        # cell_list = ListCell()
        # cell_list.cells.append(cell_3)
        # cell_list.cells.append(cell_4)
        # cell_obj.mapping["list"] = cell_list
        #
        # for row in cell_obj.view():
        #     print(row)
    # test_2 = False
    # if test_2:
    #     additSw = AdditionalSwitch()
    #     print(additSw.all_attributes)

    test_3 = False
    if test_3:
        pass
        # print(not_empty_extraction({1: "  ", 2: ""}))
        # print(not_empty_extraction([{1: "  ", 2: ""}]))

    test_4 = False
    if test_4:
        class A:
            a = AttributeAccessRulesDescriptor(is_list=True)


        class B:
            b = AttributeAccessRulesDescriptor(single_attribute_type=A, min_count=3)

        # ai_1 = AttributeIndex()
        # ai_2 = AttributeIndex(index=1)
        # address_1 = AttributeAddress(attribute_index_list=[ai_1])
        # address_2 = AttributeAddress(attribute_index_list=[ai_2])
        # command_1 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.insert),
        #                                               attrib_address=address_1,
        #                                               value="500")
        # command_2 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.insert),
        #                                               attrib_address=address_2,
        #                                               value="300")
        # command_3 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.remove),
        #                                               attrib_address=address_1)
        # command_4 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.set_complex),
        #                                               attrib_address=address_1,
        #                                               value=["100", "200"])
        # command_5 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.set_single),
        #                                               attrib_address=address_2,
        #                                               value="700")
        # obj_A = A()
        # obj_A.a = command_1
        # obj_A.a = command_2
        # print(obj_A.a)
        # obj_A.a = command_3
        # print(obj_A.a)
        # obj_A.a = command_4
        # print(obj_A.a)
        # obj_A.a = command_5
        # print(obj_A.a)

        # obj_B = B()
        # print(obj_B.b.single_attribute_list[0].obj)
        # print(obj_B.b.single_attribute_list[0].obj.a)
        # ai_3 = AttributeIndex(attr_name="a")
        # ai_4 = AttributeIndex()
        # address_3 = AttributeAddress(attribute_index_list=[ai_3, ai_4])
        # command_6 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.insert),
        #                                               attrib_address=address_3,
        #                                               value="500")
        # obj_B.b = command_6
        # print(obj_B.b.single_attribute_list[0].obj)
        # print(obj_B.b.single_attribute_list[0].obj.a)

    test_5 = True
    if test_5:
        ppo_rp = PpoPoint("My_point")  # PpoRoutePointer
        print(ppo_rp.class_)
        print(ppo_rp.tag)
        # print(ppo_rp.to_file_json())
        print(dir(PpoRoutePointer))
        print(list(reversed(PpoRoutePointer.__mro__[:-1])))
        print(ppo_rp.to_json_dict(is_base_object=True))
        # ppo_rp.to_attributes_json()
        print(ppo_rp.to_json_dict(False, is_base_object=True))
