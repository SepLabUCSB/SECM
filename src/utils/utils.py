import threading
import datetime
import os
import shutil

import numpy as np


def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    t.start()
    return t


def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]
    

def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return("break")



LOG_FILE = 'log/log.txt'
if not os.path.exists(LOG_FILE):
    os.makedirs('log/', exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        f.close()
if os.path.getsize(LOG_FILE) > 60000: # ~1000 lines
    shutil.copy2(LOG_FILE, 'log/old_log.txt')
    with open(LOG_FILE, 'w') as f:
        f.close()
    


class Logger():
    '''
    Base logging class. All submodules inherit this
    '''
    
    LOG_FILE = LOG_FILE
    MAX_SIZE = 1e6
    
        
    
    def log(self, string, quiet=False):
        # All child classes inherit this so self is i.e. MasterModule,
        # GUI, etc.
        time   = datetime.datetime.now().strftime('%Y%m%d-%H:%M:%S.%f')
        module = self.__class__.__name__[:12]
        
        if not quiet:
            print(f'{module.ljust(12)} | {string}')
        msg = f'{time} | {module.ljust(12)} | {string}\n'
        
        with open(self.LOG_FILE, 'a') as f:
            f.write(msg)
        return
