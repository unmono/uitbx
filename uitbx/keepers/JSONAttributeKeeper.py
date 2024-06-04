import json
import os
from pathlib import Path
from typing import Callable, Iterable, Any

type CanBeFile = os.PathLike | str


def validate_file_path(file_path: CanBeFile) -> Path:
    file = Path(file_path)
    if not file.exists():
        if not file.parent.exists():
            raise FileNotFoundError(f'{file.parent} directory does not exist')
        path_to_check = file.parent
    else:
        path_to_check = file
    if os.access(path_to_check, os.R_OK) and os.access(path_to_check, os.W_OK):
        return file
    raise PermissionError(f'{path_to_check} is not readable or writable')


class JSONAttributeKeeper:
    """
    Saves object attributes in a JSON file and sets them back.
    Useful for keep values of some attributes between runs of application.
    By default, saves them in a preferences.json file in application's CWD.
    """

    # Map types to converter functions, that return json serializable values.
    converters: dict[type, Callable[[Any], Any]] = {
        os.PathLike: lambda p: str(Path(p).resolve()),
    }

    # If some attributes need to set in special ways, map their types to functions
    # that take: object to set attribute, name of attribute and value recovered
    # from json and set it in required way.
    setters: dict[type, Callable[[Any, str, Any], None]] = {
        os.PathLike: lambda obj, name, p: setattr(obj, name, Path(p)),
    }

    def __init__(
            self,
            obj: object,
            attrs: Iterable[str],
            file: CanBeFile = Path.cwd() / 'preferences.json',
    ):
        self.file = validate_file_path(file)
        self.obj = obj
        self.attrs = self._define_attrs(*attrs)

    def convert_attr(self, value: Any) -> str:
        """
        Method that converts special instances to json serializable values
        using provided converters.
        """
        for converter_type in self.converters:
            if isinstance(value, converter_type):
                return self.converters[converter_type](value)
        raise TypeError(
            f'{type(value)} is not a json serializable type by default and with provided converters'
        )

    def save(self) -> None:
        """
        Saves attributes in json file. Runs converter functions for unserializable types.
        """
        self.file.touch()
        with self.file.open(mode='w') as f:
            json.dump(self._attrs_to_save, f, default=self.convert_attr)

    def set_attr(self, name: str, value: Any) -> None:
        """
        Sets saved attribute values in object.
        Runs provided setters for special cases.
        """
        attr = getattr(self.obj, name)
        for setter_type in self.setters:
            if isinstance(attr, setter_type):
                self.setters[setter_type](self.obj, name, value)
                return
        setattr(self.obj, name, value)

    def setup(self) -> None:
        """
        Retrieves saved attributes from json file and sets them to object.
        """
        if not self.file.exists():
            return
        with self.file.open(mode='r') as f:
            saved_attrs = json.load(f)
        if not isinstance(saved_attrs, dict):
            raise TypeError(f'Unsupported structure of {self.file.name}')
        for attr_name, value in saved_attrs.items():
            if attr_name not in self.attrs:
                continue
            self.set_attr(attr_name, value)

    def _define_attrs(self, *args: str) -> tuple[str, ...]:
        """
        Checks provided arguments to be valid attribute names of the related object.
        """
        for arg in args:
            if not isinstance(arg, str):
                raise AttributeError('All attribute names have to be strings')
            if not hasattr(self.obj, arg):
                raise AttributeError(f'Object doesn\'t have attribute \'{arg}\'')
        return args

    @property
    def _attrs_to_save(self) -> dict:
        return {attr_name: getattr(self.obj, attr_name) for attr_name in self.attrs}
