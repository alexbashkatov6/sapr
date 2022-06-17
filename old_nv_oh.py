from __future__ import annotations

import os.path
from collections import OrderedDict
from typing import Type, Iterable, Optional, Any, Callable, Union
import json
from functools import partial
from copy import copy
from dataclasses import dataclass, field

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject

from custom_enum import CustomEnum

TPL_TO_OBJ_ID = OrderedDict([('PpoPoint', "Str"),
                             ('PpoTrainSignal', "SvP"),
                             ('PpoShuntingSignal', "SvM"),
                             ('PpoPointSection', "SPU"),
                             ('PpoTrackSection', "SPU"),
                             ('PpoTrackAnD', "Put"),
                             ('PpoAutomaticBlockingSystem', "AdjAB"),
                             ('PpoSemiAutomaticBlockingSystem', "AdjPAB"),
                             ('PpoLineEnd', "Tpk"),
                             ('PpoControlAreaBorder', "GRU")])

FILE_NAME_TO_CLASSES = OrderedDict([('TObjectsPoint', ["PpoPoint"]),
                                    ('TObjectsSignal', ["PpoRoutePointer",
                                                        "PpoTrainSignal",
                                                        "PpoShuntingSignal",
                                                        "PpoShuntingSignalWithTrackAnD",
                                                        "PpoWarningSignal",
                                                        "PpoRepeatSignal"]),
                                    ('TObjectsTrack', ["PpoTrackAnD",
                                                       "PpoTrackAnDwithPoint",
                                                       "PpoLineEnd",
                                                       "PpoPointSection",
                                                       "PpoTrackSection"]),
                                    ('IObjectsCodeGenerator', ["PpoCodeEnablingRelayALS"]),
                                    ('IObjectsEncodingPoint', ["PpoTrackEncodingPoint"]),
                                    ('IObjectsPoint', ["PpoPointMachineCi"]),
                                    ('IObjectsRelay', ["PpoGeneralPurposeRelayInput",
                                                       "PpoGeneralPurposeRelayOutput"]),
                                    ('IObjectsSignal', ["PpoRoutePointerRi",
                                                        "PpoLightSignalCi"]),
                                    ('IObjectsTrack', ["PpoTrackReceiverRi",
                                                       "PpoTrackUnit"]),
                                    ('Border', ["PpoControlAreaBorder",
                                                "PpoSemiAutomaticBlockingSystemRi",
                                                "PpoSemiAutomaticBlockingSystem",
                                                "PpoAutomaticBlockingSystemRi",
                                                "PpoAutomaticBlockingSystem"]),
                                    ('Equipment', ["PpoElectricHeating",
                                                   "PpoElectricHeatingRi"]),
                                    ('Operator', ["TrafficOperatorWorkset",
                                                  "StationOperatorWorkset",
                                                  "ControlArea"]),
                                    ('RailWarningArea', ["PpoRailCrossingRi",
                                                         "PpoTrainNotificationRi",
                                                         "PpoTrackCrossroad",
                                                         "PpoRailCrossing"]),
                                    ('Telesignalization', ["PpoCabinetUsoBk",
                                                           "PpoInsulationResistanceMonitoring",
                                                           "PpoPointMachinesCurrentMonitoring",
                                                           "PpoTelesignalization",
                                                           "PpoPointsMonitoring",
                                                           "PpoLightModeRi",
                                                           "PpoLightMode",
                                                           "PpoFireAndSecurityAlarm",
                                                           "PpoDieselGenerator"])])


class AttributeCommand(CustomEnum):
    set_single = 0
    set_complex = 1
    insert = 2
    remove = 3


@dataclass
class AttributeIndex:
    index: int = 0
    attr_name: str = ""


@dataclass
class AttributeAddress:
    attribute_index_list: list[AttributeIndex] = field(default_factory=list)


@dataclass
class ComplexAttributeManagementCommand:
    command: AttributeCommand
    attrib_address: AttributeAddress
    value: Any = None


@dataclass
class ComplexAttribute:
    is_list: bool = False
    is_required: bool = False
    min_count: int = 1
    single_attribute_type: Any = str
    single_attribute_list: list[SingleAttribute] = field(default_factory=list)


@dataclass
class SingleAttribute:
    index_in_complex: int = 0
    obj: Any = None
    last_input_value: str = ""
    accepted_value: Any = None
    is_suggested: bool = False
    error_message: str = ""


class NewDefaultDescriptor:

    def __init__(self, is_list: bool = False, is_required: bool = False, min_count: int = 0, single_attribute_type: Any = None):
        self.complex_attribute_template = ComplexAttribute(is_list=is_list, is_required=is_required,
                                                           min_count=min_count,
                                                           single_attribute_type=single_attribute_type)

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        if not hasattr(instance, "_{}".format(self.name)):
            self.init_attr_in_object(instance)
        return getattr(instance, "_{}".format(self.name))

    def __set__(self, instance, command: ComplexAttributeManagementCommand):
        if not hasattr(instance, "_{}".format(self.name)):
            self.init_attr_in_object(instance)
        complex_attr: ComplexAttribute = getattr(instance, "_{}".format(self.name))
        command_, attr_address, value = command.command, command.attrib_address, command.value
        if command_ == AttributeCommand.set_single:
            """ index is already exists """
            cycle_complex_attr, single_attrib = self.cyclic_find(complex_attr, attr_address, True)
            single_attrib.last_input_value = value
            return
        else:
            cycle_complex_attr, _ = self.cyclic_find(complex_attr, attr_address)
        if command_ == AttributeCommand.set_complex:
            cycle_complex_attr.single_attribute_list.clear()
            if isinstance(value, list):
                for val in value:
                    single_attr = SingleAttribute()
                    single_attr.last_input_value = val
                    cycle_complex_attr.single_attribute_list.append(single_attr)
            else:
                single_attr = SingleAttribute()
                single_attr.last_input_value = value
                cycle_complex_attr.single_attribute_list.append(single_attr)
            return
        index = attr_address.attribute_index_list[-1].index
        if command_ == AttributeCommand.insert:
            single_attr = SingleAttribute()
            single_attr.last_input_value = value
            if cycle_complex_attr.is_list:
                cycle_complex_attr.single_attribute_list.insert(index, single_attr)
            else:
                cycle_complex_attr.single_attribute_list.clear()
                cycle_complex_attr.single_attribute_list.insert(index, single_attr)
        elif command_ == AttributeCommand.remove:
            cycle_complex_attr.single_attribute_list.pop(index)
        else:
            assert False

    def init_attr_in_object(self, instance):
        init_value = ComplexAttribute(is_list=self.complex_attribute_template.is_list,
                                      is_required=self.complex_attribute_template.is_required,
                                      min_count=self.complex_attribute_template.min_count,
                                      single_attribute_type=self.complex_attribute_template.single_attribute_type)
        for _ in range(self.complex_attribute_template.min_count):
            single_attr = SingleAttribute()
            single_attr.obj = self.complex_attribute_template.single_attribute_type()
            init_value.single_attribute_list.append(single_attr)
        setattr(instance, "_{}".format(self.name), init_value)

    def cyclic_find(self, complex_attr: ComplexAttribute, attr_address: AttributeAddress, find_single_attribute: bool = False) -> \
            tuple[ComplexAttribute, Optional[SingleAttribute]]:
        cycle_complex_attr = complex_attr
        ail = attr_address.attribute_index_list
        for i, attr_index in enumerate(ail):
            index, attr_name = attr_index.index, attr_index.attr_name
            if (len(ail) - 1 == i) and not find_single_attribute:
                single_attrib = None
                break
            if cycle_complex_attr.is_list:
                single_attrib = cycle_complex_attr.single_attribute_list[index]
            else:
                single_attrib = cycle_complex_attr.single_attribute_list[0]
            if cycle_complex_attr.single_attribute_type is None:
                assert len(ail) - 1 == i
            else:
                cycle_complex_attr = getattr(single_attrib.obj, attr_name)
        return cycle_complex_attr, single_attrib


# --------------------------  DESCRIPTORS  ------------------------

def not_empty_extraction(obj: Any) -> Any:
    if isinstance(obj, str):
        if obj and not obj.isspace():
            return obj
    elif isinstance(obj, list):
        res = [elem for elem in obj if not_empty_extraction(elem)]
        if res:
            return res
    elif isinstance(obj, (dict, OrderedDict)):
        res = {key: val for key, val in obj.items() if not_empty_extraction(val)}
        if res:
            return res


class DefaultDescriptor:

    def __init__(self, default_value: Any = None, is_required: bool = True, is_list: bool = False, min_count: int = 1,
                 no_repeating_values: bool = True):
        self.name = None
        self.default_value = default_value
        self.is_required = is_required
        self.is_list = is_list
        self.min_count = min_count
        self.no_repeating_values = no_repeating_values

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        attr_contain_value_name = "_{}".format(self.name)
        if not hasattr(instance, attr_contain_value_name):
            if self.is_list:
                setattr(instance, "_{}".format(self.name), [""] * self.min_count)
                setattr(instance, "_str_{}".format(self.name), [""] * self.min_count)
                setattr(instance, "_check_status_{}".format(self.name), [""] * self.min_count)
            elif self.default_value:
                setattr(instance, "_{}".format(self.name), self.default_value)
                setattr(instance, "_str_{}".format(self.name), self.default_value)
                setattr(instance, "_check_status_{}".format(self.name), "")
            else:
                setattr(instance, "_{}".format(self.name), "")
                setattr(instance, "_str_{}".format(self.name), "")
                setattr(instance, "_check_status_{}".format(self.name), "")
        return getattr(instance, "_str_{}".format(self.name))

    def __set__(self, instance, input_value):
        setattr(instance, "_str_{}".format(self.name), input_value)
        setattr(instance, "_{}".format(self.name), input_value)


class ObjectListDescriptor(DefaultDescriptor):

    def __init__(self, obj_type: Type, is_required: bool = True, min_count: int = 1, no_repeating_values: bool = True):
        super().__init__(None, is_required, True, min_count, no_repeating_values)
        self.obj_type = obj_type

    def __get__(self, instance, owner):
        if not instance:
            return self
        attr_val = "_{}".format(self.name)
        if not hasattr(instance, attr_val):
            objs_list = []
            for i in range(self.min_count):
                obj = self.obj_type()
                objs_list.append(obj)
            setattr(instance, attr_val, objs_list)
        return getattr(instance, attr_val)

    def __set__(self, instance, input_value: list):
        setattr(instance, "_{}".format(self.name), input_value)


class StrBoundedValuesDescriptor(DefaultDescriptor):

    def __init__(self, default_value: Any = None, is_required: bool = True, is_list: bool = False, min_count: int = 1,
                 no_repeating_values: bool = True):
        super().__init__(default_value, is_required, is_list, min_count, no_repeating_values)
        self._possible_values = []

    def __set__(self, instance, input_value: Union[str, list[str]]):
        setattr(instance, "_str_{}".format(self.name), input_value)
        if not self.possible_values:
            setattr(instance, "_{}".format(self.name), input_value)
            if self.is_list:
                init_check_value = [""] * len(input_value)
            else:
                init_check_value = ""
            setattr(instance, "_check_status_{}".format(self.name), init_check_value)
        else:
            if not self.is_list:
                if (self.default_value and (input_value == self.default_value)) or (
                        input_value in self.possible_values):
                    setattr(instance, "_{}".format(self.name), input_value)
                    setattr(instance, "_check_status_{}".format(self.name), "")
                else:
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Value {} not in list of possible values: {}".format(input_value, self.possible_values))
            else:
                old_destination_list = getattr(instance, "_{}".format(self.name))
                destination_list = []
                check_list = []
                for i, value in enumerate(input_value):
                    destination_list.append("")
                    check_list.append("")
                    if (self.default_value and (value == self.default_value)) or (value in self.possible_values):
                        destination_list[-1] = value
                        check_list[-1] = ""
                    else:
                        check_list[-1] = "Value {} not in list of possible values: {}".format(value,
                                                                                              self.possible_values)
                        if i < len(old_destination_list):
                            destination_list[i] = old_destination_list[i]
                setattr(instance, "_{}".format(self.name), destination_list)
                setattr(instance, "_check_status_{}".format(self.name), check_list)

    @property
    def possible_values(self) -> list[str]:
        result = list(self._possible_values)
        if self.default_value:
            result.append(self.default_value)
        return result

    @possible_values.setter
    def possible_values(self, values: Iterable[str]):
        self._possible_values = values


class ClassNameDescriptor:
    def __get__(self, instance, owner):
        return owner.__name__

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class TagDescriptor:
    def __init__(self):
        self.tags = set()

    def __get__(self, instance, owner):
        if not instance:
            return self
        return getattr(instance, "_tag")

    def __set__(self, instance, value: str):
        instance._tag = value
        self.tags.add(instance._tag)


class AllAttributesOdDescriptor:
    def __init__(self):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return [key for key in owner.__dict__.keys() if not key.startswith("__")]

        result = OrderedDict()
        for attr_name in getattr(owner, self.name):
            result[attr_name] = getattr(instance, attr_name)
        return result


class AllNotEmptyAttributesDescriptor:
    def __init__(self):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return [key for key in owner.__dict__.keys() if not key.startswith("__")]

        result = OrderedDict()
        for attr_name in getattr(owner, self.name):
            attr_val = getattr(instance, attr_name)
            extr = not_empty_extraction(attr_val)
            if extr:
                result[attr_name] = extr
        # print("result = ", result)
        return result


class DataDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return [key for key in owner.__dict__.keys() if not key.startswith("__")]

        data_odict = OrderedDict()
        for attr_name in owner.data:
            if attr_name == "id_":
                data_odict["id"] = getattr(instance, attr_name)
            else:
                descr = getattr(owner, attr_name)
                if isinstance(descr, ObjectListDescriptor):
                    obj_list = getattr(instance, attr_name)
                    result = []
                    for obj in obj_list:
                        all_attrs = obj.all_attributes
                        result.append(all_attrs)
                    data_odict[attr_name] = result
                else:
                    data_odict[attr_name] = getattr(instance, attr_name)
        return data_odict

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class DataNotEmptyDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return [key for key in owner.__dict__.keys() if not key.startswith("__")]

        data_odict = OrderedDict()
        for attr_name in owner.data:
            if attr_name == "id_":
                data_odict["id"] = getattr(instance, attr_name)
            else:
                descr = getattr(owner, attr_name)
                if isinstance(descr, ObjectListDescriptor):
                    obj_list = getattr(instance, attr_name)
                    result = []
                    for obj in obj_list:
                        all_attrs = not_empty_extraction(obj.all_not_empty_attributes)
                        if all_attrs:
                            result.append(all_attrs)
                    if result:
                        data_odict[attr_name] = result
                else:
                    candid_value = getattr(instance, attr_name)
                    extr = not_empty_extraction(candid_value)
                    if extr:
                        data_odict[attr_name] = extr
        return data_odict

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class DefaultToJsonDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        instance: PpoObject

        odict = OrderedDict()
        odict["class"] = instance.class_
        odict["tag"] = instance.tag
        odict["data"] = instance.data

        return odict

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class ToNotEmptyJsonDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        instance: PpoObject

        odict = OrderedDict()
        odict["class"] = instance.class_
        odict["tag"] = instance.tag
        odict["data"] = instance.data_not_empty

        return odict

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class EqualTagDescriptor(DefaultDescriptor):

    def __get__(self, instance, owner):
        if not instance:
            return self
        attr_val = "_{}".format(self.name)
        if not hasattr(instance, attr_val):
            setattr(instance, "_{}".format(self.name), instance.tag)
            setattr(instance, "_str_{}".format(self.name), instance.tag)
            setattr(instance, "_check_status_{}".format(self.name), "")
        return getattr(instance, "_str_{}".format(self.name))


class IdDescriptor(EqualTagDescriptor):
    pass


class IndentDescriptor(EqualTagDescriptor):
    pass


class IdControlAreaDescriptor(StrBoundedValuesDescriptor):
    pass


class IObjTagSimpleDescriptor(EqualTagDescriptor):
    pass


class RoutePointersDescriptor(StrBoundedValuesDescriptor):
    pass


class UkspsDescriptor(StrBoundedValuesDescriptor):
    pass


class PositiveIntDescriptor(DefaultDescriptor):

    def __set__(self, instance, value: str):
        setattr(instance, "_str_{}".format(self.name), value)
        if not value.isdigit():
            setattr(instance, "_check_status_{}".format(self.name), "Input value {} is not a number".format(value))
        else:
            setattr(instance, "_{}".format(self.name), value)
            setattr(instance, "_check_status_{}".format(self.name), "")


class ZeroOneDescriptor(DefaultDescriptor):

    def __set__(self, instance, value: str):
        setattr(instance, "_str_{}".format(self.name), value)
        if value not in ["0", "1"]:
            setattr(instance, "_check_status_{}".format(self.name), "Input value {} is not in [0, 1]".format(value))
        else:
            setattr(instance, "_{}".format(self.name), value)
            setattr(instance, "_check_status_{}".format(self.name), "")


class LengthDescriptor(PositiveIntDescriptor):
    pass


class TrackUnitDescriptor(StrBoundedValuesDescriptor):
    pass


class PointsMonitoringDescriptor(DefaultDescriptor):

    def __get__(self, instance, owner):
        if not instance:
            return self
        attr_val = "_{}".format(self.name)
        if not hasattr(instance, attr_val):
            setattr(instance, "_{}".format(self.name), "STRELKI")
            setattr(instance, "_str_{}".format(self.name), "STRELKI")
            setattr(instance, "_check_status_{}".format(self.name), "")
        return getattr(instance, "_str_{}".format(self.name))


class SectionDescriptor(StrBoundedValuesDescriptor):
    pass


class RailFittersWarningAreaDescriptor(EqualTagDescriptor):
    pass


class AutoReturnDescriptor(StrBoundedValuesDescriptor):
    pass


class PointDescriptor(StrBoundedValuesDescriptor):
    pass


class LockingDescriptor(StrBoundedValuesDescriptor):
    pass


class PlusMinusDescriptor(StrBoundedValuesDescriptor):
    pass


class IsInvitationSignalOpeningBeforeDescriptor(StrBoundedValuesDescriptor):
    pass


class SingleTrackDescriptor(StrBoundedValuesDescriptor):
    pass


class RailCrossingDescriptor(StrBoundedValuesDescriptor):
    pass


class AddrKiDescriptor(StrBoundedValuesDescriptor):
    def __init__(self, default_value: Any = None, is_required: bool = True, is_list: bool = False, min_count: int = 1,
                 no_repeating_values: bool = True):
        default_value = "USO:::"
        super().__init__(default_value, is_required, is_list, min_count, no_repeating_values)
        self.possible_values = ["USO", "CPU", "PPO", "Fixed_1", "Fixed_0"]

    def __set__(self, instance, value: str):
        super().__set__(instance, value)
        value = value.strip()
        if value.startswith("USO") or value.startswith("CPU") or value.startswith("PPO"):
            between_column = value.split(":")
            if len(between_column) == 2:
                if between_column[0] != "PPO":
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Address not valid begin: {}".format(value))
                    return
                if between_column[1] not in ["MAX_UINT", "0"]:
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Address not valid end: {}".format(value))
                    return
                setattr(instance, "_check_status_{}".format(self.name), "")
                setattr(instance, "_{}".format(self.name), value)
                return
            if len(between_column) < 4:
                setattr(instance, "_check_status_{}".format(self.name),
                        "Count of colon <3 in value: {}".format(value))
                return
            if between_column[0] not in ["USO", "CPU", "PPO"]:
                setattr(instance, "_check_status_{}".format(self.name),
                        "Address not valid begin: {}".format(value))
                return
            for addr_int in between_column[1:]:
                if not addr_int.isdigit():
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Address not valid because not digits: {}".format(value))
                    return
            setattr(instance, "_check_status_{}".format(self.name), "")
            setattr(instance, "_{}".format(self.name), value)


class AddrUiDescriptor(StrBoundedValuesDescriptor):
    def __init__(self, default_value: Any = None, is_required: bool = True, is_list: bool = False, min_count: int = 1,
                 no_repeating_values: bool = True):
        default_value = "USO:::"
        super().__init__(default_value, is_required, is_list, min_count, no_repeating_values)
        self.possible_values = ["USO", "CPU", "PPO", "addrKI_1U", "NoAddr"]

    def __set__(self, instance, value: str):
        super().__set__(instance, value)
        value = value.strip()
        if value.startswith("USO") or value.startswith("CPU") or value.startswith("PPO"):
            between_column = value.split(":")
            if len(between_column) < 4:
                setattr(instance, "_check_status_{}".format(self.name),
                        "Count of colon < 3 in value: {}".format(value))
                return
            if between_column[0] not in ["USO", "CPU", "PPO"]:
                setattr(instance, "_check_status_{}".format(self.name),
                        "Address not valid begin: {}".format(value))
                return
            for addr_int in between_column[1:]:
                if not addr_int.isdigit():
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Address not valid because not digits: {}".format(value))
                    return
            setattr(instance, "_check_status_{}".format(self.name), "")
            setattr(instance, "_{}".format(self.name), value)


class InterstationDirectiveDescriptor(StrBoundedValuesDescriptor):
    def __init__(self, default_value: Any = None, is_required: bool = True, is_list: bool = False, min_count: int = 1,
                 no_repeating_values: bool = True):
        super().__init__(default_value, is_required, is_list, min_count, no_repeating_values)
        self.possible_values = ["NoAddr"]

    def __get__(self, instance, owner):
        if not instance:
            return self
        self.default_value = "{}_{}".format(self.name.split("_")[1], instance.tag.replace("_Ri", ""))
        return super().__get__(instance, owner)


class HeatingDirectiveDescriptor(StrBoundedValuesDescriptor):
    pass


class CrossroadDescriptor(StrBoundedValuesDescriptor):
    pass


class IObjTagTrackCrossroadDescriptor(StrBoundedValuesDescriptor):
    pass


class ModeLightSignalDescriptor(DefaultDescriptor):

    def __get__(self, instance, owner):
        if not instance:
            return self
        attr_val = "_{}".format(self.name)
        if not hasattr(instance, attr_val):
            setattr(instance, "_{}".format(self.name), "DN_DSN")
            setattr(instance, "_str_{}".format(self.name), "DN_DSN")
            setattr(instance, "_check_status_{}".format(self.name), "")
        return getattr(instance, "_str_{}".format(self.name))


class AddrCiDescriptor(AddrKiDescriptor):

    def __set__(self, instance, value: str):
        if value.isdigit():
            setattr(instance, "_check_status_{}".format(self.name), "")
            setattr(instance, "_{}".format(self.name), value)
        super().__set__(instance, value)


class TypeLightSignalDescriptor(PositiveIntDescriptor):
    pass


class EnterSignalDescriptor(StrBoundedValuesDescriptor):
    pass


class IObjTagTrackUnitDescriptor(StrBoundedValuesDescriptor):
    pass


class SignalTagDescriptor(StrBoundedValuesDescriptor):
    pass


class EncodingPointDescriptor(StrBoundedValuesDescriptor):
    pass


class DirectionPointAndTrackDescriptor(StrBoundedValuesDescriptor):
    pass


class OppositeTrackAnDwithPointDescriptor(StrBoundedValuesDescriptor):
    pass


class AdjEnterSigDescriptor(StrBoundedValuesDescriptor):
    pass


class OkvDescriptor(StrBoundedValuesDescriptor):
    pass


class EncUnitDescriptor(StrBoundedValuesDescriptor):
    pass


# --------------------------  OBJECT CLASSES  ------------------------


class PpoObject:
    class_ = ClassNameDescriptor()
    tag = TagDescriptor()
    data = DataDescriptor()
    data_not_empty = DataNotEmptyDescriptor()
    to_json = DefaultToJsonDescriptor()
    to_json_not_empty = ToNotEmptyJsonDescriptor()
    all_attributes = AllAttributesOdDescriptor()
    all_not_empty_attributes = AllNotEmptyAttributesDescriptor()


class PpoRoutePointer(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    routePointer = RoutePointersDescriptor()


class PpoRoutePointerRi(PpoObject):
    onRoutePointer = AddrUiDescriptor()
    outputAddrs = AddrUiDescriptor()


class PpoTrainSignal(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    routePointer = RoutePointersDescriptor()
    groupRoutePointers = RoutePointersDescriptor(is_list=True)
    uksps = UkspsDescriptor()


class PpoWarningSignal(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    signalTag = SignalTagDescriptor()


class PpoRepeatSignal(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    signalTag = SignalTagDescriptor()


class PpoShuntingSignal(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoShuntingSignalWithTrackAnD(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoLightSignalCi(PpoObject):
    mode = ModeLightSignalDescriptor()
    addrKa = AddrCiDescriptor()
    addrKi = AddrCiDescriptor()
    addrUi = AddrCiDescriptor()
    type_ = TypeLightSignalDescriptor()


class PpoAnDtrack(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor(default_value="5")
    trackUnit = TrackUnitDescriptor()


class PpoTrackAnDwithPoint(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor(default_value="5")
    trackUnit = TrackUnitDescriptor()
    directionPointAnDTrack = DirectionPointAndTrackDescriptor()
    oppositeTrackAnDwithPoint = OppositeTrackAnDwithPointDescriptor()


class PpoLineEnd(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor(default_value="5")
    trackUnit = TrackUnitDescriptor(default_value="nullptr")


class PpoPointSection(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor(default_value="5")
    trackUnit = TrackUnitDescriptor()


class PpoTrackSection(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor(default_value="5")
    trackUnit = TrackUnitDescriptor()


class AdditionalSwitch(PpoObject):
    point = PointDescriptor()
    selfPosition = PlusMinusDescriptor()
    dependencePosition = PlusMinusDescriptor()


class SectionAndIgnoreCondition(PpoObject):
    section = SectionDescriptor()
    point = PointDescriptor()
    position = PlusMinusDescriptor()


class NotificationPoint(PpoObject):
    point = AddrKiDescriptor()
    delay = AddrKiDescriptor()


class PpoPoint(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    pointsMonitoring = PointsMonitoringDescriptor()
    section = SectionDescriptor()
    railFittersWarningArea = RailFittersWarningAreaDescriptor()
    autoReturn = AutoReturnDescriptor()
    guardPlusPlus = PointDescriptor(is_list=True)
    guardPlusMinus = PointDescriptor(is_list=True)
    guardMinusPlus = PointDescriptor(is_list=True)
    guardMinusMinus = PointDescriptor(is_list=True)
    lockingPlus = LockingDescriptor(is_list=True)
    lockingMinus = LockingDescriptor(is_list=True)
    additionalSwitch = ObjectListDescriptor(obj_type=AdditionalSwitch)
    pairPoint = PointDescriptor()
    oversizedPlus = ObjectListDescriptor(obj_type=SectionAndIgnoreCondition)
    oversizedMinus = ObjectListDescriptor(obj_type=SectionAndIgnoreCondition)
    additionalGuardLock = ObjectListDescriptor(obj_type=SectionAndIgnoreCondition)


class PpoPointMachineCi(PpoObject):
    addrKi = PositiveIntDescriptor()
    addrUi = PositiveIntDescriptor()


class PpoControlAreaBorder(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()


class PpoSemiAutomaticBlockingSystem(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    isInvitationSignalOpeningBefore = IsInvitationSignalOpeningBeforeDescriptor()


class PpoSemiAutomaticBlockingSystemRi(PpoObject):
    addrKI_SNP = AddrKiDescriptor()
    addrKI_S1U = AddrKiDescriptor()
    addrKI_1U = AddrKiDescriptor()
    addrKI_FP = AddrKiDescriptor()
    addrKI_POS = AddrKiDescriptor()
    addrKI_PS = AddrKiDescriptor()
    addrKI_OP = AddrKiDescriptor()
    addrKI_DSO = AddrKiDescriptor()
    addrKI_KZH = AddrKiDescriptor()

    addrUI_KS = AddrUiDescriptor()

    output_DSO = InterstationDirectiveDescriptor()
    output_OSO = InterstationDirectiveDescriptor()
    output_FDP = InterstationDirectiveDescriptor()
    output_IFP = InterstationDirectiveDescriptor()

    notificationPoints = ObjectListDescriptor(obj_type=NotificationPoint)


class PpoAutomaticBlockingSystem(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    isInvitationSignalOpeningBefore = IsInvitationSignalOpeningBeforeDescriptor()
    singleTrack = SingleTrackDescriptor()


class PpoAutomaticBlockingSystemRi(PpoObject):
    addrKI_SNP = AddrKiDescriptor()
    addrKI_SN = AddrKiDescriptor()
    addrKI_S1U = AddrKiDescriptor()
    addrKI_S1P = AddrKiDescriptor()
    addrKI_1U = AddrKiDescriptor()
    addrKI_1P = AddrKiDescriptor()
    addrKI_2U = AddrKiDescriptor()
    addrKI_3U = AddrKiDescriptor()
    addrKI_ZU = AddrKiDescriptor()
    addrKI_KP = AddrKiDescriptor()
    addrKI_KZH = AddrKiDescriptor()
    addrKI_UUB = AddrKiDescriptor()
    addrKI_PB = AddrKiDescriptor()
    addrKI_KV = AddrKiDescriptor()
    addrKI_A = AddrKiDescriptor()

    addrUI_KS = AddrUiDescriptor()
    addrUI_I = AddrUiDescriptor()
    addrUI_KZH = AddrUiDescriptor()
    addrUI_VIP1 = AddrUiDescriptor()
    addrUI_VIP2 = AddrUiDescriptor()
    addrUI_VIP3 = AddrUiDescriptor()
    addrUI_OKV = AddrUiDescriptor()
    addrUI_KM = AddrUiDescriptor()

    output_SNK = InterstationDirectiveDescriptor()
    output_DS = InterstationDirectiveDescriptor()
    output_OV = InterstationDirectiveDescriptor()
    output_PV = InterstationDirectiveDescriptor()
    output_RUU = InterstationDirectiveDescriptor()
    output_R = InterstationDirectiveDescriptor()

    adjEnterSig = AdjEnterSigDescriptor()

    notificationPoints = ObjectListDescriptor(obj_type=NotificationPoint)


class PpoTrackCrossroad(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagTrackCrossroadDescriptor()
    railCrossing = RailCrossingDescriptor()


class PpoTrainNotificationRi(PpoObject):
    NPI = AddrUiDescriptor()
    CHPI = AddrUiDescriptor()


class PpoRailCrossingRi(PpoObject):
    NCHPI = AddrKiDescriptor()
    KP_O = AddrKiDescriptor()
    KP_A = AddrKiDescriptor()
    ZG = AddrKiDescriptor()
    KZP = AddrKiDescriptor()


class PpoRailCrossing(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()
    crossroad = CrossroadDescriptor(is_list=True)


class PpoControlDeviceDerailmentStock(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoControlDeviceDerailmentStockCi(PpoObject):
    addrKI_1KSO = AddrCiDescriptor()
    addrKI_1KSR = AddrCiDescriptor()
    addrKI_2KSO = AddrCiDescriptor()
    addrKI_2KSR = AddrCiDescriptor()

    addrKI_KSV = AddrKiDescriptor()
    addrKI_SNP = AddrKiDescriptor()
    addrKI_1UP = AddrKiDescriptor()
    addrKI_2UP = AddrKiDescriptor()
    addrKI_1UU = AddrKiDescriptor()
    addrKI_2UU = AddrKiDescriptor()

    addrUI_1KSD = AddrUiDescriptor()
    addrUI_2KSB = AddrUiDescriptor()
    addrUI_KSVA = AddrUiDescriptor()

    enterSignal = EnterSignalDescriptor()


class PpoTrackUnit(PpoObject):
    iObjsTag = IObjTagTrackUnitDescriptor()
    evenTag = EncodingPointDescriptor()
    oddTag = EncodingPointDescriptor()


class PpoTrackReceiverRi(PpoObject):
    addrKI_P = AddrKiDescriptor()


class PpoLightSignalRi(PpoObject):
    addrKI_KO = AddrKiDescriptor()
    addrKI_KPS = AddrKiDescriptor()
    addrKI_RU = AddrKiDescriptor()
    addrKI_GM = AddrKiDescriptor()
    addrKI_KMGS = AddrKiDescriptor()
    addrKI_ZHZS = AddrKiDescriptor()
    addrKI_ZS = AddrKiDescriptor()


class PpoCodeEnablingRelayALS(PpoObject):
    addr = AddrKiDescriptor()
    okv = OkvDescriptor()


class PpoTrackEncodingPoint(PpoObject):
    encUnitALS = EncUnitDescriptor()
    own = IObjTagTrackUnitDescriptor(is_list=True)
    freeState = IObjTagTrackUnitDescriptor(is_list=True)
    plusPoints = PointDescriptor(is_list=True)
    minusPoints = PointDescriptor(is_list=True)


class PpoGeneralPurposeRelayInput(PpoObject):
    inputAddr = AddrKiDescriptor(is_list=True)


class PpoGeneralPurposeRelayOutput(PpoObject):
    addrUI = AddrUiDescriptor()
    defaultValue = ZeroOneDescriptor()


class PpoElectricHeating(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoElectricHeatingRi(PpoObject):
    addrKI_KEO = AddrKiDescriptor()
    addrKI_KI = AddrKiDescriptor()
    output_VO = HeatingDirectiveDescriptor()
    output_OO = HeatingDirectiveDescriptor()


class TrafficOperatorWorkset(PpoObject):
    num = 1
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    controlArea = IdControlAreaDescriptor(is_list=True)
    commonRemoteCommands = 2
    confirmedRemoteCommands = 3
    key = 3


class StationOperatorWorkset(PpoObject):
    num = 1
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    controlArea = IdControlAreaDescriptor(is_list=True)


class ControlArea(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    initialOperatorNum = 1


class PpoCabinetUsoBk(PpoObject):
    lightSignals = SignalTagDescriptor(is_list=True)
    hiCratePointMachines = PointDescriptor(is_list=True)
    loCratePointMachines = PointDescriptor(is_list=True)
    controlDeviceDerailmentStocks = 1


class PpoInsulationResistanceMonitoring(PpoObject):
    cabinets = 1
    addrKI_OK = AddrKiDescriptor()


class PpoPointMachinesCurrentMonitoring(PpoObject):
    cabinets = 1
    addrKI_KTPS = AddrKiDescriptor()


class PpoTelesignalization(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoPointsMonitoring(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()


class PpoLightModeRi(PpoObject):
    addrKI_DN1 = AddrKiDescriptor()
    addrKI_DN2 = AddrKiDescriptor()
    addrKI_DSN = AddrKiDescriptor()
    addrUI_DN = AddrUiDescriptor()
    addrUI_DSN = AddrUiDescriptor()
    addrUI_ASV = AddrUiDescriptor()


class PpoLightMode(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoFireAndSecurityAlarm(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    iObjTag = IObjTagSimpleDescriptor()


class PpoDieselGenerator(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    dieselControl = 1
    startDieselGenerator = 2
    stopDieselGenerator = 3


# --------------------------  HANDLER  ------------------------

RELATED_INTERFACE_CLASSES = {"PpoTrainSignal": "PpoLightSignal",
                             "PpoShuntingSignal": "PpoLightSignal",
                             "PpoRoutePointer": "PpoRoutePointer",
                             "PpoAutomaticBlockingSystem": "PpoAutomaticBlockingSystem",
                             "PpoSemiAutomaticBlockingSystem": "PpoSemiAutomaticBlockingSystem"}


class TagRepeatingError(Exception):
    pass


# class NotPossibleValueError(Exception):
#     pass


def check_not_repeating_names(odict):
    names = []
    for cls_name in odict:
        for obj_name in odict[cls_name]:
            if obj_name in names:
                raise TagRepeatingError("Tag {} repeats".format(obj_name))
            names.append(obj_name)


class ObjectsHandler(QObject):
    send_objects_tree = pyqtSignal(OrderedDict)
    send_attrib_list = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.bool_tpl_got = False
        self.bool_obj_id_got = False
        self.tpl_dict: OrderedDict[str, list[str]] = OrderedDict()  # input structure from tpl
        self.obj_id_dict: OrderedDict[str, list[str]] = OrderedDict()

        self.objects_tree: OrderedDict[str, OrderedDict[str, PpoObject]] = OrderedDict()  # output structure

        self.current_object: Optional[PpoObject] = None

        self.init_classes()
        self.bind_descriptors()

        self.auto_add_io: bool = True
        self.signal_itype: str = "Ci"
        self.point_itype: str = "Ci"
        self.derail_itype: str = "Ci"

        self.tech_to_interf_dict: dict[PpoObject, PpoObject] = {}
        self.interf_to_tech_dict: dict[PpoObject, PpoObject] = {}

    def auto_add_interface_objects(self, ch: bool):
        self.auto_add_io = ch

    def signal_interface_type(self, itype: str):
        self.signal_itype = itype

    def point_interface_type(self, itype: str):
        self.point_itype = itype

    def derail_interface_type(self, itype: str):
        self.derail_itype = itype

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

    def init_object(self, cls_name, obj_name):
        if cls_name == "PpoTrackAnD":
            cls_ = PpoAnDtrack
            obj = cls_()
            obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = obj

        elif cls_name in ["PpoTrainSignal", "PpoShuntingSignal"]:
            tpo_cls_ = eval(cls_name)
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            if self.auto_add_io:
                if self.signal_itype == "Ci":
                    inter_cls_ = PpoLightSignalCi
                    inter_obj = inter_cls_()
                    inter_obj.tag = obj_name + "_Ci"
                    self.objects_tree["PpoLightSignalCi"][inter_obj.tag] = inter_obj
                    self.tech_to_interf_dict[tpo_obj] = inter_obj
                elif self.signal_itype == "Ri":
                    inter_cls_ = PpoLightSignalRi
                    inter_obj = inter_cls_()
                    inter_obj.tag = obj_name + "_Ri"
                    self.objects_tree["PpoLightSignalRi"][inter_obj.tag] = inter_obj
                    self.tech_to_interf_dict[tpo_obj] = inter_obj
                else:
                    assert False

        elif cls_name == "PpoRoutePointer":
            tpo_cls_ = PpoRoutePointer
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            if self.auto_add_io:
                inter_cls_ = PpoRoutePointerRi
                inter_obj = inter_cls_()
                inter_obj.tag = obj_name + "_Ri"
                self.objects_tree["PpoRoutePointerRi"][inter_obj.tag] = inter_obj
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoPoint":
            tpo_cls_ = PpoPoint
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            if self.auto_add_io:
                inter_cls_ = PpoPointMachineCi
                inter_obj = inter_cls_()
                inter_obj.tag = obj_name + "_Ci"
                self.objects_tree["PpoPointMachineCi"][inter_obj.tag] = inter_obj
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoAutomaticBlockingSystem":
            tpo_cls_ = PpoAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            if self.auto_add_io:
                inter_cls_ = PpoAutomaticBlockingSystemRi
                inter_obj = inter_cls_()
                inter_obj.tag = obj_name + "_Ri"
                self.objects_tree["PpoAutomaticBlockingSystemRi"][inter_obj.tag] = inter_obj
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoSemiAutomaticBlockingSystem":
            tpo_cls_ = PpoSemiAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            if self.auto_add_io:
                inter_cls_ = PpoSemiAutomaticBlockingSystemRi
                inter_obj = inter_cls_()
                inter_obj.tag = obj_name + "_Ri"
                self.objects_tree["PpoSemiAutomaticBlockingSystemRi"][inter_obj.tag] = inter_obj
                self.tech_to_interf_dict[tpo_obj] = inter_obj

        elif cls_name == "PpoTrackCrossroad":
            first_symbols = obj_name[:2]
            if first_symbols not in self.name_to_obj_dict:
                crossing_cls_ = PpoRailCrossing
                crossing_obj = crossing_cls_()
                crossing_obj.tag = first_symbols
                self.objects_tree["PpoRailCrossing"][crossing_obj.tag] = crossing_obj

                if self.auto_add_io:
                    ri_crossing_cls_ = PpoRailCrossingRi
                    ri_crossing_obj = ri_crossing_cls_()
                    ri_crossing_obj.tag = first_symbols + "_Ri"
                    self.objects_tree["PpoRailCrossingRi"][ri_crossing_obj.tag] = ri_crossing_obj
                    self.tech_to_interf_dict[crossing_obj] = ri_crossing_obj

            cls_ = PpoTrackCrossroad
            obj = cls_()
            obj.tag = obj_name
            self.objects_tree["PpoTrackCrossroad"][obj_name] = obj
        else:
            cls_: Type[PpoObject] = eval(cls_name)
            obj = cls_()
            obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = obj

    def init_classes(self):
        self.objects_tree = OrderedDict()

        i = 0
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      INTERFACE OBJECTS"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()

        self.objects_tree["PpoLightSignalCi"] = OrderedDict()
        self.objects_tree["PpoLightSignalRi"] = OrderedDict()

        self.objects_tree["PpoRoutePointerRi"] = OrderedDict()

        self.objects_tree["PpoPointMachineCi"] = OrderedDict()

        self.objects_tree["PpoAutomaticBlockingSystemRi"] = OrderedDict()
        self.objects_tree["PpoSemiAutomaticBlockingSystemRi"] = OrderedDict()

        self.objects_tree["PpoRailCrossingRi"] = OrderedDict()
        self.objects_tree["PpoTrainNotificationRi"] = OrderedDict()

        self.objects_tree["PpoControlDeviceDerailmentStockCi"] = OrderedDict()

        self.objects_tree["PpoTrackReceiverRi"] = OrderedDict()

        self.objects_tree["PpoCodeEnablingRelayALS"] = OrderedDict()
        self.objects_tree["PpoTrackEncodingPoint"] = OrderedDict()

        self.objects_tree["PpoGeneralPurposeRelayInput"] = OrderedDict()
        self.objects_tree["PpoGeneralPurposeRelayOutput"] = OrderedDict()

        self.objects_tree["PpoElectricHeatingRi"] = OrderedDict()

        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      TECHNOLOGY OBJECTS"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()

        self.objects_tree["PpoControlAreaBorder"] = OrderedDict()

        self.objects_tree["PpoTrainSignal"] = OrderedDict()
        self.objects_tree["PpoWarningSignal"] = OrderedDict()
        self.objects_tree["PpoRepeatSignal"] = OrderedDict()
        self.objects_tree["PpoShuntingSignal"] = OrderedDict()

        self.objects_tree["PpoRoutePointer"] = OrderedDict()

        self.objects_tree["PpoPointSection"] = OrderedDict()
        self.objects_tree["PpoTrackSection"] = OrderedDict()
        self.objects_tree["PpoTrackAnD"] = OrderedDict()
        self.objects_tree["PpoLineEnd"] = OrderedDict()

        self.objects_tree["PpoPoint"] = OrderedDict()

        self.objects_tree["PpoAutomaticBlockingSystem"] = OrderedDict()
        self.objects_tree["PpoSemiAutomaticBlockingSystem"] = OrderedDict()

        self.objects_tree["PpoTrackCrossroad"] = OrderedDict()
        self.objects_tree["PpoRailCrossing"] = OrderedDict()

        self.objects_tree["PpoControlDeviceDerailmentStock"] = OrderedDict()

        self.objects_tree["PpoTrackUnit"] = OrderedDict()
        self.objects_tree["PpoTrackEncodingPoint"] = OrderedDict()

        self.objects_tree["PpoElectricHeating"] = OrderedDict()

        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      ADJACENT POINT CLASSES"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["PpoShuntingSignalWithTrackAnD"] = OrderedDict()
        self.objects_tree["PpoTrackAnDwithPoint"] = OrderedDict()

        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      ROUTE CLASSES"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["PpoTrainRoute"] = OrderedDict()
        self.objects_tree["PpoShuntingRoute"] = OrderedDict()

        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      OPERATOR CLASSES"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["TrafficOperatorWorkset"] = OrderedDict()
        self.objects_tree["StationOperatorWorkset"] = OrderedDict()
        self.objects_tree["ControlArea"] = OrderedDict()

        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["      TS CLASSES"] = OrderedDict()
        i += 1
        self.objects_tree[" " * i] = OrderedDict()
        self.objects_tree["PpoCabinetUsoBk"] = OrderedDict()
        self.objects_tree["PpoInsulationResistanceMonitoring"] = OrderedDict()
        self.objects_tree["PpoPointMachinesCurrentMonitoring"] = OrderedDict()
        self.objects_tree["PpoTelesignalization"] = OrderedDict()
        self.objects_tree["PpoPointsMonitoring"] = OrderedDict()
        self.objects_tree["PpoLightModeRi"] = OrderedDict()
        self.objects_tree["PpoLightMode"] = OrderedDict()
        self.objects_tree["PpoFireAndSecurityAlarm"] = OrderedDict()
        self.objects_tree["PpoDieselGenerator"] = OrderedDict()

    def bind_descriptors(self):
        PpoRoutePointer.routePointer.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()

        PpoTrainSignal.routePointer.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()
        PpoTrainSignal.groupRoutePointers.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()
        PpoTrainSignal.uksps.possible_values = self.objects_tree["PpoControlDeviceDerailmentStock"].keys()

        PpoRepeatSignal.signalTag.possible_values = self.objects_tree["PpoTrainSignal"].keys()
        PpoWarningSignal.signalTag.possible_values = self.objects_tree["PpoTrainSignal"].keys()

        for cls in [PpoAnDtrack, PpoTrackAnDwithPoint, PpoLineEnd, PpoPointSection, PpoTrackSection]:
            cls.trackUnit.possible_values = self.objects_tree["PpoTrackUnit"].keys()

        PpoPoint.section.possible_values = self.objects_tree["PpoPointSection"].keys()
        PpoPoint.autoReturn.possible_values = ["60", "180"]
        PpoPoint.guardPlusPlus.possible_values = self.objects_tree["PpoPoint"].keys()
        PpoPoint.guardPlusMinus.possible_values = self.objects_tree["PpoPoint"].keys()
        PpoPoint.guardMinusPlus.possible_values = self.objects_tree["PpoPoint"].keys()
        PpoPoint.guardMinusMinus.possible_values = self.objects_tree["PpoPoint"].keys()
        PpoPoint.lockingPlus.possible_values = self.objects_tree["PpoPointSection"].keys()
        PpoPoint.lockingMinus.possible_values = self.objects_tree["PpoPointSection"].keys()
        AdditionalSwitch.point.possible_values = self.objects_tree["PpoPoint"].keys()
        AdditionalSwitch.selfPosition.possible_values = ["+", "-"]
        AdditionalSwitch.dependencePosition.possible_values = ["+", "-"]
        PpoPoint.pairPoint.possible_values = self.objects_tree["PpoPoint"].keys()
        SectionAndIgnoreCondition.section.possible_values = self.objects_tree["PpoPointSection"].keys()
        SectionAndIgnoreCondition.point.possible_values = self.objects_tree["PpoPoint"].keys()
        SectionAndIgnoreCondition.position.possible_values = ["+", "-"]

        PpoSemiAutomaticBlockingSystem.isInvitationSignalOpeningBefore.possible_values = ["false"]
        PpoAutomaticBlockingSystem.isInvitationSignalOpeningBefore.possible_values = ["true", "false"]
        PpoAutomaticBlockingSystem.singleTrack.possible_values = ["Yes", "No"]
        PpoAutomaticBlockingSystemRi.adjEnterSig.possible_values = self.objects_tree["PpoLightSignalRi"].keys()

        PpoTrackCrossroad.railCrossing.possible_values = self.objects_tree["PpoRailCrossingRi"].keys()
        PpoTrackCrossroad.iObjTag.possible_values = self.objects_tree["PpoTrainNotificationRi"].keys()

        PpoControlDeviceDerailmentStockCi.enterSignal.possible_values = self.objects_tree["PpoTrainSignal"].keys()

        PpoTrackUnit.iObjsTag.possible_values = set(self.objects_tree["PpoTrackSection"].keys()) | \
                                                set(self.objects_tree["PpoPointSection"].keys()) | \
                                                set(self.objects_tree["PpoTrackAnDwithPoint"].keys()) | \
                                                set(self.objects_tree["PpoTrackAnD"].keys())
        PpoTrackUnit.evenTag.possible_values = self.objects_tree["PpoTrackEncodingPoint"].keys()
        PpoTrackUnit.oddTag.possible_values = self.objects_tree["PpoTrackEncodingPoint"].keys()

        PpoTrackAnDwithPoint.directionPointAnDTrack.possible_values = ["Direction12", "Direction21"]
        PpoTrackAnDwithPoint.oppositeTrackAnDwithPoint.possible_values = self.objects_tree["PpoTrackAnDwithPoint"].keys()

    def init_objects_from_tpl(self):
        for cls_name in self.tpl_dict:
            for obj_name in self.tpl_dict[cls_name]:
                self.init_object(cls_name, obj_name)
        self.send_objects_tree.emit(self.str_objects_tree)

    def init_bounded_tpl_descriptors(self):
        pass

    def init_bounded_obj_id_descriptors(self):
        ru_list = self.obj_id_dict["RU"]
        for subclass in PpoObject.__subclasses__():
            if hasattr(subclass, "idControlArea"):
                descr: StrBoundedValuesDescriptor = getattr(subclass, "idControlArea")
                descr.possible_values = ru_list

    def file_tpl_got(self, d: OrderedDict[str, list[str]]):
        # print("tpl_got")
        self.bool_tpl_got = True
        check_not_repeating_names(d)
        self.tpl_dict = d
        if self.bool_obj_id_got:
            self.compare()
        self.init_bounded_tpl_descriptors()

        self.init_objects_from_tpl()

    def file_obj_id_got(self, d: OrderedDict[str, list[str]]):
        # print("obj_id_got")
        self.bool_obj_id_got = True
        check_not_repeating_names(d)
        self.obj_id_dict = d
        if self.bool_tpl_got:
            self.compare()
        self.init_bounded_obj_id_descriptors()
        if self.current_object:
            self.got_object_name(self.current_object.tag)

    def compare(self):
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

    def attr_changed(self, address: list, new_attr_value: str):
        # print("attr changed", address, new_attr_value)
        obj = self.current_object
        for elem in address:
            attr_name = elem[0]
            index = elem[1]
            descr = getattr(obj.__class__, attr_name)
            if isinstance(descr, ObjectListDescriptor):
                obj_list = getattr(obj, attr_name)
                obj = obj_list[index]
            elif isinstance(descr, StrBoundedValuesDescriptor):
                if descr.is_list:
                    assert index != -1, "Index should be != -1"
                    old_list = copy(getattr(obj, attr_name))
                    old_list[index] = new_attr_value
                    setattr(obj, attr_name, old_list)
                else:
                    assert index == -1, "Index should be == -1"
                    setattr(obj, attr_name, new_attr_value)
            else:
                assert index == -1, "Index should be == -1"
                setattr(obj, attr_name, new_attr_value)
        self.got_object_name(self.current_object.tag)

    def add_attrib_list_element(self, address: list):
        # print("add_attrib_list", address)
        obj = self.current_object
        for i, elem in enumerate(address):
            attr_name = elem[0]
            index = elem[1]
            descr = getattr(obj.__class__, attr_name)
            # not last index handling
            if i < len(address) - 1:
                assert isinstance(descr, ObjectListDescriptor), "Internal index only for ObjectListDescriptor"
                obj_list = getattr(obj, attr_name)
                obj = obj_list[index]
                continue
            # last index handling
            assert index == -1, "Index should be == -1"
            if isinstance(descr, ObjectListDescriptor):
                new_item = descr.obj_type()
            elif isinstance(descr, StrBoundedValuesDescriptor):
                new_item = ""
            else:
                raise NotImplementedError("NotImplementedError")
            old_list = copy(getattr(obj, attr_name))
            old_list.append(new_item)
            setattr(obj, attr_name, old_list)
        self.got_object_name(self.current_object.tag)

    def remove_attrib_list_element(self, address: list):
        # print("remove_attrib_list", address)
        obj = self.current_object
        for i, elem in enumerate(address):
            attr_name = elem[0]
            index = elem[1]
            descr = getattr(obj.__class__, attr_name)
            # not last index handling
            if i < len(address) - 1:
                assert isinstance(descr, ObjectListDescriptor), "Internal index only for ObjectListDescriptor"
                obj_list = getattr(obj, attr_name)
                obj = obj_list[index]
                continue
            # last index handling
            assert index != -1, "Index should be != -1"
            old_list = copy(getattr(obj, attr_name))
            old_list.pop(index)
            setattr(obj, attr_name, old_list)
            self.got_object_name(self.current_object.tag)

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
        # print("dict = ", self.name_to_obj_dict)
        if tpo_obj in self.tech_to_interf_dict:
            i_obj = self.tech_to_interf_dict[tpo_obj]
            i_obj_name = i_obj.tag
            cls_i_name = self.obj_name_to_cls_name_dict[i_obj_name]
            self.objects_tree[cls_i_name].pop(i_obj_name)

        self.send_objects_tree.emit(self.str_objects_tree)

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
        if new_name in self.name_to_obj_dict:
            self.rename_rejected(old_name, new_name)
            self.send_objects_tree.emit(self.str_objects_tree)
        else:
            obj = self.name_to_obj_dict[old_name]
            obj.tag = new_name

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
                if old_name in interf_obj.tag:
                    new_interf_name = interf_obj.tag.replace(old_name, new_name)
                    self.got_rename(interf_obj.tag, new_interf_name)

    def rename_rejected(self, old_name: str, new_name: str):
        print("Rename from {} to {} rejected, name already exists".format(old_name, new_name))

    def generate_file(self, file_name: str):
        object_names = OrderedDict()
        if file_name in FILE_NAME_TO_CLASSES:
            for cls_name in FILE_NAME_TO_CLASSES[file_name]:
                object_names.update(self.objects_tree[cls_name])
        # if file_name == "TObjectsPoint":
        #     object_names.update(self.objects_tree["PpoPoint"])
        # elif file_name == "TObjectsSignal":
        #     object_names.update(self.objects_tree["PpoRoutePointer"])
        #     object_names.update(self.objects_tree["PpoTrainSignal"])
        #     object_names.update(self.objects_tree["PpoShuntingSignal"])
        #     object_names.update(self.objects_tree["PpoShuntingSignalWithTrackAnD"])
        #     object_names.update(self.objects_tree["PpoWarningSignal"])
        #     object_names.update(self.objects_tree["PpoRepeatSignal"])
        # elif file_name == "TObjectsTrack":
        #     object_names.update(self.objects_tree["PpoTrackAnD"])
        #     object_names.update(self.objects_tree["PpoTrackAnDwithPoint"])
        #     object_names.update(self.objects_tree["PpoLineEnd"])
        #     object_names.update(self.objects_tree["PpoPointSection"])
        #     object_names.update(self.objects_tree["PpoTrackSection"])
        # elif file_name == "IObjectsCodeGenerator":
        #     object_names.update(self.objects_tree["PpoCodeEnablingRelayALS"])
        # elif file_name == "IObjectsEncodingPoint":
        #     object_names.update(self.objects_tree["PpoTrackEncodingPoint"])
        # elif file_name == "IObjectsPoint":
        #     object_names.update(self.objects_tree["PpoPointMachineCi"])
        # elif file_name == "IObjectsRelay":
        #     object_names.update(self.objects_tree["PpoGeneralPurposeRelayInput"])
        #     object_names.update(self.objects_tree["PpoGeneralPurposeRelayOutput"])
        objects = [self.name_to_obj_dict[object_name] for object_name in object_names]
        obj_jsons = [obj.to_json_not_empty for obj in objects]
        with open(os.path.join("output", "config", "{}.json".format(file_name)), "w") as write_file:
            json.dump(obj_jsons, write_file, indent=4)

    def got_object_name(self, name: str):

        if name in self.obj_name_to_cls_name_dict:
            obj = self.name_to_obj_dict[name]

            # 1. rollback handling
            if not (self.current_object is obj):
                for attr_name in obj.data.keys():
                    if attr_name == "id":
                        attr_name += "_"
                    descr = getattr(obj.__class__, attr_name)
                    if isinstance(descr, DefaultDescriptor):
                        last_accepted_value = getattr(obj, "_{}".format(attr_name))
                        setattr(obj, attr_name, last_accepted_value)
                    # if isinstance(descr, StrBoundedValuesDescriptor):
                    #     last_accepted_value = getattr(obj, "_{}".format(attr_name))
                    #     setattr(obj, attr_name, last_accepted_value)

            # 2. main handling
            self.current_object = obj
            self.send_attrib_list.emit(self.form_columns(obj))

    def form_columns(self, obj: PpoObject) -> list:
        result_data = []
        title_label = LabelInfo()
        title_label.is_centered = True
        title_label.current_value = obj.tag
        result_data.append([title_label.to_tuple()])
        for attr_name in obj.data.keys():
            result_data.extend(self.form_attrib(obj, attr_name))
        return result_data

    def form_attrib(self, obj: PpoObject, attr_name: str, current_address: list = None) -> list:
        if not current_address:
            current_address = []
        result = []
        if attr_name in ["addrUI_KS", "output_SNK", "notificationPoints", "output_DSO", "adjEnterSig"]:
            result.append([("Spacing", "20")])
        if attr_name == "id":
            attr_name += "_"
        descr = getattr(obj.__class__, attr_name)
        if isinstance(descr, StrBoundedValuesDescriptor):
            if descr.is_list:
                label = LabelInfo()
                label.is_centered = False
                label.current_value = attr_name

                ca = copy(current_address)
                ca.append((attr_name, -1))
                add_btn = ButtonInfo()
                add_btn.is_add_button = True
                add_btn.attr_name = attr_name
                add_btn.address = ca
                result.append([label.to_tuple(), add_btn.to_tuple()])

                attr_values = getattr(obj, attr_name)
                attr_check_statuses = getattr(obj, "_check_status_{}".format(attr_name))
                for i, attr_value in enumerate(attr_values):
                    ca = copy(current_address)
                    ca.append((attr_name, i))

                    lineEdit = LineEditInfo()
                    lineEdit.possible_values = descr.possible_values
                    lineEdit.current_value = attr_value
                    lineEdit.check_status = attr_check_statuses[i]
                    lineEdit.attr_name = attr_name
                    lineEdit.index = i
                    lineEdit.address = ca

                    remove_button = ButtonInfo()
                    remove_button.is_add_button = False
                    remove_button.attr_name = attr_name
                    remove_button.index = i
                    remove_button.address = ca
                    result.append([lineEdit.to_tuple(), remove_button.to_tuple()])
            else:
                ca = copy(current_address)
                ca.append((attr_name, -1))
                label = LabelInfo()
                label.is_centered = False
                label.current_value = attr_name

                lineEdit = LineEditInfo()
                lineEdit.possible_values = descr.possible_values
                lineEdit.current_value = getattr(obj, attr_name)
                lineEdit.check_status = getattr(obj, "_check_status_{}".format(attr_name))
                lineEdit.attr_name = attr_name
                lineEdit.address = ca
                result.append([label.to_tuple(), lineEdit.to_tuple()])

        elif isinstance(descr, ObjectListDescriptor):
            title_label = LabelInfo()
            title_label.is_centered = True
            title_label.current_value = attr_name

            ca = copy(current_address)
            ca.append((attr_name, -1))
            add_btn = ButtonInfo()
            add_btn.is_add_button = True
            add_btn.attr_name = attr_name
            add_btn.address = ca
            result.append([title_label.to_tuple(), add_btn.to_tuple()])

            internal_objects = getattr(obj, attr_name)
            for i, internal_object in enumerate(internal_objects):
                ca = copy(current_address)
                ca.append((attr_name, i))
                internal_object: PpoObject
                all_attr_names = internal_object.all_attributes
                for local_attr_name in all_attr_names:
                    result.extend(self.form_attrib(internal_object, local_attr_name, ca))
                remove_button = ButtonInfo()
                remove_button.is_add_button = False
                remove_button.attr_name = attr_name
                remove_button.index = i
                remove_button.address = ca
                result.append([remove_button.to_tuple()])
        elif isinstance(descr, DefaultDescriptor):
            attr_check_status = getattr(obj, "_check_status_{}".format(attr_name))

            label = LabelInfo()
            label.is_centered = False
            label.current_value = attr_name

            ca = copy(current_address)
            ca.append((attr_name, -1))
            lineEdit = LineEditInfo()
            lineEdit.current_value = getattr(obj, attr_name)
            lineEdit.check_status = attr_check_status
            lineEdit.address = ca
            result.append([label.to_tuple(), lineEdit.to_tuple()])
        else:
            label = LabelInfo()
            label.is_centered = False
            label.current_value = attr_name

            ca = copy(current_address)
            ca.append((attr_name, -1))
            lineEdit = LineEditInfo()
            lineEdit.current_value = getattr(obj, attr_name)
            lineEdit.address = ca
            result.append([label.to_tuple(), lineEdit.to_tuple()])
        return result


class LineEditInfo:
    def __init__(self):
        self.possible_values = []
        self.current_value = ""
        self.check_status = ""
        self.attr_name = ""
        self.address = []
        self.index = -1

    def to_tuple(self) -> tuple[str, OrderedDict[str, Any]]:
        result = OrderedDict()
        result["possible_values"] = self.possible_values
        result["current_value"] = self.current_value
        result["check_status"] = self.check_status
        result["attr_name"] = self.attr_name
        result["index"] = self.index
        result["address"] = self.address
        return "LineEdit", result


class LabelInfo:
    def __init__(self):
        self.is_centered = True
        self.current_value = ""

    def to_tuple(self) -> tuple[str, OrderedDict[str, Any]]:
        result = OrderedDict()
        result["is_centered"] = self.is_centered
        result["current_value"] = self.current_value
        return "Label", result


class ButtonInfo:
    def __init__(self):
        self.is_add_button = True
        self.attr_name = ""
        self.address = []
        self.index = -1

    def to_tuple(self) -> tuple[str, OrderedDict[str, Any]]:
        result = OrderedDict()
        result["is_add_button"] = self.is_add_button
        result["attr_name"] = self.attr_name
        result["index"] = self.index
        result["address"] = self.address
        return "Button", result


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
    test_2 = False
    if test_2:
        additSw = AdditionalSwitch()
        print(additSw.all_attributes)

    test_3 = False
    if test_3:
        print(not_empty_extraction({1: "  ", 2: ""}))
        print(not_empty_extraction([{1: "  ", 2: ""}]))

    test_4 = True
    if test_4:

        class A:
            a = NewDefaultDescriptor(is_list=True)

        class B:
            b = NewDefaultDescriptor(single_attribute_type=A, min_count=3)

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

        obj_B = B()
        print(obj_B.b.single_attribute_list[0].obj)
        print(obj_B.b.single_attribute_list[0].obj.a)
        ai_3 = AttributeIndex(attr_name="a")
        ai_4 = AttributeIndex()
        address_3 = AttributeAddress(attribute_index_list=[ai_3, ai_4])
        command_6 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.insert),
                                                      attrib_address=address_3,
                                                      value="500")
        obj_B.b = command_6
        print(obj_B.b.single_attribute_list[0].obj)
        print(obj_B.b.single_attribute_list[0].obj.a)
