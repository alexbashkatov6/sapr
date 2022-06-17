from typing import Any


class Presentation:
    def is_empty(self, val: str) -> bool:
        pass

    def convert(self, val: str) -> Any:
        return val


class SpacePresentation(Presentation):
    pass


class IntPresentation(Presentation):
    pass


class AddressPresentation(Presentation):
    pass


DEFAULT_PRESENTATION = Presentation()
