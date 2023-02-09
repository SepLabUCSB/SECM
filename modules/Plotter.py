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
    #TODO: fix this or make sure it never happens
    if expt_type == '':
        expt_type = 'CA'
        
    if (expt_type == 'CV' or expt_type == 'I vs V'):
        xval = 'ch1'
        yval = 'ch2'
        yaxlabel='I'
        xaxlabel='V'
            
    elif (expt_type == 'CA' or expt_type == 'I vs t'):
        xval = 't'
        yval = 'ch2'
        yaxlabel='I'
        xaxlabel='t'
    
    elif (expt_type == 'V vs t'):
        xval = 't'
        yval = 'ch1'
        yaxlabel='V'
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
        self.data2_all  = [ [-1], [], [], [] ] #keep track of all fig2 data for later replotting
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
            # TODO: support different plots besides hardcoded CV
            self.update_fig2data(closest_datapoint.get_data())
        return
     
    
    def isADCpolling(self):
        self.adc_polling = self.master.ADC.isPolling()
        return self.adc_polling
        
   
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
        
        self.master.GUI.root.after(100, self.update_figs)
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
        # self.fig1.canvas.blit(self.fig1.bbox)
        self.fig1.canvas.draw_idle()
        self.last_data1checksum = checksum(self.data1)
        plt.pause(0.001)
    
        
    
    def reinit_fig2(self):
        # Redraw blank fig2 before polling ADC
        self.data2_all  = [ [-1], [], [], [] ]
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
        # self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)
    
    
    def update_fig2data(self, data=None):
        if type(data) != type(None):
            # Passed previously recorded data
            ts, v, i = data
            idxs = [i for i, _ in enumerate(ts)]
            self.lastdata2checksum = checksum([idxs, ts])
            self.data2_all = [idxs, ts, v, i]
            self._update_fig2(idxs, ts, v, i)
            return self.data2_all
         
        # Updating with new data    
        dat = self.master.ADC.pollingdata.copy()
        if len(dat) != 4: 
            print(dat)
            return
        idxs, ts, ch1, ch2 = dat
        if idxs[-1] < self.data2_all[0][-1]:
            # Reset figure
            self.reinit_fig2()
            
        self.lastdata2checksum = checksum([idxs, ts])
        
        # Determine new points to add
        old_idx = self.data2_all[0].copy()
        startpoint = min([i for i, val in enumerate(idxs)
                                  if val > old_idx[-1]])
        
        for i, (l, new_l) in enumerate(zip(self.data2_all, dat)):
            self.data2_all[i] += new_l[startpoint:]
        
        return self.data2_all
    


    def update_fig2(self, undersample_freq=10):
        # Called by ADC polling
        if self.master.ADC.pollingcount != self.adc_polling_count:
            # Check if new polling has started
            self.adc_polling_count = self.master.ADC.pollingcount
            self.reinit_fig2()
        
        if self.isADCpolling():
            try:
                idxs, ts, ch1, ch2 = self.update_fig2data()
            except Exception as e:
                print(f'Error in Plotter.update_fig2data(): {e}')
                return
            
            self._update_fig2(idxs, ts, ch1, ch2, undersample_freq)
            
    
    
    def _update_fig2(self, idxs, ts, ch1, ch2, undersample_freq=10):

            xval, yval, xaxlabel, yaxlabel = get_axval_axlabels(
                                            self.master.GUI.fig2selection.get()
                                            )
            
            d = {'t': ts,
                 'ch1': ch1,
                 'ch2': ch2
                 }
            
            x = d[xval]
            y = d[yval]
            
            data_freq = 1/np.mean(np.diff(ts))
            desired_freq = undersample_freq
            undersample_factor = int(data_freq//desired_freq)
                        
            def average(arr, n):
                if n < 2:
                    return arr
                # Undersample arr by averaging over n pts
                end =  n * int(len(arr)/n)
                return np.mean(arr[:end].reshape(-1, n), 1)
            
            plotx = average(np.array(x), undersample_factor)
            ploty = average(np.array(y), undersample_factor)
            
            self.ln.set_data(plotx, ploty)
            self.set_axlim('fig2', 
                           *get_plotlim(plotx, ploty)
                           )
            self.ax2.draw_artist(self.ln)
            # self.ax2.draw_artist(self.ln2)
            self.fig2.tight_layout()
            self.fig2.canvas.draw_idle()
            # self.data2plot = [idx, x, y, y2]
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
        
        
        
            
        
    



