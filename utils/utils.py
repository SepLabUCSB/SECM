import threading

def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    # t = StoppableThread(target=func, args=args)
    t.start()
    return t

def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return("break")


class StoppableThread(threading.Thread):
    
    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()