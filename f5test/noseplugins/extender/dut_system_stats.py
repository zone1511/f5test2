from __future__ import absolute_import
import logging
from f5test.interfaces.ssh import SSHInterface
from ...interfaces.config import expand_devices
from . import ExtendedPlugin, PLUGIN_NAME
import csv
import os
import datetime
from f5test.commands.shell.ssh import get_system_stats
from f5test.interfaces.rest.emapi.objects.shared import DiagnosticsRuntime
from f5test.base import AttrDict

LOG = logging.getLogger(__name__)
DEFAULT_DUTS = []


class DutSystemStats(ExtendedPlugin):
    """
    Collects system stats for each DUT and generates a report into separate
    CSV files for each DUT containing the systems stats prior to and after
    each test run
    """
    enabled = False
    score = 490  # because begin needs to happen after dut start on priority 500
    name = "dut_system_stats"
    jvm_stats = []
    jvm_key = "jvm_diagnostics"

    def configure(self, options, noseconfig):
        """ Construct list of DUTs for which to collection system stats """

        super(DutSystemStats, self).configure(options, noseconfig)
        from ...interfaces.config import ConfigInterface
        from ...interfaces.testcase import ContextHelper

        self.cfgifc = ConfigInterface()
        self.context = ContextHelper()
        self.data = self.context.set_container(PLUGIN_NAME)
        self.duts = options.get('duts',
                                self.cfgifc.config.
                                get('plugins', {}).
                                get('_default_', {}).
                                get('duts', DEFAULT_DUTS))

        self.dutlist = []
        for device in expand_devices(self.duts):
            self.dutlist.append({'name': device.get_alias(),
                                 'ssh': SSHInterface(device=device),
                                 'rest': self.context.get_icontrol_rest(device=device),
                                 'results': []})

        # Check to see if jvm_diagnostics information is desired
        config = self.cfgifc.config.get('plugins')
        if self.name in config:
            if 'jvm_diagnostics' in config[self.name]:
                jvm_diag = config[self.name]['jvm_diagnostics']
                if 'fields' in jvm_diag:
                    self.jvm_stats = jvm_diag['fields']

    def retrieve_runtime(self, restifc):
        return_dict = AttrDict()
        try:
            restcall = restifc.api.get(DiagnosticsRuntime.URI)
            for field in self.jvm_stats:
                return_dict[field] = restcall[field]
        except:
            for field in self.jvm_stats:
                return_dict[field] = "REST API Error!"

        return return_dict

    def startTest(self, test, blocking_context):
        """Collect system stats for each dut"""

        self.current_test = {}
        for dut in self.dutlist:
            util = get_system_stats(ifc=dut['ssh'])
            self.current_test[dut['name']] = {'time': datetime.datetime.now(),
                                              'mem': util['MEM'],
                                              'cpuavg': util['CPUFORMATTED'],
                                              'cpucore': util['CPUFORMATTEDPERCORE'],
                                              'jvm': None
                                              }
            if self.jvm_stats:
                self.current_test[dut['name']]['jvm'] = self.retrieve_runtime(dut['rest'])

    def stopTest(self, test):
        """Collect system stats for each dut and add pre and post stats
           to a result list
        """

        for dut in self.dutlist:
            util = get_system_stats(ifc=dut['ssh'])

            pretest = self.current_test[dut['name']]
            posttest = {'time': datetime.datetime.now(),
                        'mem': util['MEM'],
                        'cpuavg': util['CPUFORMATTED'],
                        'cpucore': util['CPUFORMATTEDPERCORE'],
                        'jvm': None
                        }
            if self.jvm_stats:
                posttest['jvm'] = self.retrieve_runtime(dut['rest'])

            dut['results'].append({'test': test,
                                   'pretest': pretest,
                                   'posttest': posttest})

    def begin(self):
        """Open SSH connections to each DUT"""

        for dut in self.dutlist:
            dut['ssh'].open()

    def finalize(self, result):
        """Creates CSV files in test run directory which display the system
           stats for all configured DUTs.
        """

        d = self.data
        path = d.session.path

        # Close SSH connections and generate reports
        for dut in self.dutlist:
            dut['ssh'].close()
            if os.path.exists(path):
                with open(os.path.join(path, "system-resources-{0}.csv".format(
                                       dut['name'])), 'wb') as csvfile:
                    csvwriter = csv.writer(csvfile)

                    # Determine number of CPU cores dut has based on
                    # first test result CPU core count

                    if len(dut['results']) > 0:
                        numcores = len(dut['results'][0]['pretest']['cpucore'])
                    else:
                        # Prevent error if no tests are run
                        numcores = 0

                    testheader = []
                    testheader.append('Test Name')
                    testheader.append('Start Time')
                    testheader.append('End Time')
                    testheader.append('Pre-Test Memory')
                    testheader.append('Pre-Test CPU Average')
                    for counter in range(0, numcores):
                        testheader.append("Pre-Test CPU Core {0}".format(counter))
                    for field in self.jvm_stats:
                        testheader.append("Pre-Test JVM {0}".format(field))
                    testheader.append('Post-Test Memory')
                    testheader.append('Post-Test CPU Average')
                    for counter in range(0, numcores):
                        testheader.append("Post-Test CPU Core {0}".format(counter))
                    for field in self.jvm_stats:
                        testheader.append("Post-Test JVM {0}".format(field))
                    for field in self.jvm_stats:
                        testheader.append("JVM Delta - {0}".format(field))
                    csvwriter.writerow(testheader)
                    for test in dut['results']:
                        row = []
                        row.append(test['test'])
                        row.append(test['pretest']['time'])
                        row.append(test['posttest']['time'])
                        row.append(test['pretest']['mem'])
                        row.append(test['pretest']['cpuavg'])
                        for core in test['pretest']['cpucore']:
                            row.append(core)
                        for field in self.jvm_stats:
                            row.append(test['pretest']['jvm'][field])
                        row.append(test['posttest']['mem'])
                        row.append(test['posttest']['cpuavg'])
                        for core in test['posttest']['cpucore']:
                            row.append(core)
                        for field in self.jvm_stats:
                            row.append(test['posttest']['jvm'][field])
                        for field in self.jvm_stats:
                            try:
                                row.append(int(
                                           test['posttest']['jvm'][field]) -
                                           int(test['pretest']['jvm'][field]))
                            except:
                                row.append("Not calculable")
                        csvwriter.writerow(row)
