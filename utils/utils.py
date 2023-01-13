import threading

def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    t.start()
    return t

def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return("break")