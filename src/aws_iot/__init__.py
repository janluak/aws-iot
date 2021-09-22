__version__ = "0.2.4"


class _BaseIoT:
    def __init__(self, thing_name, *args):
        self.__thing_name = thing_name

    @property
    def thing_name(self) -> str:
        return self.__thing_name



