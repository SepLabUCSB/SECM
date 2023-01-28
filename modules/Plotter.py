import matplotlib.pyplot as plt
import time
import numpy as np


def checksum(data):
    if type(data) == np.ndarray:
        # Heatmap type data
        return data.sum()
    if type(data) == list:
        # CV curve type data
        # From polling ADC, of form [ [idxs], [times], [*data] ]
        return sum(data[0])

class Plotter():
    
    def __init__(self, master, fig1, fig2):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.fig1 = fig1
        self.fig2 = fig2
        self.ax1  = fig1.gca()
        self.ax2  = fig2.gca()
        
        self.data1 = np.array([0,])
        self.data2poll = self.master.ADC.pollingdata
        self.data2plot = [ [0,], [], [] ] #idx, x, y
        
        self.last_data1checksum = checksum(self.data1)
        self.last_data2checksum = checksum(self.data2plot)
        
        
        
        # Initialize heatmap
        self.image1 = self.ax1.imshow(np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32), cmap='afmhot')
        self.ax1.set_xlabel(r'$\mu$m')
        self.ax1.set_ylabel(r'$\mu$m')
        self.fig1.canvas.draw()
        self.fig1.tight_layout()
        self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.ax1.draw_artist(self.image1)
        self.fig1.canvas.blit(self.ax1.bbox)
        plt.pause(0.001)
        
        
        # Initialize echem fig
        self.ln, = self.ax2.plot([], [])
        self.ax2.set_xlim(-0., 2.1)
        self.ax2.set_xlabel('')
        self.ax2.set_ylabel('')
        self.fig2.canvas.draw()
        self.fig2.tight_layout()
        self.ax2bg = self.fig2.canvas.copy_from_bbox(self.ax2.bbox)
        self.ax2.draw_artist(self.ln)
        self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)
        
        
    
    def load_from_expt(self, expt):
        self.data1 = expt.data
        xlim = (0, expt.length)
        ylim = (0, expt.length)
        self.set_axlim('fig1', xlim, ylim)
            
   
    def update_figs(self, **kwargs):
        # Called every 10 ms by TK mainloop.
        # Check if data has updated. If so, plot it to
        # the appropriate figure.
        # self.data2poll = self.master.ADC.pollingdata
        self.data2poll = self.master.ADC.pollingdata
        if checksum(self.data1) != self.last_data1checksum:
            self.update_fig1()
        
        if checksum(self.data2poll) != self.last_data2checksum:
            self.update_fig2()        
        
        self.master.GUI.root.after(10, self.update_figs)
        return
        
    
    
    def update_fig1(self, **kwargs):
        # Fig 1 - SECM heatmap
        arr = self.data1
        self.image1.set_data(arr)
        minval = min(arr.flatten())
        maxval = max(arr.flatten())
        self.image1.set(clim=( minval - abs(0.1*minval), # Update color scale
                          maxval + abs(0.1*maxval)) 
                  ) 
        left, right = self.ax1lim[0][0], self.ax1lim[0][1]
        bottom, top = self.ax1lim[1][0], self.ax1lim[1][1]
        self.image1.set_extent((left, right, bottom, top))
        self.ax1.draw_artist(self.image1)
        self.fig1.canvas.blit(self.fig1.bbox)
        self.fig1.canvas.draw_idle()
        self.last_data1checksum = checksum(self.data1)
        plt.pause(0.001)
    
    
    def update_fig2(self):
        idxs, ts, ch1data, ch2data = self.master.ADC.pollingdata.copy()
        self.last_data2checksum = checksum([idxs, ts])
        idx, x, y = self.data2plot
        last_idx = max(idx)
        startpoint = min([i for i, val in enumerate(idxs)
                          if val > last_idx])
        idx += idxs[startpoint:]
        x   += ts[startpoint:]
        y   += ch1data[startpoint:]
        
        self.ln.set_data(x, y)
        self.set_axlim('fig2', 
                       (min(x) - 0.05*abs(min(x)),
                        max(x) + 0.05*abs(max(x))),
                       (min(y) - 0.05*abs(min(y)),
                        max(y) + 0.05*abs(max(y)))
                       )
        self.ax2.draw_artist(self.ln)
        self.fig2.canvas.blit(self.ax2.bbox)
        self.fig2.canvas.draw_idle()
        plt.pause(0.001)
    
    
    def set_axlim(self, fig, xlim, ylim):
        if fig == 'fig1':
            self.ax1lim = (xlim, ylim)
            self.ax1.set_xlim(xlim)
            self.ax1.set_ylim(ylim)
        if fig == 'fig2':
            self.ax2lim = (xlim, ylim)
            self.ax2.set_xlim(xlim)
            self.ax2.set_ylim(ylim)
        
        
        
            
        
    



