from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field

T = TypeVar("T")


@dataclass
class UIValue:
    """Holds the configuration and current value of a UI element"""

    type: str
    value: Any
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: List[Any] = field(default_factory=list)
    callbacks: List[Callable] = field(default_factory=list)
    order: int = 0
    name: str = ""


class UIProperty:
    """Descriptor for UI properties with callback support"""

    _counter = 0

    def __init__(
        self,
        type: str,
        default: Any,
        label: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        options: Optional[List[Any]] = None,
    ):
        self.type = type
        self.default = default
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.options = options
        self._order = UIProperty._counter
        UIProperty._counter += 1
        self._callbacks = []  # ← store callbacks at the descriptor level

    def __set_name__(self, owner: Type, name: str):
        self.name = name
        self.label = self.label or name.replace("_", " ").title()

    def __get__(self, obj: Any, objtype: Type = None) -> Any:
        if obj is None:
            return self
        if not hasattr(obj, "_ui_values"):
            obj._ui_values = {}
        if self.name not in obj._ui_values:
            obj._ui_values[self.name] = UIValue(
                type=self.type,
                value=self.default,
                label=self.label,
                min_value=self.min_value,
                max_value=self.max_value,
                options=self.options or [],
                order=self._order,
                name=self.name,
                callbacks=self._callbacks.copy(),  # ← assign callbacks here
            )
        return obj._ui_values[self.name].value

    def __set__(self, obj: Any, value: Any):
        if not hasattr(obj, "_ui_values"):
            obj._ui_values = {}
        ui_value = obj._ui_values.get(self.name)
        if ui_value is None:
            ui_value = UIValue(
                type=self.type,
                value=value,
                label=self.label,
                min_value=self.min_value,
                max_value=self.max_value,
                options=self.options or [],
                order=self._order,
                name=self.name,
                callbacks=self._callbacks.copy(),  # ← assign callbacks here
            )
            obj._ui_values[self.name] = ui_value
        else:
            ui_value.value = value
        # print(self.name, ui_value.value, ui_value.callbacks)
        for callback in ui_value.callbacks:
            callback(obj, self.name, value)

    def callback(self, func: Callable) -> Callable:
        """Decorator to register a callback for value changes"""
        self._callbacks.append(func)
        return func


class UI:
    """Factory for creating UI properties"""

    @staticmethod
    def int(
        default: int = 0, min: int = None, max: int = None, label: str = None
    ) -> UIProperty:
        return UIProperty("int", default, label, min, max)

    @staticmethod
    def float(
        default: float = 0.0, min: float = None, max: float = None, label: str = None
    ) -> UIProperty:
        return UIProperty("float", default, label, min, max)

    @staticmethod
    def bool(default: bool = False, label: str = None) -> UIProperty:
        return UIProperty("bool", default, label)

    @staticmethod
    def select(
        default: Any,
        options: List[Any],
        label: str = None,
    ) -> UIProperty:
        return UIProperty("select", default or options[0], label, options=options)

    @staticmethod
    def button(label: str, callback: Callable = None) -> UIProperty:
        prop = UIProperty("button", None, label)
        if callback:
            prop.callback(callback)
        return prop
