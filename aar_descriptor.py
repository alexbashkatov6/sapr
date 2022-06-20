from typing import Any, Union, Optional, Iterable

from attribute_management import NamedAttribute, AttributeAddress, SingleAttribute, ComplexAttributeManagementCommand, \
    AttributeCommand, AttributeIndex, ListAttribute, UnaryAttribute, StrSingleAttribute
from descr_value_checkers import ValueChecker, DEFAULT_VALUE_CHECKER, ValueInSetChecker, \
    ValueStrIsPositiveNumberChecker, ValueAddressChecker
from descr_value_suggesters import Suggester, DEFAULT_VALUE_SUGGESTER, InterstationDirectiveSuggester, \
    EqualOtherAttributeSuggester, ConstSuggester, AddressSuggester
from descr_value_presentation import Presentation, DEFAULT_PRESENTATION
from attr_manage_group import AttributeManagementGroup
from attribute_address_access import cyclic_find, NotValidIndexException


class AttributeAccessRulesDescriptor:

    def __init__(self,
                 is_list: bool = False,
                 min_count: int = 0,
                 single_attribute_type: Any = str,
                 value_checkers: Union[ValueChecker, Iterable[ValueChecker]] = DEFAULT_VALUE_CHECKER,
                 value_suggester: Suggester = DEFAULT_VALUE_SUGGESTER,
                 presentation: Presentation = DEFAULT_PRESENTATION,
                 attribute_management_group: AttributeManagementGroup = None):
        self._value_checkers = []
        type_named_attr = ListAttribute if is_list else UnaryAttribute
        self.named_attribute_template = type_named_attr(min_count=min_count,
                                                        single_attribute_type=single_attribute_type)
        self.single_is_str = issubclass(single_attribute_type, str)
        if attribute_management_group:
            self.value_checkers = attribute_management_group.value_checker
            self.value_suggester = attribute_management_group.value_suggester
            self.presentation = attribute_management_group.presentation
        else:
            self.value_checkers = value_checkers
            self.value_suggester = value_suggester
            self.presentation = presentation

    @property
    def value_checkers(self):
        return self._value_checkers

    @value_checkers.setter
    def value_checkers(self, val):
        self._value_checkers = val
        if not isinstance(self._value_checkers, Iterable):
            self._value_checkers = [self._value_checkers]

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if not instance:
            return self
        if not hasattr(instance, "_{}".format(self.name)):
            self.init_attr_in_object(instance)
        self.value_suggester.eval_possible_values(instance)
        return getattr(instance, "_{}".format(self.name))

    def __set__(self, instance, command: ComplexAttributeManagementCommand):
        if not hasattr(instance, "_{}".format(self.name)):
            self.init_attr_in_object(instance)
        command_, attr_address, value = command.command, command.attrib_address, command.value
        if command_ == AttributeCommand.set_single:
            """ index is already exists """
            cycle_named_attr, single_attrib, obj, slice_address = cyclic_find(instance, attr_address, True)
            if not (obj is instance):
                setattr(obj, slice_address.get_first_attr_name(),
                        ComplexAttributeManagementCommand(command=command_, attrib_address=slice_address, value=value))
                return
            if not single_attrib:
                self.new_attr_operations(instance, cycle_named_attr)
                cycle_named_attr, single_attrib, obj, slice_address = cyclic_find(instance, attr_address, True)
            sa_type = cycle_named_attr.single_attribute_type
            if issubclass(sa_type, str):
                single_attrib: StrSingleAttribute
                single_attrib.last_input_value = value
                single_attrib.is_suggested = False
                single_attrib.error_message = ""
                if (not value) or value.isspace():
                    if single_attrib.needs_in_suggestion:
                        self.suggest(instance, single_attrib)
                    else:
                        single_attrib.displaying_value = ""
                        self.form_file_presentation(single_attrib)
                else:
                    single_attrib.displaying_value = single_attrib.last_input_value
                    self.form_file_presentation(single_attrib)
                    self.check_value(single_attrib, value)
                self.equal_others_suggesters_handling(instance)
                if not single_attrib.possible_str_value_storages:
                    self.possible_values_binding(single_attrib)
            else:
                assert False
            return
        else:
            cycle_named_attr, _, _, _ = cyclic_find(instance, attr_address)
        if command_ == AttributeCommand.append:
            assert isinstance(cycle_named_attr, ListAttribute)
            self.new_attr_operations(instance, cycle_named_attr)
        elif command_ == AttributeCommand.remove:
            assert isinstance(cycle_named_attr, ListAttribute)
            index = attr_address.attribute_index_list[-1].index
            cycle_named_attr.remove_existing_sa(index)
        else:
            assert False

    def form_file_presentation(self, single_attrib: StrSingleAttribute):
        single_attrib.file_value = self.presentation.convert(single_attrib.displaying_value)

    def init_attr_in_object(self, instance):
        instance_aa: AttributeAddress = instance.obj_addr
        ca_addr = instance_aa.expand(AttributeIndex(self.name, -1))
        named_attr = type(self.named_attribute_template)\
            (attr_addr=ca_addr,
             min_count=self.named_attribute_template.min_count,
             single_attribute_type=self.named_attribute_template.single_attribute_type)
        count_cycles = self.named_attribute_template.min_count
        if count_cycles == 0:
            count_cycles += 1  # temporary for test - displaying attribute existence
        for _ in range(count_cycles):
            self.new_attr_operations(instance, named_attr)
        setattr(instance, "_{}".format(self.name), named_attr)
        self.equal_others_suggesters_binding(self.value_suggester)

    def new_attr_operations(self, instance, named_attr):
        new_sa = named_attr.append_new_sa()
        if isinstance(new_sa, StrSingleAttribute):
            self.suggest(instance, new_sa)
        self.possible_values_binding(new_sa)

    def possible_values_binding(self, str_sa: StrSingleAttribute):
        storages = []
        for value_checker in self.value_checkers:
            if isinstance(value_checker, ValueInSetChecker):
                storages += list(value_checker.storages)
        sugg_poss_val = self.value_suggester.possible_values
        if isinstance(self.value_suggester, (EqualOtherAttributeSuggester, ConstSuggester, InterstationDirectiveSuggester, AddressSuggester)):
            storages.append(sugg_poss_val)
        str_sa.possible_str_value_storages = storages

    def equal_others_suggesters_binding(self, suggester: Suggester):
        for sugg_cls in {EqualOtherAttributeSuggester, InterstationDirectiveSuggester}:
            if isinstance(suggester, sugg_cls):
                common_sugg_dict = sugg_cls.attr_dependencies
                if self.name not in common_sugg_dict:
                    common_sugg_dict[self.name] = suggester.attr_name

    def equal_others_suggesters_handling(self, instance):
        """ only for not list attributes """
        for sugg_cls in {EqualOtherAttributeSuggester, InterstationDirectiveSuggester}:
            for key, value in sugg_cls.attr_dependencies.items():
                if value == self.name:
                    if hasattr(instance, key):
                        named_attr: UnaryAttribute = getattr(instance, key)
                        single_attr: StrSingleAttribute = named_attr.single_attribute
                        if single_attr.is_suggested:
                            single_attr.needs_in_suggestion = True
                            setattr(instance, key, ComplexAttributeManagementCommand(AttributeCommand.set_single,
                                                                                     single_attr.address,
                                                                                     ""))

    def suggest(self, instance, single_attrib: StrSingleAttribute):
        single_attrib.needs_in_suggestion = False
        if isinstance(self.value_suggester, ConstSuggester):
            single_attrib.displaying_value = single_attrib.suggested_value = self.value_suggester.suggest()
        elif isinstance(self.value_suggester, EqualOtherAttributeSuggester):
            single_attrib.displaying_value = single_attrib.suggested_value = self.value_suggester.suggest(instance)
        elif isinstance(self.value_suggester, InterstationDirectiveSuggester):
            self.value_suggester.descr_name = self.name
            single_attrib.displaying_value = single_attrib.suggested_value = self.value_suggester.suggest(instance)
        elif isinstance(self.value_suggester, AddressSuggester):
            single_attrib.displaying_value = single_attrib.suggested_value = self.value_suggester.suggest()
        self.form_file_presentation(single_attrib)

    def check_value(self, str_sa: StrSingleAttribute, value: Any):
        for value_checker in self.value_checkers:
            if isinstance(value_checker, ValueInSetChecker):
                str_sa.error_message = value_checker.check_value(value)
            elif isinstance(value_checker, ValueStrIsPositiveNumberChecker):
                str_sa.error_message = value_checker.check_value(value)
            elif isinstance(value_checker, ValueAddressChecker):
                str_sa.error_message = value_checker.check_value(value)


if __name__ == '__main__':
    # from attribute_management import AttributeIndex
    class A:
        a = AttributeAccessRulesDescriptor(is_list=True)


    class B:
        b = AttributeAccessRulesDescriptor(single_attribute_type=A, min_count=3)


    obj_A = A()
    obj_B = B()

    print(obj_A.a)
    print(obj_A.a.__dict__)

    print(obj_B.b)
    print(obj_B.b.__dict__)
    print(obj_B.b.single_attribute_list[0].obj.a)

    address = AttributeAddress(attribute_index_list=[AttributeIndex(attr_name="a"), AttributeIndex()])
    command_1 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.append),
                                                  attrib_address=address)  #
    command_2 = ComplexAttributeManagementCommand(command=AttributeCommand(AttributeCommand.set_single),
                                                  attrib_address=address, value="500")
    obj_B.b = command_1
    obj_B.b = command_2

    print(obj_B.b)
    print(obj_B.b.__dict__)
    print(obj_B.b.single_attribute_list[0].obj.a.single_attribute_list[0].last_input_value)
