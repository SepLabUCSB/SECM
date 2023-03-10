import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from utils.utils import Logger


def checksum(data):
    # TODO: make this simpler
    if type(data) == np.ndarray:
        # Heatmap type data
        return data.sum()
    if type(data) == list:
        # CV curve type data
        # From polling ADC, of form [ [idxs], [times], [*data] ]
        data = [l for l in data if 
                len(np.array(l)) != 0]
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


def get_clim(arr):
    # Return minimum and maximum values of array 
    # (plus some padding) which will be used to define
    # min and max values on the heatmap color scale.
    arr = [val for val in np.array(arr).flatten()
           if val != 0]
    avg = np.average(arr)
    std = np.std(arr)
    
    if abs(std/avg) < 0.1:
        std = 0.1*abs(avg)
    
    minval = avg - 2*std
    maxval = avg + 2*std
    
    return minval, maxval



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


class RectangleSelector:
    '''
    Class which draws a rectangle on the heatmap based on the user
    clicking and dragging. Rectangle is used to zoom in to the 
    selected region.
    '''
    
    def __init__(self, Plotter, fig, ax):
        self.Plotter = Plotter
        self.fig = fig
        self.ax  = ax
        
        self.bg      = None
        self.clicked = False
        
        self.rect = matplotlib.patches.Rectangle((0,0), 0, 0, fill=0,
                                                 edgecolor='red', lw=2)
        self.ax.add_artist(self.rect)
        
        
    def connect(self):
        self.clickedcid = self.fig.canvas.mpl_connect('button_press_event',
                                                      self.on_press)
        self.releasecid = self.fig.canvas.mpl_connect('button_release_event',
                                                      self.on_release)
        self.dragcid    = self.fig.canvas.mpl_connect('motion_notify_event',
                                                      self.on_drag)
    
    def disconnect(self):
        for cid in (self.clickedcid, self.releasecid, self.dragcid):
            self.fig.canvas.mpl_disconnect(cid)
        # Give control back to Plotter
        self.Plotter.connect_cids()
    
    def clear(self):
        self.rect.set_width(0)
        self.rect.set_height(0)
        self.fig.canvas.draw()
        plt.pause(0.001)
    
    def make_rectangle(self, loc1, loc2):
        x1, y1 = loc1
        x2, y2 = loc2
        width  = x2 - x1
        height = y2 - y1
        self.rect.set_x(x1)
        self.rect.set_y(y1)
        self.rect.set_width(width)
        self.rect.set_height(height)
        
        # Redraw with blitting
        self.rect.set_animated(True)
        self.fig.canvas.draw()
        self.bg = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        
        self.ax.draw_artist(self.rect)
        self.fig.canvas.blit(self.ax.bbox)
    
    def get_coords(self):
        x = self.rect.get_x()
        y = self.rect.get_y()
        h = self.rect.get_height()
        w = self.rect.get_width()
        corners = [
            (x  , y),
            (x+w, y),
            (x  , y+h),
            (x+w, y+h)
            ]
        return corners
    
    
    def snap_to_grid(self):
        '''
        snap to nearest coordinates on the grid and 
        make it square
        '''
        gridpts = self.Plotter.master.expt.get_loc_data()
        delta = abs(gridpts[0][0][0] - gridpts[0][1][0])
        corners = self.get_coords()
        corners.sort()
        nearest_points = []
        for corner in corners:
            nearest = self.Plotter.master.expt.get_nearest_datapoint(corner[0], 
                                                                     corner[1])
            x0, y0, _ = nearest.loc
            nearest_points.append( (x0, y0) )
        
        nearest_points.sort() # in order [(0,0), (0,1), (1,0), (1,1)]

        x, y = nearest_points[0]
        w    = nearest_points[3][0] - x
        h    = nearest_points[3][1] - y
        w = h = max(w, h) # make it a square            
        self.make_rectangle( (x, y), (x+w, y+h) )
        return
    
        
    def on_press(self, event):
        # click
        if event.inaxes != self.ax:
            return
        self.clicked = True
        self.loc1 = (event.xdata, event.ydata)
    
    def on_release(self, event):
        # release
        self.snap_to_grid()
        self.clicked = False
        self.disconnect()
    
    def on_drag(self, event):
        # drag rectangle
        if (not self.clicked or event.inaxes != self.ax):
            return
        self.loc2 = (event.xdata, event.ydata)
        self.make_rectangle(self.loc1, self.loc2) 



class Plotter(Logger):
    
    def __init__(self, master, fig1, fig2):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.adc_polling = True
        self.adc_polling_count = 0
        self.FIG2_FORCED = False
        
        self.fig1 = fig1
        self.fig2 = fig2
        self.ax1  = fig1.gca()
        self.ax2  = fig2.gca()
        
        self.data1 = np.array([0,])
        self.data2 = [ [-1], [], [], [] ] #keep track of all fig2 data for later replotting
        
        self.last_data1checksum = checksum(self.data1)
        self.last_data2checksum = checksum(self.data2)
        

        # Initialize heatmap
        self.image1 = self.ax1.imshow(np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32), cmap='afmhot', origin='upper')
        self.fig1.colorbar(self.image1, ax=self.ax1, shrink=0.5,
                           pad=0.02, )
        self.ax1.set_xlabel(r'$\mu$m')
        self.ax1.set_ylabel(r'$\mu$m')
        self.fig1.canvas.draw()
        self.fig1.tight_layout()
        self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.ax1.draw_artist(self.image1)
        plt.pause(0.001)
        
        
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
        
        
        self.connect_cids()
        self.RectangleSelector = RectangleSelector(self, self.fig1, self.ax1)
        
    
    def connect_cids(self):
        self.cid1 = self.fig1.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
        self.cid2 = self.fig2.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
    
    def disconnect_cids(self):
        for cid in (self.cid1, self.cid2):
            self.fig2.canvas.mpl_disconnect(cid)
    
    
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
            self.update_fig2data(closest_datapoint.get_data(),
                                 sample_freq=10000)
            x0, y0, _ = closest_datapoint.loc
        return 
    
    
    def update_heatmap(self, option=None, value=None):
        # Called from GUI by changing view selector
        expt = self.master.expt
        pts = []
        
        if option == value == None:
            option = self.master.GUI.heatmapselection.get()
            value = self.master.GUI.HeatMapDisplayParam.get('1.0', 'end')
        
        if option == 'Max. current':
            pts = expt.get_heatmap_data('max')
        if option == 'Current @ ... (V)':
            try:
                value = float(value)
                pts = expt.get_heatmap_data('val_at', value)
            except:
                return
        if option == 'Z height':
            pts = expt.get_heatmap_data('z')
        if option == 'Avg. current':
            pts = expt.get_heatmap_data('avg')
        
        if len(pts) > 0:
            self.data1 = pts #will update plot automatically
        return
    
    
    def heatmap_zoom(self):
        self.disconnect_cids()
        self.RectangleSelector.connect() 
        # Plotter regains control of mouse inputs 
        # on RectangleSelector.disconnect()
        return
     
    
    def isADCpolling(self):
        self.adc_polling = self.master.ADC.isPolling()
        return self.adc_polling
        
   
    def update_figs(self, **kwargs):
        # Called every 100 ms by TK mainloop.
        # Check if data has updated. If so, plot it to
        # the appropriate figure.
        
        pollingData = self.master.ADC.pollingdata
        if checksum(self.data1) != self.last_data1checksum:
            self.update_fig1()
        
        if checksum(pollingData) != self.last_data2checksum:
            self.update_fig2()        
        
        self.master.GUI.root.after(100, self.update_figs)
        return
    
    
    def set_axlim(self, fig, xlim, ylim):
        if fig == 'fig1':
            self.ax1lim = (xlim, ylim)
            self.ax1.set_xlim(xlim)
            self.ax1.set_ylim(ylim)
        if fig == 'fig2':
            self.ax2lim = (xlim, ylim)
            self.ax2.set_xlim(xlim)
            self.ax2.set_ylim(ylim)    
    
    
    def update_fig1(self, **kwargs):
        # Fig 1 - SECM heatmap
        arr = self.data1[::-1]
        self.image1.set_data(arr)
        minval, maxval = get_clim(arr)
        self.image1.set(clim=( minval, maxval) )
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
        self.FIG2_FORCED = False
        self.data2 = [ [-1], [], [], [] ]
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
    
    
    def update_fig2data(self, data=None, sample_freq=10):
        # Called either by loading a previously recorded data point 
        # (passes data [ idxs, ts, ch1, ch2 ] to this func) or from 
        # new ADC polling data.
        
        if type(data) != type(None):
            # Passed previously recorded data
            self.FIG2_FORCED = True
            if len(data) == 3:
                ts, v, i = data
                idxs = [i for i, _ in enumerate(ts)]
            elif len(data) == 4:
                idxs, ts, v, i = data
            self.lastdata2checksum = checksum(data)
            self.data2 = [idxs, ts, v, i]
            self._update_fig2(idxs, ts, v, i, sample_freq = 1000)
            return self.data2, 10000
        
        if self.FIG2_FORCED:
            return self.data2, 10000
            
        # Updating with new data    
        dat = self.master.ADC.pollingdata.copy()
        if type(dat) != list:
            return [[-1], [], [], []], sample_freq
        
        gain = 1e9 * self.master.GUI.amp_params['float_gain']
        
        idxs, ts, ch1, ch2 = dat
        ch1 = [v/10 for v in ch1] # Analog voltage output gets 
                                  # multiplied by 10
        ch2 = [v/gain for v in ch2] # Convert V --> pA
        
        dat = idxs, ts, ch1, ch2
        
        self.lastdata2checksum = checksum(dat)
        
        # Determine new points to add
        old_idx = self.data2[0].copy()
        startpoint = min([i for i, val in enumerate(idxs)
                                  if val > old_idx[-1]])
        
        for i, (l, new_l) in enumerate(zip(self.data2, dat)):
            self.data2[i] += new_l[startpoint:]
        
        return self.data2, sample_freq
    


    def update_fig2(self, sample_freq=10):
        # Called by ADC polling
        if self.master.ADC.pollingcount != self.adc_polling_count:
            # Check if new polling has started
            self.adc_polling_count = self.master.ADC.pollingcount
            self.reinit_fig2()
        
        if self.isADCpolling():
            data, sample_freq = self.update_fig2data(sample_freq=sample_freq)            
            self._update_fig2(*data, sample_freq)
            
    
    
    def _update_fig2(self, idxs, ts, ch1, ch2, sample_freq=10):
        # Function for redrawing fig 2 data
        
        # Determine what to plot based on user selection in GUI
        xval, yval, xaxlabel, yaxlabel = get_axval_axlabels(
                                        self.master.GUI.fig2selection.get()
                                        )
        
        # Get the correct data
        d = {'t': ts,
             'ch1': ch1,
             'ch2': ch2
             }
        x = d[xval]
        y = d[yval]
        
        # Undersample data if desired
        # (i.e. HEKA records CV at 10 Hz, but ADC samples at 234 Hz -
        #  we see every step in the digital CV and pick up excess noise
        #  as well as current spikes.)
        
        def average(arr, n):
            if n < 2:
                return arr
            # Undersample arr by averaging over n pts
            end =  n * int(len(arr)/n)
            return np.mean(arr[:end].reshape(-1, n), 1)
        
        if len(x) > sample_freq:
            data_freq = 1/np.mean(np.diff(ts))
            undersample_factor = int(data_freq//sample_freq)
            
            plotx = average(np.array(x), undersample_factor)
            ploty = average(np.array(y), undersample_factor)
        
        else:
            plotx = x
            ploty = y
           
        
        # Finally, plot the data
        self.ln.set_data(plotx, ploty)
        self.set_axlim('fig2', 
                       *get_plotlim(plotx, ploty)
                       )
        self.ax2.set_xlabel(xaxlabel)
        self.ax2.set_ylabel(yaxlabel)
        self.ax2.draw_artist(self.ln)
        self.fig2.tight_layout()
        self.fig2.canvas.draw_idle()
        plt.pause(0.001)
        
    
    
        
    
        
        
        
            
        
    



