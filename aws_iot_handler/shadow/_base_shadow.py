from abc import ABC, abstractmethod
from copy import deepcopy


class _BaseShadow(ABC):
    def __init__(self, thing_name):
        self.__thing_name = thing_name
        self._full_state = dict()
        self._meta = dict()

        self._update_timestamp = int()
        self._version = int()

    @property
    def thing_name(self) -> str:
        return self.__thing_name

    @property
    def update_timestamp(self) -> int:
        return self._update_timestamp

    @property
    def shadow_version(self) -> int:
        return self._version

    def _get_property_of_state(self, prop):
        return deepcopy(self._full_state.pop(prop, dict()))

    @property
    def state(self) -> dict:
        return deepcopy(self._full_state)

    @state.deleter
    @abstractmethod
    def state(self):
        pass

    @property
    def reported(self):
        return self._get_property_of_state("reported")

    @property
    def desired(self):
        return self._get_property_of_state("desired")

    @property
    def delta(self):
        return self._get_property_of_state("delta")

    @property
    def meta(self):
        return deepcopy(self._meta)
