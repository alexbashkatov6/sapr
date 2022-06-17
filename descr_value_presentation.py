from typing import Any


class Presentation:
    def convert(self, val: str) -> Any:
        return val


class IntPresentation(Presentation):
    def convert(self, val: str) -> Any:
        if val and val.isdigit():
            return int(val)
        return None


class AddressPresentation(Presentation):
    pass


DEFAULT_PRESENTATION = Presentation()
