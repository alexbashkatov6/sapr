from typing import Any

from config import DEFAULT_ADDRESS_SUGGESTION


class Presentation:
    def convert(self, val: str) -> Any:
        return val


class IntPresentation(Presentation):
    def convert(self, val: str) -> Any:
        if val and val.isdigit():
            return int(val)
        return None


class IfZeroThenIntPresentation(Presentation):
    def convert(self, val: str) -> Any:
        if val.strip() == "0":
            return 0
        return val


class AddressPresentation(Presentation):
    def convert(self, val: str) -> Any:
        if val.strip() == DEFAULT_ADDRESS_SUGGESTION:
            return None
        return val


DEFAULT_PRESENTATION = Presentation()
