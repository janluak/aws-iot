from abc import ABC
from pathlib import Path
from ._shadow import IoTShadowThing
from ._job import IoTJobThing


__all__ = ["IoTThing", "IoTShadowThing", "IoTJobThing"]


class IoTThing(IoTShadowThing, IoTJobThing, ABC):
    """
    Custom AWS thing taking care of the underlying functions used in AWS IoT
    """

    def __init__(
        self,
        thing_name: str,
        aws_region: str,
        endpoint: str,
        cert_path: (str, Path) = None,
        delete_shadow_on_init: bool = False,
    ):
        """
        Parameters
        ----------
        thing_name : str
            the name of the AWS thing
            needs to be identical to the name of an AWS thing as configured in the management console
        aws_region : str
            region of AWS thing management
        endpoint : str
            MQTT enpoint of the desired AWS account
        cert_path : str, Path
            directory of the certificates
        delete_shadow_on_init : bool
            if True: shadow is deleted on every new instantiation

        """
        IoTShadowThing.__init__(
            self, thing_name, aws_region, endpoint, cert_path, delete_shadow_on_init
        )
        IoTJobThing.__init__(self, thing_name, aws_region, endpoint, cert_path)
