import weakref
from typing import Any, NoReturn


class DependencyUnresolvedException(Exception):
    pass


class DependencyStubMeta(type):
    __slots__ = ()
    _instances = weakref.WeakValueDictionary()

    def __call__(cls, key: str) -> "DependencyStub":
        if key not in cls._instances:
            instance = super().__call__(key)
            cls._instances[key] = instance
        return cls._instances[key]


class DependencyStub(metaclass=DependencyStubMeta):
    __slots__ = ("key", "__weakref__")

    def __init__(self, key: str):
        self.key = key

    def __repr__(self) -> str:
        return f"DependencyStub(key={self.key} id={id(self):x})"

    def __hash__(self) -> int:
        return hash(
            (
                "dependency_stub",
                self.key,
            )
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DependencyStub):
            return NotImplemented

        return self.key == other.key

    def __call__(self) -> NoReturn:
        raise DependencyUnresolvedException(
            "DependencyStub should not be called. "
            f"You might haven't provided an actual value for dependency with a key={self.key}"
            f" to `FastAPI.dependency_overrides`. ",
        )
