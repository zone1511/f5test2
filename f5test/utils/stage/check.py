'''
Created on Jan 28, 2015

@author: jwong
'''
from .base import Stage
from ...base import Options
from ...interfaces.config import ConfigInterface
from ...macros.check import ScaleCheck
import logging

LOG = logging.getLogger(__name__)


class ScaleCheckStage(Stage, ScaleCheck):
    """
    This stage is used for scale testing. It should run after the configure
    stage. It assumes the BIG-IP and BIG-IQ devices are already setup. It will:
    1) Delete restjavad log files and wipe storage on BIG-IP
    2) Re-license if BIG-IP is almost expired (within 5 days)
    3) Make sure default BIG-IQ can ping the discover address
    4) And 'bigstart restart' if BIG-IP is in a state other than 'Active' 
    """
    name = 'check'

    def __init__(self, device, specs, *args, **kwargs):
        configifc = ConfigInterface()
        biq_default = configifc.get_device()

        options = Options(device=device,
                          device_biq=biq_default,
                          timeout=specs.get('timeout'))

        super(ScaleCheckStage, self).__init__(options, *args, **kwargs)
