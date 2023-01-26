import matplotlib.pyplot as plt
import time
import numpy as np








class Plotter():
    
    def __init__(self, master, fig1, fig2):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.fig1 = fig1
        self.fig2 = fig2
        self.ax1  = fig1.gca()
        self.ax2  = fig2.gca()
        
        self.data1 = np.array([])
        self.data2 = np.array([])
        
        self.last_data1 = np.array([0])
        self.last_data2 = np.array([0])
        
        self.NEW_DATA = False
        
        
        # Initialize heatmap
        self.image1 = self.ax1.imshow(np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32), cmap='afmhot')
        self.fig1.canvas.draw()
        self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.ax1.draw_artist(self.image1)
        self.fig1.canvas.blit(self.ax1.bbox)
        plt.pause(0.001)
        
        
    
    def run(self):
        while True:
            if self.master.STOP:
                print('plotter stopping')
                self.willStop = True
                return
            if self.NEW_DATA:
                self.update_fig('fig1')
                self.NEW_DATA = False
            time.sleep(0.001)
            
   
    def init_fig1(self, arr, **kwargs):
        self.image1 = self.ax1.imshow(arr, cmap='afmhot')
        self.fig1.canvas.draw()
        self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.ax1.draw_artist(self.image1)
        self.fig1.canvas.blit(self.ax1.bbox)
        plt.pause(0.001)
        self.FIG1_INITIALIZED = True
    
    
    def update_fig(self, fig:str, **kwargs):
        arr = self.data1.copy()
        # print(arr)
        self.image1.set_data(arr)
        minval = min(arr.flatten())
        maxval = max(arr.flatten())
        self.image1.set(clim=( minval - abs(0.1*minval), # Update color scale
                          maxval + abs(0.1*maxval)) 
                  ) 
        # self.ax1.draw_artist(self.image1)
        # self.fig1.canvas.blit(self.fig1.bbox)
        # self.fig1.canvas.draw_idle()
        # self.fig1.canvas.draw()
        # self.fig1.canvas.flush_events()
        plt.show(block=False)
        plt.pause(0.05)
        
        
        
            
        
    



