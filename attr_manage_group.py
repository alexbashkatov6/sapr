from descr_value_checkers import ValueChecker, ValueAddressKIChecker, ValueAddressUIChecker
from descr_value_suggesters import Suggester, AddressSuggester
from descr_value_presentation import Presentation, AddressPresentation


class AttributeManagementGroup:
    def __init__(self, value_checker: ValueChecker, value_suggester: Suggester, presentation: Presentation):
        self.value_checker = value_checker
        self.value_suggester = value_suggester
        self.presentation = presentation


AMG_ADR_UI = AttributeManagementGroup(value_checker=ValueAddressUIChecker(),
                                      value_suggester=AddressSuggester(),
                                      presentation=AddressPresentation())

AMG_ADR_KI = AttributeManagementGroup(value_checker=ValueAddressKIChecker(),
                                      value_suggester=AddressSuggester(),
                                      presentation=AddressPresentation())
