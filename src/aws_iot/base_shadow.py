from abc import ABC, abstractmethod
from copy import deepcopy


class BaseShadow(ABC):
    def __init__(self):
        self._full_state = dict()
        self._meta = dict()

        self._update_timestamp = int()
        self._version = int()

    @property
    def update_timestamp(self) -> int:
        return self._update_timestamp

    @property
    def shadow_version(self) -> int:
        return self._version

    def _get_property_of_state(self, prop) -> dict:
        return deepcopy(self._full_state.get(prop, dict()))

    @property
    def state(self) -> dict:
        return deepcopy(self._full_state)

    @state.deleter
    @abstractmethod
    def state(self):
        pass

    @property
    def reported(self) -> dict:
        return self._get_property_of_state("reported")

    @property
    def desired(self) -> dict:
        return self._get_property_of_state("desired")

    @property
    def delta(self) -> dict:
        return self._get_property_of_state("delta")

    @property
    def meta(self) -> dict:
        return deepcopy(self._meta)
