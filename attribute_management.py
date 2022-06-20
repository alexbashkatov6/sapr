from __future__ import annotations

from abc import abstractmethod, ABC
from copy import copy
from dataclasses import dataclass, field
from typing import Any, Iterable, Union, Type, Optional

from custom_enum import CustomEnum
from config import SINGLE_ATTRIBUTE_PROPERTIES, NAMED_ATTRIBUTE_PROPERTIES, ADDRESS, PROPERTIES, INTERNAL_STRUCTURE
from file_object_conversions import attr_name_from_object_to_file


class AttributeCommand(CustomEnum):
    set_single = 0
    append = 1
    remove = 2


class AttributeIndex:
    def __init__(self, attr_name: str = "", index: int = 0):
        self.attr_name: str = attr_name
        self.index: int = index

    def to_list(self):
        return [f'{self.attr_name}', self.index]


class AttributeAddress:
    def __init__(self, attribute_index_list: list[AttributeIndex] = None):
        self.attribute_index_list = attribute_index_list or []

    def get_first_attr_name(self) -> str:
        return self.attribute_index_list[0].attr_name

    def expand(self, ai: AttributeIndex) -> AttributeAddress:
        return AttributeAddress(self.attribute_index_list + [ai])

    def get_end_slice(self, ai: AttributeIndex) -> AttributeAddress:
        result_list = []
        append = False
        for attr_ind in self.attribute_index_list:
            if attr_ind == ai:
                append = True
            if append:
                result_list.append(attr_ind)
        return AttributeAddress(result_list)

    def specify_num_of_last(self, num: int) -> AttributeAddress:
        new_ail = copy(self.attribute_index_list)
        last_ai = new_ail.pop()
        new_ail.append(AttributeIndex(last_ai.attr_name, num))
        return AttributeAddress(new_ail)

    def to_list(self):
        return [ai.to_list() for ai in self.attribute_index_list]

    @staticmethod
    def from_list(laa: list[list[str, int]]) -> AttributeAddress:
        aa = AttributeAddress()
        for attr_index in laa:
            ai = AttributeIndex(*attr_index)
            aa.attribute_index_list.append(ai)
        return aa


@dataclass
class ComplexAttributeManagementCommand:
    command: AttributeCommand
    attrib_address: AttributeAddress
    value: Any = None


class AddressedAttribute(ABC):
    def __init__(self, attr_addr: AttributeAddress = None):
        self.address = attr_addr

    @abstractmethod
    def file_representation(self) -> dict:
        pass

    @abstractmethod
    def attr_exchange_representation(self) -> dict:
        pass


class NamedAttribute(AddressedAttribute):
    def __init__(self, attr_addr: AttributeAddress = None, single_attribute_type: Type = str, min_count: int = 0):
        super().__init__(attr_addr)
        self.single_attribute_type = single_attribute_type
        self.min_count = min_count
        # self.is_empty = True

    @abstractmethod
    def file_representation(self) -> dict:
        pass

    @abstractmethod
    def attr_exchange_representation(self) -> dict:
        pass

    def init_single_attr(self, addr) -> SingleAttribute:
        return StrSingleAttribute(addr) if issubclass(self.single_attribute_type, str) \
            else ObjSingleAttribute(addr, self.single_attribute_type(obj_addr=addr))


class UnaryAttribute(NamedAttribute):
    def __init__(self, attr_addr: AttributeAddress = None, single_attribute_type: Type = str, min_count: int = 0):
        super().__init__(attr_addr, single_attribute_type, min_count)
        self.single_attribute = None

    @property
    def is_required(self):
        return not self.min_count

    @property
    def file_representation(self) -> Optional[dict]:
        return self.single_attribute.file_representation

    @property
    def attr_exchange_representation(self) -> dict:
        return {
            NAMED_ATTRIBUTE_PROPERTIES:
                {"address": self.address.to_list(),
                 "is_list": False,
                 "obj_type": self.single_attribute_type.__name__},
            SINGLE_ATTRIBUTE_PROPERTIES:
                self.single_attribute.attr_exchange_representation
        }

    def append_new_sa(self) -> SingleAttribute:
        new_sa_addr = self.address.specify_num_of_last(0)
        sa = self.init_single_attr(new_sa_addr)
        self.single_attribute = sa
        return sa

    def remove_existing_sa(self, index: int):
        assert False


class ListAttribute(NamedAttribute):
    def __init__(self, attr_addr: AttributeAddress = None, single_attribute_type: Type = str, min_count: int = 0):
        super().__init__(attr_addr, single_attribute_type, min_count)
        self.single_attribute_list: list[SingleAttribute] = []

    @property
    def file_representation(self):
        result = [single_attribute.file_representation for single_attribute in self.single_attribute_list
                  if not (single_attribute.file_representation is None)]
        return result or None

    @property
    def attr_exchange_representation(self):
        return {
            NAMED_ATTRIBUTE_PROPERTIES:
                {"address": self.address.to_list(),
                 "is_list": True,
                 "obj_type": self.single_attribute_type.__name__},
            SINGLE_ATTRIBUTE_PROPERTIES:
                [single_attribute.attr_exchange_representation for single_attribute in self.single_attribute_list]
        }

    @property
    def sa_count(self):
        return len(self.single_attribute_list)

    def append_new_sa(self) -> SingleAttribute:
        new_sa_addr = self.address.specify_num_of_last(self.sa_count)
        sa = self.init_single_attr(new_sa_addr)
        self.single_attribute_list.append(sa)
        return sa

    def remove_existing_sa(self, index: int):
        for i in range(index+1, self.sa_count):
            sa = self.single_attribute_list[i]
            sa.address = sa.address.specify_num_of_last(i-1)
        self.single_attribute_list.pop(index)


class SingleAttribute(AddressedAttribute):
    def __init__(self, attr_addr: AttributeAddress = None):
        super().__init__(attr_addr)
        # self.is_empty = True

    @abstractmethod
    def file_representation(self) -> dict:
        pass

    @abstractmethod
    def attr_exchange_representation(self) -> dict:
        pass


class StrSingleAttribute(SingleAttribute):
    def __init__(self, attr_addr: AttributeAddress = None):
        super().__init__(attr_addr)
        self.displaying_value: str = ""
        self._suggested_value: str = ""
        self.last_input_value: str = ""
        self.needs_in_suggestion: bool = True
        self.is_suggested: bool = False
        self.is_required: bool = True
        self.error_message: str = ""
        self.possible_str_value_storages: Union[Iterable[str], Iterable[Iterable[str]]] = None
        self.file_value: Any = ""

    @property
    def suggested_value(self) -> str:
        return self._suggested_value

    @suggested_value.setter
    def suggested_value(self, value: str):
        if not value:
            return
        self._suggested_value = value
        self.is_suggested = True

    @property
    def possible_values(self) -> list[str]:
        possible_str_values = []
        if self.possible_str_value_storages:
            for storage in self.possible_str_value_storages:
                if isinstance(storage, Iterable) and not isinstance(storage, str):
                    for element in storage:
                        assert isinstance(element, str)
                        possible_str_values.append(element)
                elif isinstance(storage, str):
                    possible_str_values.append(storage)
        return possible_str_values

    @property
    def attr_exchange_dict(self) -> dict:
        attr_exch_dict = copy(self.__dict__)

        attr_exch_dict.pop("possible_str_value_storages")
        attr_exch_dict["possible_values"] = self.possible_values

        attr_exch_dict["address"] = self.address.to_list()
        return attr_exch_dict

    @property
    def file_representation(self):
        if self.file_value == "":
            return None
        return self.file_value  #  or None

    @property
    def attr_exchange_representation(self):
        return {
            ADDRESS:
                self.address.to_list(),
            PROPERTIES:
                self.attr_exchange_dict
        }


class ObjSingleAttribute(SingleAttribute):
    def __init__(self, attr_addr: AttributeAddress = None, obj: Any = None):  # PpoObject
        super().__init__(attr_addr)
        self.obj: Any = obj

    @property
    def file_representation(self):
        d = {}
        data_attr_names = self.obj.data_attr_names
        for data_attr_name in data_attr_names:
            na: NamedAttribute = getattr(self.obj, data_attr_name)
            file_representation = na.file_representation
            if not (file_representation is None):
                d[attr_name_from_object_to_file(data_attr_name)] = file_representation
        return d or None

    @property
    def attr_exchange_representation(self):
        d = {}
        data_attr_names = self.obj.data_attr_names
        for data_attr_name in data_attr_names:
            na: NamedAttribute = getattr(self.obj, data_attr_name)
            d[data_attr_name] = na.attr_exchange_representation
        return {
            ADDRESS:
                self.address.to_list(),
            INTERNAL_STRUCTURE:
                d
        }


if __name__ == "__main__":
    pai = NamedAttribute()
    sa = StrSingleAttribute()
    print(sa.__dict__)

    ai = AttributeIndex("lala", 0)
    print(ai.to_list())

    # aa = AttributeAddress([ai])
    # print(aa.to_list())

    aa = AttributeAddress.from_list([['notificationPoints', 0], ['point', 0]])
    print(aa.to_list())
