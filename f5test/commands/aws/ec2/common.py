'''
Created on Feb 21, 2014

@author: a.dobre@f5.com
'''

from .base import EC2Command
from f5test.base import AttrDict
from ....utils.wait import wait
import logging


LOG = logging.getLogger(__name__)


get_all_instance_ids = None
class GetAllInstanceIds(EC2Command):  # @IgnorePep8
    """returns the all instances that are NOT terminated

    @return: list of instance objs
    @rtype: List of Instance objs
    """
    def __init__(self, *args, **kwargs):
        super(GetAllInstanceIds, self).__init__(*args, **kwargs)

    def setup(self):
        ret = []
        reservations = self.api.get_all_reservations()
        for reservation in reservations:
            for instance in reservation.instances:
                if not instance.state in ('terminated', 'shutting-down'):
                    ret.append(instance.id)
        return ret


get_instance_by_id = None
class GetInstanceById(EC2Command):  # @IgnorePep8
    """returns the instance object to use in diverse other functions

    @param iid: instance ID #mandatory
    @type iid: string

    @return: the instance obj
    @rtype: Instance obj
    """
    def __init__(self, iid, *args, **kwargs):
        super(GetInstanceById, self).__init__(*args, **kwargs)
        self.iid = iid

    def setup(self):
        # Find a specific instance, returns a list of Reservation objects
        reservations = self.api.get_all_instances(instance_ids=[self.iid])
        # Find the Instance object inside the reservation
        return reservations[0].instances[0]


get_instances_by_id = None
class GetInstancesById(EC2Command):  # @IgnorePep8
    """returns the instances' objects to use in diverse other functions

    @param iidlist: list of instance IDs #mandatory
    @type iidlist: list of strings

    @return: list of instance objs
    @rtype: List of Instance objs
    """
    def __init__(self, iidlist, *args, **kwargs):
        super(GetInstancesById, self).__init__(*args, **kwargs)
        self.iidlist = iidlist

    def setup(self):
        ret = []
        reservations = self.api.get_all_reservations()
        for iid in self.iidlist:
            for reservation in reservations:
                for instance in reservation.instances:
                    if iid == instance.id:
                        ret.append(instance)
                        break
        return ret


get_instance_health_by_id = None
class GetInstanceHealthById(EC2Command):  # @IgnorePep8
    """Checks for health and status of a instance by id

    @param iid: instance ID #mandatory
    @type iid: string

    @return: AttrDict of the health
    @rtype: AttrDict
    """
    def __init__(self, iid, *args, **kwargs):
        super(GetInstanceHealthById, self).__init__(*args, **kwargs)
        self.iid = iid

    def setup(self):
        dicti = AttrDict()
        instance = get_instance_by_id(self.iid, ifc=self.ifc)
        dicti['id'] = instance.id
        dicti['state'] = None
        dicti['istate'] = None
        dicti['sstate'] = None
        if instance.state != "running":
            dicti['state'] = instance.state
            dicti['istate'] = None
            dicti['sstate'] = None
        else:
            istatuses = self.api.get_all_instance_status([self.iid])
            if istatuses:
                istatus = istatuses[0]
                LOG.debug("Istatus was: {0}".format(istatus))
                # dicti['id'] = istatus.id
                dicti['state'] = istatus.state_name
                dicti['istate'] = str(istatus.instance_status)
                dicti['sstate'] = str(istatus.system_status)
        return dicti


get_instances_health_by_id = None
class GetInstancesHealthById(EC2Command):  # @IgnorePep8
    """Checks for health and status of all instances by id - from a list of ids

    @param iidlist: list of instance IDs #mandatory
    @type iidlist: list of strings

    @return: List of AttrDict of the health
    @rtype: List of AttrDict
    """
    def __init__(self, iidlist, *args, **kwargs):
        super(GetInstancesHealthById, self).__init__(*args, **kwargs)
        self.iidlist = iidlist

    def setup(self):
        health = []
        for iid in self.iidlist:
            dicti = get_instance_health_by_id(iid, ifc=self.ifc)
            health.append(dicti)
        return health


wait_to_stop_instances_by_id = None
class WaitToStopInstancesById(EC2Command):  # @IgnorePep8
    """Issues a stop command for all instances from the given list (by ids)
    And waits for all to be properly stopped before exiting.

    @param iidlist: list of instance IDs #mandatory
    @type iidlist: list of strings

    @return: True if all are stopped properly
    @rtype: Bool
    """
    def __init__(self, iidlist, timeout=300, *args, **kwargs):
        super(WaitToStopInstancesById, self).__init__(*args, **kwargs)
        self.iidlist = iidlist
        self.timeout = timeout

    def setup(self):
        self.api.stop_instances(instance_ids=self.iidlist)
        self.statenow = None

        for self.iid in self.iidlist:

            def is_instance_stopped():
                self.instance = get_instance_by_id(self.iid, ifc=self.ifc)
                self.statenow = self.instance.state
                LOG.debug("Instance {0} state: {1}".format(self.instance.id,
                                                           self.statenow))
                if self.statenow != "stopped":
                    return False
                else:
                    LOG.info("Instance {0} is stopped.".format(self.instance.id))
                    return True
            wait(is_instance_stopped, timeout=self.timeout, interval=15,
                    progress_cb=lambda x: 'Stopping {0}. State now: {1}...'
                                   .format(self.instance, self.statenow),
                    timeout_message="Instances Not Stopped in {0}s")
        return True


wait_to_start_instances_by_id = None
class WaitToStartInstancesById(EC2Command):  # @IgnorePep8
    """Issues a start command for all instances from the given list (by ids)
    And waits for all to be properly started before exiting. This includes:
    - status for the instance
    - inside instance checks
    - inside system checks

    @param iidlist: list of instance IDs #mandatory
    @type iidlist: list of strings

    @return: True if all started properly
    @rtype: Bool
    """
    def __init__(self, iidlist, timeout=400, *args, **kwargs):
        super(WaitToStartInstancesById, self).__init__(*args, **kwargs)
        self.iidlist = iidlist
        self.timeout = timeout

    def setup(self):
        self.api.start_instances(instance_ids=self.iidlist)

        for self.iid in self.iidlist:
            self.healthnow = None

            def is_instance_started_and_healthy():
                self.healthnow = get_instance_health_by_id(self.iid, ifc=self.ifc)
                LOG.debug("Instance {0} health now: {1}".format(self.iid, self.healthnow))
                if self.healthnow.state != "running" or \
                    self.healthnow.sstate != 'Status:ok' or \
                    self.healthnow.istate != 'Status:ok':
                        return False
                else:
                    LOG.info("Instance {0} is healthy.".format(self.iid))
                return True
            wait(is_instance_started_and_healthy, timeout=self.timeout, interval=15,
                    progress_cb=lambda x: "Starting Instance {0}. Health: {1}..."
                                   .format(self.iid, self.healthnow),
                    timeout_message="Instances Not Healthy after {0}s")

        return True


wait_to_terminate_instances_by_id = None
class WaitToTerminateInstancesById(EC2Command):  # @IgnorePep8
    """Waits for instance(s) by id(s) to be terminated.
    It will NOT issue the terminate command unless specified with:
    with_terminate=True

    @param iidlist: list of instance IDs #mandatory
    @type iidlist: list of strings
    @param with_terminate: defaults to False; #optional
                It will not issue the terminate command, it will just check if
                it is terminated. Use with True to actually terminate and check.
    @type with_terminate: bool

    @return: True if all started properly
    @rtype: Bool
    """
    def __init__(self, iidlist, with_terminate=False, timeout=400, *args, **kwargs):
        super(WaitToTerminateInstancesById, self).__init__(*args, **kwargs)
        self.iidlist = iidlist
        self.with_terminate = with_terminate
        self.timeout = timeout

    def setup(self):
        if self.with_terminate:
            self.api.terminate_instances(instance_ids=self.iidlist)

        for self.iid in self.iidlist:
            self.healthnow = None

            def is_instance_terminated():
                self.healthnow = get_instance_health_by_id(self.iid, ifc=self.ifc)
                LOG.debug("Instance {0} health now: {1}".format(self.iid, self.healthnow))
                if self.healthnow.state != "terminated":
                        return False
                else:
                    LOG.info("Instance {0} is terminated.".format(self.iid))
                return True
            wait(is_instance_terminated, timeout=self.timeout, interval=15,
                    progress_cb=lambda x: "Instance {0}. Health: {1}..."
                                   .format(self.iid, self.healthnow),
                    timeout_message="Instances Not Terminated after {0}s")

        return True
