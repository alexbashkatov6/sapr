from __future__ import annotations

import os.path
from collections import OrderedDict
from typing import Type, Iterable, Optional, Any, Callable
import json
from functools import partial

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject

tpl_to_obj_id: OrderedDict[str, str] = OrderedDict()
tpl_to_obj_id['PpoPoint'] = "Str"
tpl_to_obj_id['PpoTrainSignal'] = "SvP"
tpl_to_obj_id['PpoShuntingSignal'] = "SvM"
tpl_to_obj_id['PpoPointSection'] = "SPU"
tpl_to_obj_id['PpoTrackSection'] = "SPU"
tpl_to_obj_id['PpoTrackAnD'] = "Put"
tpl_to_obj_id['PpoAutomaticBlockingSystem'] = "AdjAB"
tpl_to_obj_id['PpoSemiAutomaticBlockingSystem'] = "AdjPAB"
tpl_to_obj_id['PpoLineEnd'] = "Tpk"
tpl_to_obj_id['PpoControlAreaBorder'] = "GRU"


class TagRepeatingError(Exception):
    pass


class NotPossibleValueError(Exception):
    pass

# --------------------------  DESCRIPTORS  ------------------------


class Verificator:
    def __init__(self):
        self._verify_function = None

    @property
    def verify_function(self) -> Callable:
        return self._verify_function

    @verify_function.setter
    def verify_function(self, func: Callable):
        self._verify_function = func

    def verify(self, value) -> str:
        return self.verify_function(value)


def bounded_set_of_values(value, possible_values: Iterable) -> str:
    if value in possible_values:
        return ""
    return "Value {} not in possible values {}".format(value, possible_values)


class BoundedVerificator(Verificator):
    def __init__(self, possible_values: Iterable):
        super().__init__()
        self.verify_function = partial(bounded_set_of_values, possible_values=possible_values)
        self.possible_values = possible_values


class Cell:
    pass


class ElementaryObjectCell(Cell):
    def __init__(self):
        self._verificator = None
        self._input_value = None
        self._verified_value = None
        self._check_status = ""

    @property
    def input_value(self):
        return self._input_value

    @input_value.setter
    def input_value(self, val):
        self._input_value = val

    @property
    def check_status(self) -> str:
        return self._check_status

    @property
    def verified_value(self):
        return self._verified_value

    @property
    def verificator(self):
        return self._verificator

    @verificator.setter
    def verificator(self, value):
        self._verificator = value

    def verify(self):
        if self.verificator:
            self._check_status = self.verificator.verify(self.input_value)
            if not self.check_status:
                self._verified_value = self.input_value

    def reset_input_value(self):
        self.input_value = self.verified_value

    def view(self) -> tuple[str, str]:
        return "LineEdit", self.input_value


class CompositeObjectCell(Cell):
    def __init__(self):
        self.mapping: OrderedDict[str, Cell] = OrderedDict()

    def view(self) -> list[list]:
        result = []
        for attr_name, cell in self.mapping.items():
            if isinstance(cell, ElementaryObjectCell):
                result.append([("Label", attr_name), cell.view()])
            elif isinstance(cell, CompositeObjectCell):
                result.extend(cell.view())
            elif isinstance(cell, ListCell):
                result.extend(cell.view(attr_name))
        return result


class ListCell(Cell):
    def __init__(self):
        self.cells: list[Cell] = []

    def append_cell(self):
        pass

    def cell_at_index(self) -> Any:
        pass

    def remove_cell(self):
        pass

    def view(self, attr_name) -> list[list]:
        result = []
        result.append([("CenterLabel", attr_name), ("AddButton")])
        for cell in self.cells:
            if isinstance(cell, ElementaryObjectCell):
                result.append([cell.view()])
                result.append([("RemoveButton")])
            elif isinstance(cell, CompositeObjectCell):
                result.extend(cell.view())
                result.append([("RemoveButton")])
            elif isinstance(cell, ListCell):
                raise NotImplementedError("Not implemented")
        return result


class NamedDescriptor:

    def __init__(self):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name


# class BaseDescriptor(NamedDescriptor):
#
#     def __init__(self, verify_function: Callable = None, default_value: Any = None, min_count: int = 1):
#         super().__init__()
#         self.verify_function: Callable = verify_function  # -> str check_status
#         self.default_value = default_value
#         self.min_count = min_count
#         self.is_iterable = False
#
#     def __get__(self, instance, owner):
#         if not instance:
#             return self
#
#     def __set__(self, instance, composite_value):
#         setattr(instance, "_last_set_value_{}".format(self.name), composite_value)
#         if not isinstance(composite_value, Iterable):
#             composite_value = [composite_value]
#             self.is_iterable = False
#         else:
#             self.is_iterable = True
#         check_status = []
#         for i, elem_value in enumerate(composite_value):
#             if self.verify_function:
#                 check_status.append(self.verify_function(elem_value))
#         setattr(instance, "_{}".format(self.name), value)


class BoundedValuesDescriptor:

    def __init__(self, default_value: Any = None, is_list: bool = False, min_count: int = 1):
        self.name = None
        self.is_list = is_list
        self.min_count = min_count
        self.default_value = default_value
        self._possible_values = []

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        if hasattr(instance, "_{}".format(self.name)):
            return getattr(instance, "_{}".format(self.name))
        setattr(instance, "_{}".format(self.name), "")
        setattr(instance, "_str_{}".format(self.name), "")
        setattr(instance, "_check_status_{}".format(self.name), "")
        return ""

    def __set__(self, instance, value: str):
        setattr(instance, "_str_{}".format(self.name), value)
        if self.possible_values:
            if not self.is_list:
                values = [value]
            else:
                values = value.split(" ")
            for value in values:
                if self.default_value and (value == self.default_value):
                    continue
                if value not in self.possible_values:
                    setattr(instance, "_check_status_{}".format(self.name),
                            "Value {} not in list of possible values: {}".format(value, self.possible_values))
                    return
        setattr(instance, "_check_status_{}".format(self.name), "")
        setattr(instance, "_{}".format(self.name), value)

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


class DataDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return [key for key in owner.__dict__.keys() if not key.startswith("__")]

        data_odict = OrderedDict()
        for attr_name in owner.data:
            if attr_name == "id_":
                data_odict["id"] = getattr(instance, attr_name)
            else:
                data_odict[attr_name] = getattr(instance, attr_name)
        return data_odict

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class ToJsonDescriptor:

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


class IdDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class IndentDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class IdControlAreaDescriptor(BoundedValuesDescriptor):
    pass


class IObjTagSimpleDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class RoutePointersDescriptor(BoundedValuesDescriptor):
    pass


class UkspsDescriptor(BoundedValuesDescriptor):
    pass


class LengthDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        if hasattr(instance, "_length"):
            return getattr(instance, "_length")
        return "5"

    def __set__(self, instance, value):
        setattr(instance, "_length", value)


class TrackUnitDescriptor(BoundedValuesDescriptor):
    pass

    # def __get__(self, instance, owner):
    #     if isinstance(instance, PpoLineEnd):
    #         self.default_value = "nullptr"
    #     return super().__get__(instance, owner)


class PointsMonitoringDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return "STRELKI"

    def __set__(self, instance, value):
        pass


class SectionDescriptor(BoundedValuesDescriptor):
    pass


class RailFittersWarningAreaDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class AutoReturnDescriptor(BoundedValuesDescriptor):
    pass


class PointDescriptor(BoundedValuesDescriptor):
    pass


class LockingDescriptor(BoundedValuesDescriptor):
    pass


class PlusMinusDescriptor(BoundedValuesDescriptor):
    pass


class AdditionalSwitchDescriptor:
    point = PointDescriptor()
    selfPosition = PlusMinusDescriptor()
    dependencePosition = PlusMinusDescriptor()

    def __get__(self, instance, owner):
        if not instance:
            return self
        return OrderedDict.fromkeys((key, getattr(self, key)) for key in self.__dict__.keys() if not key.startswith("__"))

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class PairPointDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class OversizedDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class IsInvitationSignalOpeningBeforeDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class SingleTrackDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class RailCrossingDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class AddrKiDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class AddrUiDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class CrossroadDirectiveDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class NotificationPointsDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class CrossroadDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return ["1", "2", "3"]

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class IObjTagTrackCrossroadDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class ModeLightSignalDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class AddrCiDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class TypeLightSignalDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class EnterSignalDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class IObjTagTrackUnitDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class EncodingPointDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class DirectionPointAndTrackDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))


class OppositeTrackAnDwithPointDescriptor:

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance.tag

    def __set__(self, instance, value):
        raise NotImplementedError('{} setter not implemented'.format(self.__class__.__name__))

# --------------------------  OBJECT CLASSES  ------------------------


class PpoObject:
    class_ = ClassNameDescriptor()
    tag = TagDescriptor()
    data = DataDescriptor()
    to_json = ToJsonDescriptor()


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
    length = LengthDescriptor()
    trackUnit = TrackUnitDescriptor()


class PpoTrackAnDwithPoint(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor()
    trackUnit = TrackUnitDescriptor()
    directionPointAnDTrack = DirectionPointAndTrackDescriptor()
    oppositeTrackAnDwithPoint = OppositeTrackAnDwithPointDescriptor()


class PpoLineEnd(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor()
    trackUnit = TrackUnitDescriptor(default_value="nullptr")


class PpoPointSection(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor()
    trackUnit = TrackUnitDescriptor()


class PpoTrackSection(PpoObject):
    id_ = IdDescriptor()
    indent = IndentDescriptor()
    idControlArea = IdControlAreaDescriptor()
    length = LengthDescriptor()
    trackUnit = TrackUnitDescriptor()


class AdditionalSwitch:
    point = PointDescriptor()
    selfPosition = PlusMinusDescriptor()
    dependencePosition = PlusMinusDescriptor()


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
    additionalSwitch = AdditionalSwitchDescriptor()
    pairPoint = PairPointDescriptor()
    oversizedPlus = OversizedDescriptor()
    oversizedMinus = OversizedDescriptor()


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

    output_DSO = CrossroadDirectiveDescriptor()
    output_OSO = CrossroadDirectiveDescriptor()
    output_FDP = CrossroadDirectiveDescriptor()
    output_IFP = CrossroadDirectiveDescriptor()

    notificationPoints = NotificationPointsDescriptor()


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

    output_SNK = CrossroadDirectiveDescriptor()
    output_DS = CrossroadDirectiveDescriptor()
    output_OV = CrossroadDirectiveDescriptor()
    output_PV = CrossroadDirectiveDescriptor()
    output_RUU = CrossroadDirectiveDescriptor()
    output_R = CrossroadDirectiveDescriptor()

    notificationPoints = NotificationPointsDescriptor()


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
    crossroad = CrossroadDescriptor()


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

# --------------------------  HANDLER  ------------------------


def check_not_repeating_names(odict):
    names = []
    for cls_name in odict:
        for obj_name in odict[cls_name]:
            if obj_name in names:
                raise TagRepeatingError("Tag {} repeats".format(obj_name))
            names.append(obj_name)


class AttribProperties:
    def __init__(self):
        self.last_accepted_value = ""
        self.current_value = ""
        self.possible_values = []
        self.check_status = ""

    def to_odict(self):
        result = OrderedDict()
        result["current_value"] = self.current_value
        result["possible_values"] = self.possible_values
        result["check_status"] = self.check_status
        return result


class ObjectsHandler(QObject):
    send_objects_tree = pyqtSignal(OrderedDict)
    send_attrib_dict = pyqtSignal(OrderedDict)

    def __init__(self):
        super().__init__()
        self.bool_tpl_got = False
        self.bool_obj_id_got = False
        self.tpl_dict: OrderedDict[str, list[str]] = OrderedDict()  # input structure from tpl
        self.obj_id_dict: OrderedDict[str, list[str]] = OrderedDict()

        self.objects_tree: OrderedDict[str, OrderedDict[str, PpoObject]] = OrderedDict()  # output structure

        self.current_object: Optional[PpoObject] = None

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

            inter_cls_ = PpoLightSignalCi
            inter_obj = inter_cls_()
            inter_obj.tag = obj_name+"_Ci"
            self.objects_tree["PpoLightSignalCi"][inter_obj.tag] = inter_obj

        elif cls_name == "PpoRoutePointer":
            tpo_cls_ = PpoRoutePointer
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            inter_cls_ = PpoRoutePointerRi
            inter_obj = inter_cls_()
            inter_obj.tag = obj_name+"_Ri"
            self.objects_tree["PpoRoutePointerRi"][inter_obj.tag] = inter_obj

        elif cls_name == "PpoAutomaticBlockingSystem":
            tpo_cls_ = PpoAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            inter_cls_ = PpoAutomaticBlockingSystemRi
            inter_obj = inter_cls_()
            inter_obj.tag = obj_name+"_Ri"
            self.objects_tree["PpoAutomaticBlockingSystemRi"][inter_obj.tag] = inter_obj

        elif cls_name == "PpoSemiAutomaticBlockingSystem":
            tpo_cls_ = PpoSemiAutomaticBlockingSystem
            tpo_obj = tpo_cls_()
            tpo_obj.tag = obj_name
            if cls_name not in self.objects_tree:
                self.objects_tree[cls_name] = OrderedDict()
            self.objects_tree[cls_name][obj_name] = tpo_obj

            inter_cls_ = PpoSemiAutomaticBlockingSystemRi
            inter_obj = inter_cls_()
            inter_obj.tag = obj_name+"_Ri"
            self.objects_tree["PpoSemiAutomaticBlockingSystemRi"][inter_obj.tag] = inter_obj

        elif cls_name == "PpoTrackCrossroad":
            first_symbols = obj_name[:2]
            if first_symbols not in self.name_to_obj_dict:
                crossing_cls_ = PpoRailCrossing
                crossing_obj = crossing_cls_()
                crossing_obj.tag = first_symbols
                self.objects_tree["PpoRailCrossing"][crossing_obj.tag] = crossing_obj

                ri_crossing_cls_ = PpoRailCrossingRi
                ri_crossing_obj = ri_crossing_cls_()
                ri_crossing_obj.tag = first_symbols+"_Ri"
                self.objects_tree["PpoRailCrossingRi"][ri_crossing_obj.tag] = ri_crossing_obj

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
        self.objects_tree["    "] = OrderedDict()
        self.objects_tree["      INTERFACE OBJECTS"] = OrderedDict()
        self.objects_tree["     "] = OrderedDict()
        self.objects_tree["PpoLightSignalCi"] = OrderedDict()
        self.objects_tree["PpoRoutePointerRi"] = OrderedDict()
        self.objects_tree["PpoAutomaticBlockingSystemRi"] = OrderedDict()
        self.objects_tree["PpoSemiAutomaticBlockingSystemRi"] = OrderedDict()
        self.objects_tree["PpoRailCrossing"] = OrderedDict()
        self.objects_tree["PpoRailCrossingRi"] = OrderedDict()
        self.objects_tree["PpoTrackCrossroad"] = OrderedDict()
        self.objects_tree["PpoControlDeviceDerailmentStockCi"] = OrderedDict()
        self.objects_tree["PpoTrackReceiverRi"] = OrderedDict()
        self.objects_tree["   "] = OrderedDict()
        self.objects_tree[" "] = OrderedDict()
        self.objects_tree["      TECHNOLOGY OBJECTS"] = OrderedDict()
        self.objects_tree["  "] = OrderedDict()
        for cls_name in self.tpl_dict:
            self.objects_tree[cls_name] = OrderedDict()
        self.objects_tree["PpoControlDeviceDerailmentStock"] = OrderedDict()
        self.objects_tree["PpoTrackUnit"] = OrderedDict()

    def init_descriptor_links(self):
        PpoRoutePointer.routePointer.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()
        PpoTrainSignal.routePointer.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()
        PpoTrainSignal.groupRoutePointers.possible_values = self.objects_tree["PpoRoutePointerRi"].keys()
        PpoTrainSignal.uksps.possible_values = self.objects_tree["PpoControlDeviceDerailmentStock"].keys()
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
        # print("type = ", type(PpoPoint.additionalSwitch))
        PpoPoint.additionalSwitch.__class__.point.possible_values = self.objects_tree["PpoPoint"].keys()
        PpoPoint.additionalSwitch.__class__.selfPosition.possible_values = ["+", "-"]
        PpoPoint.additionalSwitch.__class__.dependencePosition.possible_values = ["+", "-"]

    def init_objects(self):
        self.init_classes()
        self.init_descriptor_links()
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
                descr: BoundedValuesDescriptor = getattr(subclass, "idControlArea")
                descr.possible_values = ru_list

    def file_tpl_got(self, d: OrderedDict[str, list[str]]):
        # print("tpl_got")
        self.bool_tpl_got = True
        check_not_repeating_names(d)
        self.tpl_dict = d
        if self.bool_obj_id_got:
            self.compare()
        self.init_bounded_tpl_descriptors()

        self.init_objects()

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
            if cls_name in tpl_to_obj_id:
                tpl_list = self.tpl_dict[cls_name]
                obj_id_list = self.obj_id_dict[tpl_to_obj_id[cls_name]]
                for tag in tpl_list:
                    if (cls_name, tag) not in differences['tpl']:
                        differences['tpl'].append((cls_name, tag))
                for tag in obj_id_list:
                    if (tpl_to_obj_id[cls_name], tag) not in differences['obj_id']:
                        differences['obj_id'].append((tpl_to_obj_id[cls_name], tag))

        # cycle of remove
        for cls_name in self.tpl_dict:
            if cls_name in tpl_to_obj_id:
                tpl_list = self.tpl_dict[cls_name]
                obj_id_list = self.obj_id_dict[tpl_to_obj_id[cls_name]]
                for tag in tpl_list:
                    if (tpl_to_obj_id[cls_name], tag) in differences['obj_id']:
                        differences['obj_id'].remove((tpl_to_obj_id[cls_name], tag))
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

    def attr_changed(self, attr_name: str, new_attr_value: str):
        current_obj = self.current_object
        setattr(current_obj, attr_name, new_attr_value)
        self.got_object_name(self.current_object.tag)

    def got_change_cls_request(self, obj_name: str, to_cls_name: str):
        # 1. create new obj in new class
        new_name = self.got_add_new(to_cls_name)
        # 2. remove obj in old class
        self.got_remove_request(obj_name)
        # 3. rename obj in new class
        self.got_rename(new_name, obj_name)

        self.send_objects_tree.emit(self.str_objects_tree)

    def got_remove_request(self, name: str):
        cls_name = self.obj_name_to_cls_name_dict[name]
        self.objects_tree[cls_name].pop(name)

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

    def rename_rejected(self, old_name: str, new_name: str):
        print("Rename from {} to {} rejected, name already exists".format(old_name, new_name))

    def got_object_name(self, name: str):

        if name in self.obj_name_to_cls_name_dict:
            obj = self.name_to_obj_dict[name]

            # 1. rollback handling
            if not (self.current_object is obj):
                for attr_name in obj.data.keys():
                    if attr_name == "id":
                        attr_name += "_"
                    descr = getattr(obj.__class__, attr_name)
                    if isinstance(descr, BoundedValuesDescriptor):
                        last_accepted_value = getattr(obj, attr_name)
                        setattr(obj, attr_name, last_accepted_value)

            # 2. main handling
            self.current_object = obj
            result_data = OrderedDict()
            i = 0
            for attr_name in obj.data.keys():
                if attr_name in ["addrUI_KS", "output_SNK", "notificationPoints", "output_DSO"]:
                    i += 1
                    result_data["spacing_{}".format(i)] = "20"
                if attr_name == "id":
                    attr_name += "_"
                result_data[attr_name] = self.form_attrib_properties(attr_name)
            self.send_attrib_dict.emit(result_data)

    def form_attrib_properties(self, attr_name: str) -> OrderedDict:
        current_obj = self.current_object
        ap = AttribProperties()
        ap.last_accepted_value = getattr(current_obj, attr_name)
        descr = getattr(current_obj.__class__, attr_name)
        # if isinstance(descr, AdditionalSwitchDescriptor):
        #     result = self.form_attrib_properties()
        if isinstance(descr, BoundedValuesDescriptor):
            ap.possible_values = descr.possible_values
            ap.current_value = getattr(current_obj, "_str_{}".format(attr_name))
            ap.check_status = getattr(current_obj, "_check_status_{}".format(attr_name))
        else:
            ap.current_value = ap.last_accepted_value
        return ap.to_odict()

    def generate_file(self, file_name: str):
        if file_name == "TObjectsPoint":
            object_names = self.objects_tree["PpoPoint"]
            objects = [self.name_to_obj_dict[object_name] for object_name in object_names]
            obj_jsons = [obj.to_json for obj in objects]
            with open(os.path.join("output", "config", "{}.json".format(file_name)), "w") as write_file:
                json.dump(obj_jsons, write_file, indent=4)


if __name__ == '__main__':
    train_signal = PpoTrainSignal()
    train_signal.tag = "I9"
    print(train_signal.data)
    print(PpoAutomaticBlockingSystemRi.__dict__.keys())
