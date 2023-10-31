import time
import os
import psutil
import shutil
import json
from collections import deque
import numpy as np
from tkinter import messagebox
from .FeedbackController import read_heka_data
from .DataStorage import EISDataPoint
from ..utils.utils import run, Logger
from ..utils.EIS_util import generate_tpl, get_EIS_sample_rate
from functools import partial


input_file  = r'C:/ProgramData/HEKA/com/E9Batch.In'
output_file = r'C:/ProgramData/HEKA/com/E9Batch.Out'

DEFAULT_SAVE_PATH = r'D:/SECM/Data'

gl_st = time.time()
     



        ######################################
        #####                            #####
        #####     HEKA READER CLASS      #####                            
        #####                            #####
        ######################################


class HekaReader(Logger):
    'Pass all commands to module shared between channels'
    def __init__(self, master, sharedReader):
        self.master = master
        self.master.register(self) # Also sets self.channel
        self.willStop = False
        
        self.Reader = sharedReader
    
    def PatchmasterRunning(self):
        self.Reader.PatchmasterRunning(self.channel)
            
    def read_stream(self):
        run(self.Reader.read_stream)
        run(self.check_for_stop)
    
    def check_for_stop(self):
        while True:
            if self.master.STOP:
                self.Reader.STOP = True
                break
        self.log('Stopping')
        
    def get_last(self):
        'Returns most recent output from Patchmaster'
        return self.Reader.last
        


        
class SharedHekaReader(Logger):
    '''
    Class for reading PATCHMASTER's responses in /E9Batch.Out
    
    The last response is stored in HekaReader.last and should be checked
    immediately after a command is sent, because it could get overwritten
    by a subsequent message
    '''
    def __init__(self, output_file=output_file):
        self.file = output_file
        self.last = None
        self.STOP = False
        self.isReading = False
        if os.path.exists(self.file):
            with open(self.file, 'w') as f: 
                f.close()
    
    def PatchmasterRunning(self, channel):
        # Checks if PATCHMASTER is currently running
        for p in psutil.process_iter():
            if 'PatchMaster.exe' in p.name():
                return True
        return False
    
    
    def read_stream(self):
        '''
        Call in its own thread. Reads HEKA output file continuously
        until receives stop command from master. Stores the last
        output in self.last.
        '''
        if self.isReading:
            # Other channel already initialized reading
            return
        
        while True:
            self.isReading = True
            if self.STOP:
                break
            
            if not os.path.exists(self.file): continue
            
            with open(self.file, 'r') as f:
                lines = [line.rstrip() for line in f]
                if (lines != self.last and lines != None):
                    # print(f'Response: {lines} {time.time() - gl_st:0.4f}')
                    self.last = lines
        self.log('Stopped reading')







        ######################################
        #####                            #####
        #####     HEKA WRITER CLASS      #####                            
        #####                            #####
        ######################################

class HekaWriter(Logger):
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
    
    def send_commands(self):
        'Pass commands on to shared writer'
        pass
    
    def run_CV(self):
        pass
    
    def run_EIS(self):
        pass
    
    def run_custom(self):
        pass
    

class SharedHekaWriter(Logger):
    
    def __init__(self, input_file=input_file):
        self.file = input_file
        self.num  = 0
        
        self.clear_file()
        self.send_command('Echo startup')
        self.send_command('SetSleep 0.01')
    
    def clear_file(self, channel):
        with open(self.file, 'w') as f:
            f.close()
        self.num = 0
    
    def send_command(self, cmd):
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n{cmd}\n')
        self.num += 1
        time.sleep(0.1)
        
    def send_multiple_cmds(self, cmds):
        with open(self.file, 'w') as f:
            f.write(f'+{self.num}\n')
            for cmd in cmds:
                f.write(f'{cmd}\n')
        self.num += 1
        time.sleep(0.1)
    
    def save_last_experiment
      
        

def generate_CV_params(E0, E1, E2, E3, scan_rate, quiet_time):
    '''
    *** POTENTIALS IN V, SCAN_RATE IN V/s, QUIET_TIME IN s ***
    1. Hold at E0 for quiet_time
    2. Ramp to E1 at scan_rate
    3. Ramp to E2 at scan_rate
    4. Ramp to E3 (end potential) at scan_rate
    
    Parameter assignments:
            0: Holding potential (V) (p1)
            1: Holding time      (s) (p2)
            2: E1 potential      (V) (p3)
            3: E1 ramp time      (s) (p4)
            4: E2 potential      (V) (p5)
            5: E2 ramp time      (s) (p6)
            6: End potential     (V) (p7)
            7: End ramp time     (s) (p8)
    '''
    rt1 = abs(E1 - E0) / scan_rate
    rt2 = abs(E2 - E1) / scan_rate
    rt3 = abs(E3 - E2) / scan_rate
    
    duration = quiet_time + rt1 + rt2 + rt3
    
    values = {
        0: E0,
        1: quiet_time,
        2: E1,
        3: rt1,
        4: E2,
        5: rt2,
        6: E3,
        7: rt3
        }
    return values, duration



def generate_EIS_params(E_DC, duration):
    '''
    *** POTENTIALS IN V, ***
    
    Parameter assignments:
        0: DC bias   (V) (p1)
        1: scan time (s) (p2)
    '''
    
    values = {
        0: E_DC,
        1: duration,
        }
    
    return values, duration


def get_filters(max_freq):
    '''
    Return appropriate setting for filter1 and filter2 based on the 
    
    maximum applied EIS freq
    '''
    
    filt1s = [10, 30, 100]
    best_filt1 = 100
    for filt in filt1s:
        if filt*1000 >= 5*max_freq:
            best_filt1 = filt
            break
    best_filt2 = 5*max_freq
    if best_filt2 > 8000:
        f2_val  = 8000
        f2_type = 2
    else:
        f2_val  = best_filt2
        f2_type = 0 # Sets as Bessel filter
        
    filter1options = [100, 30, 10]    # Order filters appear in PATCHMASTER
    f1_idx = [i for i, val in enumerate(filter1options) 
              if val == best_filt1][0]
    
    
    return [f'Set E Filter1 {f1_idx}', 
            f'Set E F2Response {f2_type}', 
            f'Set E Filter2 {f2_val/1000}']



    