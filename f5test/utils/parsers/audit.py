'''
Created on Apr 19, 2011

@author: jono
'''
def audit_parse(data):
    result = {}
    
    for line in data.splitlines():
        line.strip()
        if not line:
            continue
        if line[0] == '/':
            bits = line.replace('/','').strip().split()
            klass = bits[0]
            array = bits[-1]
            if not result.get(klass):
                result[klass] = {}
            
            bits = array.split('[')
            if len(bits) == 2:
                idx = int(bits[1][:-1])
                array = bits[0]
            else:
                idx = 0

            if not result[klass].get(array):
                result[klass][array] = []

                diff = idx - len(result[klass][array])
            if diff >= 0:
                for _ in range(diff+1):
                    result[klass][array].append({})

            continue
        
        bits = line.strip().split('=')
        if len(bits) == 2:
            kvd = result[klass][array][idx]
            kvd[bits[0]] = bits[1]
        else:
            raise ValueError, line
    
    return result

def get_inactive_volume(audit):
        return filter(lambda x:x.get('is_active') != 'true' and not x.get('is_CF'), 
                      audit['Slot']['audit_slots']) \
                  [0]['visible_name']

def get_active_volume(audit):
        return filter(lambda x:x.get('is_active') == 'true', 
                      audit['Slot']['audit_slots']) \
                  [0]['visible_name']
