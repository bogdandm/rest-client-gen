from inspect import isclass
from typing import Callable, List, Tuple

from .base import GenericModelCodeGenerator, KWAGRS_TEMPLATE, METADATA_FIELD_NAME, sort_kwargs, template
from ..dynamic_typing import DDict, DList, DOptional, ImportPathList, MetaData, ModelMeta, StringSerializable

DEFAULT_ORDER = (
    ("default", "default_factory"),
    "*",
    ("metadata",)
)


def dataclass_post_init_converters(str_fields: List[str]):
    """
    Method factory. Return post_init method to convert string into StringSerializable types
    To override generated __post_init__ you can call it directly:

    >>> def __post_init__(self):
    ...     dataclass_post_init_converters(['a', 'b'])(self)

    :param str_fields: names of StringSerializable fields
    :return: __post_init__ method
    """

    def __post_init__(self):
        for name in (str_fields):
            t = self.__annotations__[name]
            setattr(self, name, t.to_internal_value(getattr(self, name)))

    return __post_init__


def convert_strings(str_fields: List[str]) -> Callable[[type], type]:
    """
    Decorator factory. Set up `__post_init__` method to convert strings fields values into StringSerializable types

    :param str_fields: names of StringSerializable fields
    :return: Class decorator
    """

    def decorator(cls: type) -> type:
        if hasattr(cls, '__post_init__'):
            old_fn = cls.__post_init__

            def __post_init__(self, *args, **kwargs):
                dataclass_post_init_converters(str_fields)(self)
                old_fn(self, *args, **kwargs)

            setattr(cls, '__post_init__', __post_init__)
        else:
            setattr(cls, '__post_init__', dataclass_post_init_converters(str_fields))

        return cls

    return decorator


class DataclassModelCodeGenerator(GenericModelCodeGenerator):
    DC_DECORATOR = template(f"dataclass{{% if kwargs %}}({KWAGRS_TEMPLATE}){{% endif %}}")
    DC_CONVERT_DECORATOR = template("convert_strings({{ str_fields }})")
    DC_FIELD = template(f"field({KWAGRS_TEMPLATE})")

    def __init__(self, model: ModelMeta, meta=False, post_init_converters=False, dataclass_kwargs: dict = None,
                 **kwargs):
        """
        :param model: ModelMeta instance
        :param meta: Enable generation of metadata as attrib argument
        :param post_init_converters: Enable generation of type converters in __post_init__ methods
        :param dataclass_kwargs: kwargs for @dataclass() decorators
        :param kwargs:
        """
        super().__init__(model, **kwargs)
        self.post_init_converters = post_init_converters
        self.no_meta = not meta
        self.dataclass_kwargs = dataclass_kwargs or {}

    @property
    def decorators(self) -> Tuple[ImportPathList, List[str]]:
        imports = [('dataclasses', ['dataclass', 'field'])]
        decorators = [self.DC_DECORATOR.render(kwargs=self.dataclass_kwargs)]

        if self.post_init_converters:
            str_fields = [self.convert_field_name(name) for name, t in self.model.type.items()
                          if isclass(t) and issubclass(t, StringSerializable)]
            if str_fields:
                imports.append(('json_to_models.models.dataclasses', ['convert_strings']))
                decorators.append(self.DC_CONVERT_DECORATOR.render(str_fields=str_fields))

        return imports, decorators

    def field_data(self, name: str, meta: MetaData, optional: bool) -> Tuple[ImportPathList, dict]:
        """
        Form field data for template

        :param name: Original field name
        :param meta: Field metadata
        :param optional: Is field optional
        :return: imports, field data
        """
        imports, data = super().field_data(name, meta, optional)
        body_kwargs = {}
        if optional:
            meta: DOptional
            if isinstance(meta.type, DList):
                body_kwargs["default_factory"] = "list"
            elif isinstance(meta.type, DDict):
                body_kwargs["default_factory"] = "dict"
            else:
                body_kwargs["default"] = "None"
                if isclass(meta.type) and issubclass(meta.type, StringSerializable):
                    pass
        elif isclass(meta) and issubclass(meta, StringSerializable):
            pass

        if not self.no_meta and name != data["name"]:
            body_kwargs["metadata"] = {METADATA_FIELD_NAME: name}
        if len(body_kwargs) == 1 and next(iter(body_kwargs.keys())) == "default":
            data["body"] = body_kwargs["default"]
        elif body_kwargs:
            data["body"] = self.DC_FIELD.render(kwargs=sort_kwargs(body_kwargs, DEFAULT_ORDER))
        return imports, data
