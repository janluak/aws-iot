from ._shadow import IoTShadowHandler
from ._job import IoTJobHandler


class IoTHandler(IoTShadowHandler, IoTJobHandler):
    def __init__(self, thing_name: str, *, account_id: str = None, endpoint_url: str = None):
        IoTShadowHandler.__init__(self, thing_name, endpoint_url=endpoint_url)
        IoTJobHandler.__init__(self, thing_name, account_id=account_id)
