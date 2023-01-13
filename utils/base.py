import time
import heapq

class BaseClass():
    # Base class for event handling modules
    # All modules should be subclassed from this
    
    def __init__(self):
        self.willStop = False
        self.logger = Logger()
        
    def log(self, txt):
        self.logger.log()
        
    def end(self):
        self.willStop = True



class Scheduler():
    # Scheduler for a single thread's tasks
    def __init__(self, interval = 0.01):
        self.queue = []
        self.interval = interval
    
    def put(self, x):
        # add to queue
        heapq.heappush(self.queue, x)
    
    def peek(self):
        return self.queue[0]
    
    def get(self):
        if len(self.queue) == 0: return None
        return heapq.heappop(self.queue)
    
    def cancelTask(self, task):
        # Remove task from queue
        for i,t in enumerate(self.queue):
            if t == task:
                del self[i]
                break
        heapq.heapify(self.queue)
        task.endTask()
    
    def nextTime(self):
        if len(self.queue) == 0: return 1000
        return self.peek().nextExec - time.time()
    
    def runNextTask(self):
        nextTime = self.nextTime()
        while nextTime - time.time() > 0:
            time.sleep(0.005)
        nextTask = self.get()
        if nextTask is None: return
        
        if nextTask.status != 'end':
            nextTask.run()
    
    


class Task():
    
    def __init__(self, delay=0):
        self.delay = delay
        self.nextExec = time.time() + delay
        self.runCount = 0
        self.status = 'running'
    
    def __gt__(self, b):
        return self.nextExec > b.nextExec

    def __lt__(self, b):
        return self.nextExec < b.nextExec
    
    def __eq__(self, b):
        return self.nextExec == b.nextExec
    
    def run(self):
        self.runCount += 1
        self.nextRun(self.delay)
        
    def nextRun(self, delay):
        self.nextExec = time.time() + delay
    
    def endTask(self):
        self.status = 'end'