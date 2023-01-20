



class FeedbackController():
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        # Get local refs to other modules
        self.Piezo = self.master.Piezo
        self.ADC = self.master.ADC
        self.HekaWriter = self.master.HekaWriter

    

    def approach_curve(self, i_cutoff):
        
        current = self.get_current()
        
        while True:
            break

    


