from typing import Any, Iterable
import re


class ValueChecker:

    def check_value(self, value: Any) -> str:
        pass


class ValueInSetChecker(ValueChecker):
    def __init__(self, storages: Iterable[Any] = None):
        if storages is None:
            self.storages = set()
        else:
            self.storages = storages

    @property
    def storages(self):  #  -> set
        return self._storages

    @storages.setter
    def storages(self, val: Iterable):
        assert isinstance(val, Iterable)
        self._storages = val  # set(val)

    @property
    def possible_values(self) -> set[Any]:
        result = set()
        if not self.storages:
            return result
        for storage in self.storages:
            if isinstance(storage, str):
                result.add(storage)
            else:
                result |= set(storage)
        return result

    def check_value(self, value: Any) -> str:
        if not self.storages:
            return ""
        if isinstance(value, str):
            value = value.strip()
        print("possible_values", self.possible_values)
        if value in self.possible_values:
            return ""
        else:
            return "Value is not in set of possible values"


class ValueStrIsNonNegNumberChecker(ValueChecker):

    def check_value(self, value: str) -> str:
        if value.isdigit():
            return ""
        else:
            return "Value is not non-negative integer"


class ValueStrIsPositiveNumberChecker(ValueChecker):

    def check_value(self, value: str) -> str:
        if value.isdigit() and (int(value) != 0):
            return ""
        else:
            return "Value is not positive integer"


class ValueZeroOneChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["0", "1"])


class ValueYesNoChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["Yes", "No"])


class ValuePlusMinusChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["+", "-"])


class ValueTimeAutoReturnChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["60", "180"])


class ValueABInvitSignalOpeningBeforeChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["true", "false"])


class ValuePABInvitSignalOpeningBeforeChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["false"])


class ValueElectricHeatingOnOffChecker(ValueInSetChecker):
    def __init__(self):
        super().__init__(["ElectricHeatingOn", "ElectricHeatingOff"])


class ValueAddressChecker(ValueChecker):

    def check_value(self, value: str) -> str:
        template = r"(?:USO|CPU|PPO)(?::\d{1,2}){2,3}"
        if re.fullmatch(template, value):
            return ""
        else:
            return "Address should be in format USO/CPU/PPO : NN : NN : NN"
        # RE-SOLUTION: r"(?:USO|CPU|PPO)(?::\d{1,2}){2,3}"
        # if value.isdigit() and (int(value) != 0):
        #     return ""
        # else:
        #     return "Value is not positive integer"


class ValueAddressUIChecker(ValueAddressChecker):
    def __init__(self):
        pass


class ValueAddressKIChecker(ValueAddressChecker):
    def __init__(self):
        pass


DEFAULT_VALUE_CHECKER = ValueChecker()
