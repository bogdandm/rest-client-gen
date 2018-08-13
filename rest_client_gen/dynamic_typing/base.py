from typing import Any, Union


class BaseType:
    def to_static_type(self) -> type:
        raise NotImplementedError()


class UnknownType(BaseType):
    __slots__ = []

    def __str__(self):
        return "Unknown"

    def to_static_type(self):
        return Any


Unknown = UnknownType()
NoneType = type(None)


class SingleType(BaseType):
    __slots__ = ["type"]

    def __init__(self, t: Union[type, BaseType]):
        self.type = t

    def __str__(self):
        return f"{self.__class__.__name__}[{self.type}]"

    def __repr__(self):
        return f"<{self.__class__.__name__} [{self.type}]>"

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.type == other.type


class ComplexType(BaseType):
    __slots__ = ["types"]

    def __init__(self, *types: Union[type, BaseType]):
        self.types = types

    def __str__(self):
        items = ', '.join(map(str, self.types))
        return f"{self.__class__.__name__}[{items}]"

    def __repr__(self):
        items = ', '.join(map(str, self.types))
        return f"<{self.__class__.__name__} [{items}]>"

    def _sort_key(self, item):
        if isinstance(item, dict):
            return f"Dict#{sorted(item.keys())}"
        else:
            return str(item)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and all(t1 == t2 for t1, t2 in zip(
            sorted(self.types, key=self._sort_key), sorted(other.types, key=self._sort_key)
        ))

    def __len__(self):
        return len(self.types)