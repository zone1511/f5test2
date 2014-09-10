from .. import base


class EC2Command(base.AWSCommand):

    def __init__(self, *args, **kwargs):
        super(EC2Command, self).__init__(*args, **kwargs)
