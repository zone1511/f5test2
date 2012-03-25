'''
Created on Feb 9, 2012

@author: jono
'''
from f5test.interfaces.config import expand_devices
from f5test.macros.base import MacroThread, StageError
from f5test.base import Options
from Queue import Queue
import traceback
import logging
#from pprint import pprint

LOG = logging.getLogger(__name__)
DEFAULT_PRIORITY = 100


def process_stages(stages, ifcs, stages_map):
    if not stages:
        return

    q = Queue()
    pool = []
    
    # Sort stages by priority attribute and stage name
    stages = sorted(stages.iteritems(), key=lambda x:(x[1] and 
                                                      x[1].get('priority', 
                                                               DEFAULT_PRIORITY), 
                                                      x[0]))
    # Group stages of the same type. The we spin up one thread per stage in a
    # group and wait for threads within a group to finish.
    sg_dict = {}
    sg_list = []
    last = Options()
    for stage in stages:
        specs = stage[1]
        if not specs:
            continue
        specs = Options(specs)

        key = specs.get('group', last.key if specs.type == last.type 
                        else "{0}-{1}".format(stage[0], specs.type))
        
        group = sg_dict.get(key)
        if not group:
            sg_dict[key] = []
            sg_list.append(sg_dict[key])
        sg_dict[key].append(stage)
        last.type = specs.type
        last.key = key

#    pprint(sg_list)
#    raise
    for stages in sg_list:
        for stage in stages:
            description, specs = stage
            if not specs:
                continue
            
            # items() reverts <Options> to a simple <dict>
            specs = Options(specs)
            if not stages_map.get(specs.type):
                LOG.warning("Stage '%s' (%s) not defined.", description, specs.type)
                continue
            
            stage_class = stages_map[specs.type]
            parameters = specs.get('parameters', Options())
            parameters._IFCS = ifcs
    
            for device in expand_devices(specs):
                stage = stage_class(device, parameters)
                t = MacroThread(stage, q, name='%s :: %s' % (specs.type, device))
                t.start()
                pool.append(t)
                if not stage_class.parallelizable:
                    LOG.debug('Waiting for thread')
                    t.join()

        LOG.debug('Waiting for threads...')
        for t in pool:
            t.join()
        
        if not q.empty():
            count = 0
            while not q.empty():
                count += 1
                ret = q.get(block=False)
                thread, exc_info = ret.popitem()
                LOG.error('Exception while "%s"', thread.getName())
                for line in traceback.format_exception(*exc_info):
                    LOG.error(line.strip())
                
            raise StageError('%d Exception(s) occurred in stage "%s"' % (count, description))
