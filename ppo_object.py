from __future__ import annotations

from copy import copy
from typing import Type, Iterable, Optional, Any, Callable, Union
from functools import partial
from collections import OrderedDict

from descr_value_checkers import ValueChecker, ValueInSetChecker, ValueAddressUIChecker, ValueAddressKIChecker, \
    ValuePlusMinusChecker, ValueYesNoChecker, ValueZeroOneChecker, ValueStrIsPositiveNumberChecker, \
    ValueTimeAutoReturnChecker, ValueElectricHeatingOnOffChecker, ValueStrIsNonNegNumberChecker, \
    ValueABInvitSignalOpeningBeforeChecker, ValuePABInvitSignalOpeningBeforeChecker
from descr_value_suggesters import Suggester, ConstSuggester, AddressSuggester, \
    EqualOtherAttributeSuggester, InterstationDirectiveSuggester
from descr_value_presentation import Presentation, IntPresentation, AddressPresentation, IfZeroThenIntPresentation
from attr_manage_group import AMG_ADR_UI, AMG_ADR_KI
from attribute_address_access import set_str_attr, get_str_attr
from attribute_management import AttributeAddress, NamedAttribute, SingleAttribute, AttributeCommand, \
    ComplexAttributeManagementCommand, StrSingleAttribute, ObjSingleAttribute, AttributeIndex, UnaryAttribute
from aar_descriptor import AttributeAccessRulesDescriptor, cyclic_find
from file_object_conversions import attr_name_from_file_to_object, attr_name_from_object_to_file


class ClassNameDescriptor:
    def __get__(self, instance, owner):
        return owner.__name__


def extract_data_attr_names(obj: PpoObject) -> list[str]:
    data_attr_names = []
    for cls in list(reversed(obj.__class__.__mro__[:-2])):  # last = PpoObject, object
        for attr_name in cls.__dict__:
            if not attr_name.startswith("__"):
                data_attr_names.append(attr_name)
    return data_attr_names


set_tag = partial(set_str_attr, attr_address=AttributeAddress([AttributeIndex("tag", 0)]))
get_tag = partial(get_str_attr, attr_address=AttributeAddress([AttributeIndex("tag", 0)]))


def elementary_attr_handling(address, attr_val) -> list[ComplexAttributeManagementCommand]:
    if isinstance(attr_val, str):
        command = ComplexAttributeManagementCommand(AttributeCommand(AttributeCommand.set_single), address, attr_val)
        return [command]
    elif isinstance(attr_val, int):
        attr_val = str(attr_val)
        command = ComplexAttributeManagementCommand(AttributeCommand(AttributeCommand.set_single), address, attr_val)
        return [command]
    elif isinstance(attr_val, dict):
        com_list = address_expansion(attr_val, address)
        return com_list
    else:
        assert False


def address_expansion(input_dict: dict, input_address: AttributeAddress) -> list[ComplexAttributeManagementCommand]:
    result_command_list: list[ComplexAttributeManagementCommand] = []
    for attr_name, attr_val in input_dict.items():
        # if attr_name == "Сrossroad":
        #     print("Сrossroad")
        attr_name = attr_name_from_file_to_object(attr_name)
        if isinstance(attr_val, list):
            for i, elem in enumerate(attr_val):
                aa = input_address.expand(AttributeIndex(attr_name, i))
                result_command_list.extend(elementary_attr_handling(aa, elem))
        else:
            aa = input_address.expand(AttributeIndex(attr_name, -1))
            result_command_list.extend(elementary_attr_handling(aa, attr_val))
    return result_command_list


class PpoObject:
    class_ = ClassNameDescriptor()
    tag = AttributeAccessRulesDescriptor()

    def __init__(self, obj_addr: AttributeAddress = None):
        self.obj_addr = obj_addr or AttributeAddress()

    @property
    def data_attr_names(self) -> list[str]:
        return extract_data_attr_names(self)

    def to_json_dict(self, to_file: bool = True, is_base_object: bool = False) -> dict:
        """ to file output format is much smaller, because not includes attributes metadata """
        json_dict = {}
        data_dict = {}
        if is_base_object:
            json_dict["class"] = self.class_
            json_dict["tag"] = get_tag(self)  # self.tag
            json_dict["data"] = data_dict
        data_attr_names = extract_data_attr_names(self)
        for data_attr_name in data_attr_names:
            named_attr: NamedAttribute = getattr(self, data_attr_name)
            if to_file:
                result = named_attr.file_representation
                if not (result is None):
                    data_dict[attr_name_from_object_to_file(data_attr_name)] = result
            else:
                result = named_attr.attr_exchange_representation
                data_dict[attr_name_from_object_to_file(data_attr_name)] = result
        if is_base_object:
            return json_dict
        else:
            return data_dict

    def from_dict(self, d: dict):
        if "tag" in d:
            set_tag(self, d["tag"])
        if "data" in d:
            data = d["data"]
            command_list = address_expansion(data, self.obj_addr)
            # print("command list = ", len(command_list),
            #       [[idx.to_list() for idx in com.attrib_address.attribute_index_list] for com in command_list])
            for command in command_list:
                attr_name = command.attrib_address.attribute_index_list[0].attr_name
                setattr(self, attr_name, command)


class PpoObject2i(PpoObject):
    id_ = AttributeAccessRulesDescriptor(value_suggester=EqualOtherAttributeSuggester("tag"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=EqualOtherAttributeSuggester("tag"),
                                            presentation=IfZeroThenIntPresentation())


class PpoObject3i(PpoObject2i):
    idControlArea = AttributeAccessRulesDescriptor(value_checkers=ValueInSetChecker())


class PpoObject4i(PpoObject3i):
    iObjTag = AttributeAccessRulesDescriptor(value_suggester=EqualOtherAttributeSuggester("tag"))


class PpoRoutePointer(PpoObject3i):
    routePointer = AttributeAccessRulesDescriptor()


class PpoRoutePointerRi(PpoObject):
    onRoutePointer = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    outputAddrs = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI, is_list=True)


class StartWarningArea(PpoObject):
    obj = AttributeAccessRulesDescriptor()
    point = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                           presentation=IntPresentation())


class PpoTrainSignal(PpoObject4i):
    railCrossing = AttributeAccessRulesDescriptor()
    delayOpenSignalShRoute = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                            presentation=IntPresentation())
    delayOpenSignalTrRoute = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                            presentation=IntPresentation())
    startUp = AttributeAccessRulesDescriptor()
    routePointer = AttributeAccessRulesDescriptor()
    startWarningArea = AttributeAccessRulesDescriptor(single_attribute_type=StartWarningArea)
    groupRoutePointers = AttributeAccessRulesDescriptor(is_list=True)
    uksps = AttributeAccessRulesDescriptor()
    shutOffTime = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                 presentation=IntPresentation())


class PpoGroupTrainSignal(PpoObject4i):
    routePointer = AttributeAccessRulesDescriptor()


class PpoFictionalSignal(PpoObject4i):
    groupSignal = AttributeAccessRulesDescriptor()
    startWarningArea = AttributeAccessRulesDescriptor(single_attribute_type=StartWarningArea)


class PpoWarningSignal(PpoObject4i):
    signalTag = AttributeAccessRulesDescriptor()


class PpoRepeatSignal(PpoObject4i):
    signalTag = AttributeAccessRulesDescriptor()


class PpoShuntingSignal(PpoObject4i):
    delayOpenSignalShRoute = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                            presentation=IntPresentation())


class PpoShuntingSignalWithTrackAnD(PpoObject4i):
    routePullTrain = AttributeAccessRulesDescriptor()


class PpoFictionalRepeatingShuntingSignal(PpoObject4i):
    groupSignal = AttributeAccessRulesDescriptor()


class PpoInterstationWaySignal(PpoObject4i):
    protectiveTrack = AttributeAccessRulesDescriptor()
    signalRepeat = AttributeAccessRulesDescriptor()
    stateInterstationWay = AttributeAccessRulesDescriptor()


class PpoInterstationWayFictionalSignal(PpoObject3i):
    signalRepeat = AttributeAccessRulesDescriptor()
    stateInterstationWay = AttributeAccessRulesDescriptor()


class PpoIndicationSignal(PpoObject4i):
    pass


class PpoLightSignalCi(PpoObject):
    mode = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("DN_DSN"))
    addrKa = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker())
    addrKi = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                            presentation=IntPresentation())
    addrUi = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                            presentation=IntPresentation())
    type_ = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                           presentation=IntPresentation())


class PpoTrack(PpoObject3i):
    length = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                            value_suggester=ConstSuggester("5"),
                                            presentation=IntPresentation())
    trackUnit = AttributeAccessRulesDescriptor()


class PpoAnDtrack(PpoTrack):
    pass


class PpoTrackAnDwithPoint(PpoTrack):
    directionPointAnDTrack = AttributeAccessRulesDescriptor(
        value_checkers=ValueInSetChecker(["Direction12", "Direction21"]))
    oppositeTrackAnDwithPoint = AttributeAccessRulesDescriptor()


class PpoLineEnd(PpoTrack):
    id_ = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                            presentation=IfZeroThenIntPresentation())
    trackUnit = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("nullptr"))


class PpoPointSection(PpoTrack):
    type_ = AttributeAccessRulesDescriptor()
    crossroad = AttributeAccessRulesDescriptor()


class PpoTrackSection(PpoTrack):
    pass


class PpoInterstationWayTrack(PpoObject3i):
    trackUnit = AttributeAccessRulesDescriptor()


class PpoIndicationTrack(PpoObject3i):
    trackUnit = AttributeAccessRulesDescriptor()


class AdditionalSwitch(PpoObject):
    point = AttributeAccessRulesDescriptor()
    selfPosition = AttributeAccessRulesDescriptor(value_checkers=ValuePlusMinusChecker())
    dependencePosition = AttributeAccessRulesDescriptor(value_checkers=ValuePlusMinusChecker())


class SectionAndIgnoreCondition(PpoObject):
    section = AttributeAccessRulesDescriptor()
    point = AttributeAccessRulesDescriptor()
    position = AttributeAccessRulesDescriptor(value_checkers=ValuePlusMinusChecker())


class NotificationPoint(PpoObject):
    point = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    delay = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)


class PpoPoint(PpoObject4i):
    type_ = AttributeAccessRulesDescriptor(presentation=IntPresentation())
    pointsMonitoring = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("STRELKI"))
    section = AttributeAccessRulesDescriptor()
    railFittersWarningArea = AttributeAccessRulesDescriptor(value_suggester=EqualOtherAttributeSuggester("tag"))
    autoReturn = AttributeAccessRulesDescriptor(value_checkers=ValueTimeAutoReturnChecker())
    guardPlusPlus = AttributeAccessRulesDescriptor(is_list=True)
    guardPlusMinus = AttributeAccessRulesDescriptor(is_list=True)
    guardMinusPlus = AttributeAccessRulesDescriptor(is_list=True)
    guardMinusMinus = AttributeAccessRulesDescriptor(is_list=True)
    lockingPlus = AttributeAccessRulesDescriptor(is_list=True)
    lockingPlusSignal = AttributeAccessRulesDescriptor(is_list=True)
    lockingMinus = AttributeAccessRulesDescriptor(is_list=True)
    lockingMinusSignal = AttributeAccessRulesDescriptor(is_list=True)
    additionalSwitch = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=AdditionalSwitch)
    pairPoint = AttributeAccessRulesDescriptor()
    oversizedPlus = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=SectionAndIgnoreCondition)
    oversizedMinus = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=SectionAndIgnoreCondition)
    additionalGuardLock = AttributeAccessRulesDescriptor(single_attribute_type=SectionAndIgnoreCondition)


class PpoPointMachineCi(PpoObject):
    addrKi = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                            presentation=IntPresentation())
    addrUi = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                            presentation=IntPresentation())


class PpoControlAreaBorder(PpoObject3i):
    pass


class PpoSemiAutomaticBlockingSystem(PpoObject4i):
    isInvitationSignalOpeningBefore = AttributeAccessRulesDescriptor(
        value_checkers=ValuePABInvitSignalOpeningBeforeChecker())


class PpoSemiAutomaticBlockingSystemRi(PpoObject):
    addrKI_SNP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_S1U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_1U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_FP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_POS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_PS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_OP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_DSO = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KZH = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)

    addrUI_KS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)

    output_DSO = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_OSO = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_FDP = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_IFP = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))

    notificationPoints = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=NotificationPoint)


class PpoAutomaticBlockingSystem(PpoObject4i):
    isInvitationSignalOpeningBefore = AttributeAccessRulesDescriptor(
        value_checkers=ValueABInvitSignalOpeningBeforeChecker())
    singleTrack = AttributeAccessRulesDescriptor(value_checkers=ValueYesNoChecker())


class PpoAutomaticBlockingSystemRi(PpoObject):
    addrKI_SNP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_SN = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_S1U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_S1P = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_1U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_1P = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_2U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_3U = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_ZU = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KZH = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_UUB = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_PB = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KV = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_A = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)

    addrUI_KS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_I = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_KZH = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_VIP1 = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_VIP2 = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_VIP3 = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_OKV = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_KM = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)

    output_SNK = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_DS = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_OV = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_PV = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_RUU = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))
    output_R = AttributeAccessRulesDescriptor(value_suggester=InterstationDirectiveSuggester("tag"))

    adjEnterSig = AttributeAccessRulesDescriptor()

    notificationPoints = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=NotificationPoint)


class PpoAdjacentStationTrainSignal(PpoObject4i):
    isInvitationSignalOpeningBefore = AttributeAccessRulesDescriptor()


class PpoAdjacentStationTrainSignalRi(PpoObject):
    addrKI_SNP = AttributeAccessRulesDescriptor()
    addrKI_S1U = AttributeAccessRulesDescriptor()
    addrKI_S1P = AttributeAccessRulesDescriptor()
    addrKI_1U = AttributeAccessRulesDescriptor()
    addrKI_2U = AttributeAccessRulesDescriptor()
    addrKI_3U = AttributeAccessRulesDescriptor()

    addrUI_SNP = AttributeAccessRulesDescriptor()
    addrUI_S1U = AttributeAccessRulesDescriptor()
    addrUI_S1P = AttributeAccessRulesDescriptor()
    addrUI_1U = AttributeAccessRulesDescriptor()
    addrUI_2U = AttributeAccessRulesDescriptor()
    addrUI_3U = AttributeAccessRulesDescriptor()

    adjEnterSig = AttributeAccessRulesDescriptor()
    selfSignal = AttributeAccessRulesDescriptor()
    trackEnter = AttributeAccessRulesDescriptor()


class PpoInterstationWayBorder(PpoObject4i):
    id_ = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                            presentation=IfZeroThenIntPresentation())
    type_ = AttributeAccessRulesDescriptor()
    stateInterstationWay = AttributeAccessRulesDescriptor()
    oppositeBorder = AttributeAccessRulesDescriptor()
    protectiveTrack = AttributeAccessRulesDescriptor()
    removalZone1 = AttributeAccessRulesDescriptor(is_list=True)
    removalZone2 = AttributeAccessRulesDescriptor(is_list=True)
    removalZone3 = AttributeAccessRulesDescriptor(is_list=True)
    approachZone1 = AttributeAccessRulesDescriptor(is_list=True)
    approachZone2 = AttributeAccessRulesDescriptor(is_list=True)
    approachZone3 = AttributeAccessRulesDescriptor(is_list=True)
    notificationPoints = AttributeAccessRulesDescriptor(is_list=True)
    approachZoneCancelRoute = AttributeAccessRulesDescriptor()


class PpoInterstationWayBorderRi(PpoObject):
    addrKI_SNK = AttributeAccessRulesDescriptor()
    addrKI_DS = AttributeAccessRulesDescriptor()
    addrKI_OV = AttributeAccessRulesDescriptor()
    addrKI_PV = AttributeAccessRulesDescriptor()
    addrKI_RUU = AttributeAccessRulesDescriptor()
    addrKI_R = AttributeAccessRulesDescriptor()
    addrKI_KS = AttributeAccessRulesDescriptor()
    addrKI_I = AttributeAccessRulesDescriptor()
    addrKI_KZH = AttributeAccessRulesDescriptor()
    addrKI_VIP1 = AttributeAccessRulesDescriptor()
    addrKI_VIP2 = AttributeAccessRulesDescriptor()
    addrKI_VIP3 = AttributeAccessRulesDescriptor()
    addrKI_KM = AttributeAccessRulesDescriptor()
    addrKI_OKV = AttributeAccessRulesDescriptor()
    addrKI_Notification = AttributeAccessRulesDescriptor()

    addrUI_SNP = AttributeAccessRulesDescriptor()
    addrUI_SN = AttributeAccessRulesDescriptor()
    addrUI_S1U = AttributeAccessRulesDescriptor()
    addrUI_S1P = AttributeAccessRulesDescriptor()
    addrUI_1U = AttributeAccessRulesDescriptor()
    addrUI_2U = AttributeAccessRulesDescriptor()
    addrUI_3U = AttributeAccessRulesDescriptor()
    addrUI_ZU = AttributeAccessRulesDescriptor()
    addrUI_KP = AttributeAccessRulesDescriptor()
    addrUI_UB = AttributeAccessRulesDescriptor()
    addrUI_PB = AttributeAccessRulesDescriptor()
    addrUI_KV = AttributeAccessRulesDescriptor()
    addrUI_A = AttributeAccessRulesDescriptor()

    notificationPoints = AttributeAccessRulesDescriptor(is_list=True, single_attribute_type=NotificationPoint)

    enterSignal = AttributeAccessRulesDescriptor()
    track_P1 = AttributeAccessRulesDescriptor()
    track_P2 = AttributeAccessRulesDescriptor()


class PpoControlDeviceDerailmentStock(PpoObject4i):
    pass


class PpoControlDeviceDerailmentStockCi(PpoObject):
    addrKI_1KSO = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker())
    addrKI_1KSR = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker())
    addrKI_2KSO = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker())
    addrKI_2KSR = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker())

    addrKI_KSV = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_SNP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_1UP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_2UP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_1UU = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_2UU = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)

    addrUI_1KSD = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_2KSB = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_KSVA = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)

    enterSignal = AttributeAccessRulesDescriptor()


class PpoTrackUnit(PpoObject):
    iObjsTag = AttributeAccessRulesDescriptor(is_list=True)
    oddTag = AttributeAccessRulesDescriptor(is_list=True)
    evenTag = AttributeAccessRulesDescriptor(is_list=True)
    longFreeTime = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                  presentation=IntPresentation())


class PpoTrackReceiverRi(PpoObject):
    addrKI_P = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)


class PpoTrackReceiverCi(PpoObject):
    receiverAddr = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                  presentation=IntPresentation())


class PpoLightSignalRi(PpoObject):
    addrKI_KO = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KPS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_S = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_RU = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_GM = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KMGS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_ZHZS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_ZS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    yellowCode = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                presentation=IntPresentation())


class PpoCodeEnablingRelayALS(PpoObject):
    addr = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    okv = AttributeAccessRulesDescriptor()


class PpoTrackEncodingPoint(PpoObject):
    encUnitALS = AttributeAccessRulesDescriptor()
    signalUnit = AttributeAccessRulesDescriptor()
    own = AttributeAccessRulesDescriptor(is_list=True)
    freeState = AttributeAccessRulesDescriptor(is_list=True)
    plusPoints = AttributeAccessRulesDescriptor(is_list=True)
    minusPoints = AttributeAccessRulesDescriptor(is_list=True)
    codeGenerationMode = AttributeAccessRulesDescriptor()
    codeGenerationDirection = AttributeAccessRulesDescriptor()


class PpoCodeGeneratorALS(PpoObject):
    addr = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                          presentation=IntPresentation())


class PpoGeneralPurposeRelayInput(PpoObject):
    inputAddr = AttributeAccessRulesDescriptor(is_list=True, attribute_management_group=AMG_ADR_KI)


class PpoGeneralPurposeRelayOutput(PpoObject):
    addrUI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    defaultValue = AttributeAccessRulesDescriptor(value_checkers=ValueZeroOneChecker())


class PpoGeneralPurposeRelayTranslator(PpoObject):
    SrcKI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    DstUI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)


class PpoSignalRelayRepeater(PpoObject):
    addrKI = AttributeAccessRulesDescriptor()
    KO = AttributeAccessRulesDescriptor()
    KPS = AttributeAccessRulesDescriptor()
    RU = AttributeAccessRulesDescriptor()
    GM = AttributeAccessRulesDescriptor()
    KMGS = AttributeAccessRulesDescriptor()
    ZHZS = AttributeAccessRulesDescriptor()
    ZS = AttributeAccessRulesDescriptor()
    ZK = AttributeAccessRulesDescriptor()


class PpoTrackRelayRepeater(PpoObject):
    trackReceivers = AttributeAccessRulesDescriptor(is_list=True)
    longFreeTime = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                  presentation=IntPresentation())
    AddrMUI = AttributeAccessRulesDescriptor()


class PpoGeneralPurposeGroupRelayInput(PpoObject):
    inputAddr = AttributeAccessRulesDescriptor(is_list=True)


class PpoElectricHeating(PpoObject4i):
    pass


class PpoElectricHeatingRi(PpoObject):
    addrKI_KEO = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_KI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    output_VO = AttributeAccessRulesDescriptor(value_checkers=ValueElectricHeatingOnOffChecker())
    output_OO = AttributeAccessRulesDescriptor(value_checkers=ValueElectricHeatingOnOffChecker())


class TrafficOperatorWorkset(PpoObject2i):
    num = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                         presentation=IntPresentation())
    controlArea = AttributeAccessRulesDescriptor(is_list=True, value_checkers=ValueInSetChecker())
    commonRemoteCommands = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("commonRemoteCommands1"))
    confirmedRemoteCommands = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("confirmedRemoteCommands1"))
    key = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0xFFFFFFFFFFFFFFFFULL"))


class StationOperatorWorkset(PpoObject):
    num = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                         presentation=IntPresentation())
    id_ = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                            presentation=IfZeroThenIntPresentation())
    controlArea = AttributeAccessRulesDescriptor(is_list=True, value_checkers=ValueInSetChecker())


class ControlArea(PpoObject2i):
    initialOperatorNum = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                        presentation=IntPresentation())


class PpoTrackCrossroad(PpoObject3i):
    id_ = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                            presentation=IfZeroThenIntPresentation())
    iObjTag = AttributeAccessRulesDescriptor()
    railCrossing = AttributeAccessRulesDescriptor()


class PpoTrainNotificationRi(PpoObject):
    NPI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    CHPI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)


class PpoRailCrossingRi(PpoObject):
    NCHPI = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    KP_O = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    KP_A = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    ZG = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    KZP = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)


class PpoRailCrossing(PpoObject4i):
    crossroad = AttributeAccessRulesDescriptor(is_list=True)


class PpoGroupRailFittersWarningArea(PpoObject):
    pass


class PpoRailFittersWarningAreaRi(PpoObject):
    AddrMKI_KNM = AttributeAccessRulesDescriptor()
    AddrMUI_RRM = AttributeAccessRulesDescriptor()
    AddrMUI_OM = AttributeAccessRulesDescriptor()


class PpoRailFittersWarningArea(PpoObject4i):
    group = AttributeAccessRulesDescriptor()
    points = AttributeAccessRulesDescriptor(is_list=True)


class PpoInterstationWayCrossroad(PpoObject4i):
    id_ = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                         presentation=IfZeroThenIntPresentation())
    indent = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("0"),
                                            presentation=IfZeroThenIntPresentation())
    timeBlocking3U = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                    presentation=IntPresentation())
    timeBlocking4U = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                    presentation=IntPresentation())
    timeOccupancy2U = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                     presentation=IntPresentation())
    timeOccupancy3U = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                     presentation=IntPresentation())
    timeOccupancy4U = AttributeAccessRulesDescriptor(value_checkers=ValueStrIsPositiveNumberChecker(),
                                                     presentation=IntPresentation())
    _2U = AttributeAccessRulesDescriptor()
    _3U = AttributeAccessRulesDescriptor()
    _4UD = AttributeAccessRulesDescriptor()
    _4U = AttributeAccessRulesDescriptor(is_list=True)
    _4UB = AttributeAccessRulesDescriptor(is_list=True)


class PpoCabinetUsoBk(PpoObject):
    lightSignals = AttributeAccessRulesDescriptor(is_list=True)
    hiCratePointMachines = AttributeAccessRulesDescriptor(is_list=True)
    loCratePointMachines = AttributeAccessRulesDescriptor(is_list=True)
    controlDeviceDerailmentStocks = AttributeAccessRulesDescriptor(is_list=True)


class PpoInsulationResistanceMonitoring(PpoObject):
    cabinets = AttributeAccessRulesDescriptor(is_list=True)
    addrKI_OK = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)


class PpoPointMachinesCurrentMonitoring(PpoObject):
    cabinets = AttributeAccessRulesDescriptor(is_list=True)
    addrKI_KTPS = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)


class PpoTelesignalization(PpoObject4i):
    pass


class PpoPointsMonitoring(PpoObject3i):
    pass


class PpoLightModeRi(PpoObject):
    addrKI_DN1 = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_DN2 = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrKI_DSN = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_KI)
    addrUI_DN = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_DSN = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)
    addrUI_ASV = AttributeAccessRulesDescriptor(attribute_management_group=AMG_ADR_UI)


class PpoLightMode(PpoObject4i):
    pass


class PpoFireAndSecurityAlarm(PpoObject4i):
    pass


class PpoDieselGenerator(PpoObject3i):
    dieselControl = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("KT"))
    startDieselGenerator = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("ZDGA"))
    stopDieselGenerator = AttributeAccessRulesDescriptor(value_suggester=ConstSuggester("ODGA"))


class PpoEncodingUnitsMonitoring(PpoObject):
    generators = AttributeAccessRulesDescriptor(is_list=True)


class PpoTrackSensorsMonitoring(PpoObject):
    receivers = AttributeAccessRulesDescriptor(is_list=True)


class PpoIndicationGroupTrackSensors(PpoObject4i):
    pass
