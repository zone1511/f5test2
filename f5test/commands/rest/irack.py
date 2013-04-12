'''
Created on Mar 6, 2013

@author: jono
'''
from .base import RestCommand
from ...base import Options
import logging
import time
import yaml

LOG = logging.getLogger(__name__)


pick_best_harness = None
class PickBestHarness(RestCommand):
    """Given a list of harness definition files, pick the one that's the most "available".
    Assumes files are in YAML format.

    @rtype: dict
    """
    def __init__(self, files, *args, **kwargs):
        super(PickBestHarness, self).__init__(*args, **kwargs)
        self.files = files

    def setup(self):
        mapping = Options()
        for yaml_file in self.files:
            mapping[yaml_file] = yaml.load(open(yaml_file).read())

        rmapping = dict((b['address'], k) for k, v in mapping.iteritems()
                                          for _, b in v['devices'].iteritems())

        ret = self.ifc.api.f5asset.filter(v_accessaddress__in=rmapping.keys())

        # The harnesses with the lowest due_date are preferred.
        highest_due = {}
        for f5asset in ret.data.objects:
            yaml_file = rmapping[f5asset['v_accessaddress']]
            timestamp = time.mktime(time.strptime(f5asset['v_due_on'],
                                                  '%Y-%m-%dT%H:%M:%S')) \
                        if f5asset['v_due_on'] else 0
            highest_due[yaml_file] = max(highest_due.get(yaml_file, 0), timestamp)

        LOG.debug(highest_due)
        best_yaml_file = min(highest_due, key=lambda x: highest_due[x])
        return Options(mapping[best_yaml_file])
