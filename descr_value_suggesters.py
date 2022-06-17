from typing import Any

from attribute_management import AttributeAddress, AttributeIndex
from attribute_address_access import get_str_attr


class Suggester:
    def __init__(self):
        self._possible_values = list()

    def suggest(self, *args, **kwargs) -> str:
        pass

    @property
    def possible_values(self) -> list:
        return self._possible_values

    def eval_possible_values(self, *args, **kwargs) -> None:
        pass


class ConstSuggester(Suggester):
    def __init__(self, const_value: str):
        super().__init__()
        self.const_value = const_value

    def suggest(self) -> str:
        return self.const_value

    def eval_possible_values(self, *args, **kwargs):
        self._possible_values.clear()
        self._possible_values.append(self.const_value)


class InterstationDirectiveSuggester(Suggester):
    attr_dependencies = {}  # {"output_DSO": "tag", ...}

    def __init__(self, attr_name: str):
        super().__init__()
        self.attr_name = attr_name
        self._descr_name = "_"

    @property
    def descr_name(self):
        return self._descr_name

    @descr_name.setter
    def descr_name(self, val):
        self._descr_name = val

    def suggest(self, instance) -> str:
        tag = get_str_attr(instance, AttributeAddress([AttributeIndex(self.attr_name, 0)]))
        result = "{}_{}".format(self.descr_name.split("_")[1], tag.split("_")[0])
        return result

    def eval_possible_values(self, instance) -> None:
        self._possible_values.clear()
        self._possible_values.append("NoAddr")
        self._possible_values.append(self.suggest(instance))


class EqualOtherAttributeSuggester(Suggester):
    attr_dependencies = {}  # {"id_": "tag", ...}

    def __init__(self, attr_name: str):
        super().__init__()
        self.attr_name = attr_name

    def suggest(self, instance):
        return get_str_attr(instance, AttributeAddress([AttributeIndex(self.attr_name, 0)]))

    def eval_possible_values(self, instance) -> None:
        self._possible_values.clear()
        self._possible_values.append(self.suggest(instance))


class AddressSuggester(Suggester):

    def __init__(self):
        super().__init__()
        self._possible_values = ["USO:::", "CPU:::", "PPO:::"]

    def suggest(self):
        return "USO:::"


DEFAULT_VALUE_SUGGESTER = Suggester()
