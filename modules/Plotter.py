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


def get_plotlim(xdata, ydata):
    lim = (
     (min(xdata) - 0.05*abs(min(xdata)),
      max(xdata) + 0.05*abs(max(xdata))
      ),
     (min(ydata) - 0.05*abs(min(ydata)),
      max(ydata) + 0.05*abs(max(ydata))
      )
     )
    return lim


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
    
    
    def update_fig2(self, xval='t', yval='ch1'):
        '''
        xval: 't', 'ch1', 'ch2'
        yval: 'ch1', 'ch2'
        '''
        # Get new data from ADC
        idxs, ts, ch1, ch2 = self.master.ADC.pollingdata.copy()
        self.last_data2checksum = checksum([idxs, ts])
        
        # local copy of data already on plot
        idx, x, y = self.data2plot.copy()
        last_idx = idx[-1]
        
        # Find new points to plot
        startpoint = min([i for i, val in enumerate(idxs)
                          if val > last_idx])
        idx += idxs[startpoint:]
        
        # str -> array lookup table
        d = {'t': ts,
             'ch1': ch1,
             'ch2': ch2
             }
        
        # Set new data and draw
        new_x = d[xval][startpoint:]
        new_y = d[yval][startpoint:]
        
        x += new_x
        y += new_y
                
        self.ln.set_data(x, y)
        self.set_axlim('fig2', 
                       *get_plotlim(x, y)
                       )
        self.ax2.draw_artist(self.ln)
        self.fig2.canvas.blit(self.ax2.bbox)
        self.fig2.canvas.draw_idle()
        self.data2plot = [idx, x, y]
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
        
        
        
            
        
    



