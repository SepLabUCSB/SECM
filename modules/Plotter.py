import matplotlib.pyplot as plt
import time
import numpy as np
from scipy.signal import savgol_filter


def checksum(data):
    if type(data) == np.ndarray:
        # Heatmap type data
        return data.sum()
    if type(data) == list:
        # CV curve type data
        # From polling ADC, of form [ [idxs], [times], [*data] ]
        return np.array(data).flatten().sum()


def get_plotlim(xdata, ydata):
    lim = (
     (min(xdata) - 0.05*abs(min(xdata)),
      max(xdata) + 0.05*abs(max(xdata))
      ),
     (min(ydata) - 0.05*abs(min(ydata)),
      max(ydata) + 0.05*abs(max(ydata))
      )
     )
    if len(xdata) == 1:
        return ((0,0.1), (0,0.1))
    return lim

def get_axval_axlabels(expt_type):
    if expt_type == 'CV':
        xval = 'ch1'
        yval = 'ch2'
        yaxlabel='I'
        xaxlabel='V'
            
    elif expt_type == 'CA':
        xval = 't'
        yval = 'ch2'
        yaxlabel='I'
        xaxlabel='t'
    
    return xval, yval, xaxlabel, yaxlabel


class Plotter():
    
    def __init__(self, master, fig1, fig2):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.adc_polling = True
        self.adc_polling_count = 0
        
        self.fig1 = fig1
        self.fig2 = fig2
        self.ax1  = fig1.gca()
        self.ax2  = fig2.gca()
        
        self.data1 = np.array([0,])
        self.data2poll = self.master.ADC.pollingdata
        self.data2plot = [ [0], [0], [0], [0] ] #idx, x, y, y2
        
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
        
        self.cid1 = self.fig1.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
        
        
        # Initialize echem fig
        self.ln, = self.ax2.plot([], [])
        self.ln2, = self.ax2.plot([], [])
        self.ax2.set_xlim(-0., 2.1)
        self.ax2.set_xlabel('')
        self.ax2.set_ylabel('')
        self.fig2.canvas.draw()
        self.fig2.tight_layout()
        self.ax2bg = self.fig2.canvas.copy_from_bbox(self.ax2.bbox)
        self.ax2.draw_artist(self.ln)
        self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)
        
        self.cid2 = self.fig2.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
        
        
    
    def load_from_expt(self, expt):
        self.data1 = expt.get_heatmap_data()
        xlim = (0, expt.length)
        ylim = (0, expt.length)
        self.set_axlim('fig1', xlim, ylim)
    
    
    def onclick(self, event):
        # Clicking on pixel in SECM histogram displays that CV ( or
        # CA, or EIS, ...) in the lower figure
        if event.inaxes == self.ax1:
            x, y = event.xdata, event.ydata
            closest_datapoint = self.master.expt.get_nearest_datapoint(x, y)
            self.stop_polling_ADC()
            # TODO: support different plots besides hardcoded CV
            xdata, ydata = closest_datapoint.get_data()
            self.set_static_fig2_data(xdata, ydata)
        return
     
        
    def poll_ADC(self):
        self.adc_polling = True
        
        
    def stop_polling_ADC(self):
        self.adc_polling = False
        
   
    def update_figs(self, **kwargs):
        # Called every 10 ms by TK mainloop.
        # Check if data has updated. If so, plot it to
        # the appropriate figure.
        
        self.data2poll = self.master.ADC.pollingdata
        # self.data1 = self.master.expt.get_heatmap_data()
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
    
    
    def set_static_fig2_data(self, xdata, ydata):
        self.ax2.cla()
        self.ax2.plot(xdata, ydata)
        self.set_axlim('fig2',
                       *get_plotlim(xdata, ydata)
                       )
        _,_, xaxlabel, yaxlabel = get_axval_axlabels(
                                        self.master.expt.expt_type
                                            )
        self.ax2.set_xlabel(xaxlabel)
        self.ax2.set_ylabel(yaxlabel)
        self.fig2.canvas.draw()
        plt.pause(0.001)
        return
    
    
    def reinit_fig2(self):
        # Redraw blank fig2 before polling ADC
        self.data2plot = [ [0], [0], [0], [0] ]
        self.ax2.cla()
        self.ln, = self.ax2.plot([], [])
        self.ln2, = self.ax2.plot([], [])
        self.ax2.set_xlim(-0., 2.1)
        self.ax2.set_xlabel('')
        self.ax2.set_ylabel('')
        self.fig2.canvas.draw()
        self.fig2.tight_layout()
        self.ax2bg = self.fig2.canvas.copy_from_bbox(self.ax2.bbox)
        self.ax2.draw_artist(self.ln)
        self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)
    
    
    def update_fig2(self, xval='t', yval='ch1'):
        '''
        xval: 't', 'ch1', 'ch2'
        yval: 'ch1', 'ch2'
        '''
        
        if self.master.ADC.pollingcount != self.adc_polling_count:
            # Check if new polling has started
            self.adc_polling_count = self.master.ADC.pollingcount
            self.reinit_fig2()
        
        if self.adc_polling:
            # Real time plot - get new data from ADC
            dat = self.master.ADC.pollingdata.copy()
            if len(dat) != 4: 
                print(dat)
                return
            idxs, ts, ch1, ch2 = dat
            self.last_data2checksum = checksum([idxs, ts])
            
            # local copy of data already on plot
            idx, x, y, y2 = self.data2plot.copy()
            last_idx = idx[-1]
            if len(idx) < 5:
                # New plot
                idx, x, y, y2 = [], [], [], []
                last_idx = -1
            
            
            # Find new points to plot
            try:
                startpoint = min([i for i, val in enumerate(idxs)
                                  if val > last_idx])
            except ValueError:
                return
            idx += idxs[startpoint:]
            
            # Determine what to plot based on exp_type
            xval, yval, xaxlabel, yaxlabel = get_axval_axlabels(
                                            self.master.expt.expt_type
                                            )
            
            # str -> array lookup table
            d = {'t': ts,
                 'ch1': ch1,
                 'ch2': ch2
                 }
            
            # Set new data and draw
            new_x = d[xval][startpoint:]
            new_y = d[yval][startpoint:]
            new_y2 = ch2[startpoint:]
            
            
            x  += new_x
            y  += new_y
            y2 += new_y2
            
            # self.ln.set_data(x, y)
            self.ln.set_data(savgol_filter(x, 21, 1), 
                              savgol_filter(y, 21, 1))
            # self.ln2.set_data(x, y2)
            self.set_axlim('fig2', 
                           *get_plotlim(x, y)
                           )
            # self.ax2.set_xlabel(xaxlabel)
            # self.ax2.set_ylabel(yaxlabel)
            self.ax2.draw_artist(self.ln)
            self.ax2.draw_artist(self.ln2)
            self.fig2.tight_layout()
            self.fig2.canvas.blit(self.ax2.bbox)
            self.fig2.canvas.draw_idle()
            self.data2plot = [idx, x, y, y2]
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
        
        
        
            
        
    



