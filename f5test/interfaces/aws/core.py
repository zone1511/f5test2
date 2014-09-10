"""Interface to Amazon's services based on boto"""

from ...base import Interface
import logging
from ...base import enum
import importlib


LOG = logging.getLogger(__name__)
MODULE = enum(EC2='ec2', VPC='vpc', S3='s3', GLACIER='glacier')


class AwsError(Exception):
    pass


class AwsInterface(Interface):
    """
    Generic wrapper around boto package.

    @param region: AWS region
    @param key_id: Amazon API ID
    @param access_key: Amazon access key
    @param module: boto API modules. Supported modules listed in the MODULE enum.
    """
    def __init__(self, region, key_id, access_key, module=MODULE.EC2,
                 *args, **kwargs):
        super(AwsInterface, self).__init__()

        self.region = region
        self.key_id = key_id
        self.access_key = access_key
        self.module = module
        self.aws = importlib.import_module('boto.%s' % self.module)

    def __repr__(self):
        name = self.__class__.__name__
        return "<{0}: {1.key_id}:{1.access_key}@{1.region}>".format(name, self)

    @property
    def regions(self):
        return self.aws.regions()

    def open(self):  # @ReservedAssignment
        """
        Returns a handle to boto.XYZ.connect_to_region(...)
        """
        if self.api:
            return self.api

        self.api = self.aws.connect_to_region(self.region,
                                         aws_access_key_id=self.key_id,
                                         aws_secret_access_key=self.access_key)
        return self.api
