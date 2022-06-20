from typing import Optional, Any

from attribute_management import NamedAttribute, AttributeAddress, SingleAttribute, ListAttribute, UnaryAttribute, \
    ComplexAttributeManagementCommand, AttributeCommand, AttributeIndex, StrSingleAttribute


class NotValidIndexException(Exception):
    pass


def cyclic_find(start_object, attr_address: AttributeAddress, find_single_attribute: bool = False) -> \
        tuple[NamedAttribute, Optional[SingleAttribute], Any, AttributeAddress]:
    """ returns last NamedAttribute and SingleAttribute in address """
    ail = attr_address.attribute_index_list
    for i, attr_index in enumerate(ail):
        slice_attr_addr = attr_address.get_end_slice(attr_index)
        attr_name, index = attr_index.attr_name, attr_index.index
        cycle_named_attr = getattr(start_object, attr_name)
        if (len(ail) - 1 == i) and not find_single_attribute:
            single_attrib = None
            break
        if isinstance(cycle_named_attr, ListAttribute):
            try:
                single_attrib = cycle_named_attr.single_attribute_list[index]
            except IndexError:
                return cycle_named_attr, None, start_object, slice_attr_addr
        elif isinstance(cycle_named_attr, UnaryAttribute):
            single_attrib = cycle_named_attr.single_attribute
        else:
            assert False
        if cycle_named_attr.single_attribute_type is str:
            assert len(ail) - 1 == i
        else:
            start_object = single_attrib.obj
    return cycle_named_attr, single_attrib, start_object, slice_attr_addr


def set_str_attr(obj, value: str, attr_address: AttributeAddress):
    attr_name: str = attr_address.attribute_index_list[0].attr_name
    setattr(obj, attr_name, ComplexAttributeManagementCommand(AttributeCommand.set_single,
                                                              attr_address,
                                                              value))


def get_str_attr(obj, attr_address: AttributeAddress):
    named_attr, str_single_attr, _, _ = cyclic_find(obj, attr_address, True)
    return str_single_attr.displaying_value


class AttributeDependence:
    def __init__(self):
        self.base_attr_name = ""
        self.dependent_attr_name = ""
        self.func = lambda x: x

    def set_translation_function(self, func):
        self.func = func

    def translation_function_result(self, instance) -> str:
        attr_value = get_str_attr(instance, AttributeAddress([AttributeIndex(self.base_attr_name, 0)]))
        return self.func(attr_value)

    def eval_as_possible_value(self, instance):
        result = self.translation_function_result(instance)
        named_attr, str_single_attr, _, _ = cyclic_find(instance, AttributeAddress([AttributeIndex(self.dependent_attr_name, 0)]), True)
