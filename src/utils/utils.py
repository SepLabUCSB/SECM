import threading
import datetime
import os
import shutil

import numpy as np


def run(func, args=()):
    print(f'Error: deprecated function run() called on {func}')
    return func

def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]
    

def focus_next_widget(event):
    widget = event.widget.tk_focusNext()
    widget.focus()
    try:
        widget.select_range(0, 'end')
    except:
        pass
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
        t   = datetime.datetime.now()
        log_time = t.strftime('%Y%m%d-%H:%M:%S.%f')
        prnt_time = t.strftime('%H:%M:%S')
        module = self.__class__.__name__[:12]
        
        if not quiet:
            print(f'{prnt_time} | {module.ljust(12)} | {string}')
        msg = f'{log_time} | {module.ljust(12)} | {string}\n'
        
        with open(self.LOG_FILE, 'a') as f:
            f.write(msg)
        return



class threads(Logger):
    
    @classmethod
    def new_thread(cls, func, _new_thread=True):
        def inner_func(*args, **kwargs):
            # cls.log(cls, f'Starting new thread {func}')
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            t.start()
        if _new_thread:
            # cls.log(cls, f'Will start {func} in new thread')
            return inner_func
        else:
            # cls.log(cls, f'Will start {func} in same thread')
            return func
        
        
        
        
        
        
        
        