import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np
from tkinter import *
from tkinter.ttk import *
from utils.utils import Logger, nearest
from modules.DataStorage import (ADCDataPoint, CVDataPoint, 
                                 SinglePoint)

# For time domain plotting
x_maxes = [5, 10, 30, 60] + [120*i for i in range(1, 60)]

def checksum(data):
    # TODO: make this simpler
    
    if isinstance(data, ADCDataPoint):
        return sum(data.data[0])
    
    if isinstance(data, CVDataPoint):
        return sum(data.data[0])
    
    if type(data) == np.ndarray:
        # Heatmap type data
        try:
            return data.flatten().sum()
        except:
            return 0
    if type(data) == list:
        # CV curve type data
        # From polling ADC, of form [ [idxs], [times], [*data] ]
        data = [l for l in data if 
                len(np.array(l)) != 0]
        return np.array(data).flatten().sum()


def get_plotlim(xdata, ydata):
    if len(xdata) == 0 or len(xdata) == 1:
        return ((0,0.1), (0,0.1))
    lim = (
     (min(xdata) - 0.05*abs(min(xdata)),
      max(xdata) + 0.05*abs(max(xdata))
      ),
     (min(ydata) - 0.05*abs(min(ydata)),
      max(ydata) + 0.05*abs(max(ydata))
      )
     )
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


def set_cbar_ticklabels(cbar, clim):
    # m0=int(np.floor(arr.min()))            # colorbar min value
    # m1=int(np.ceil(arr.max()))             # colorbar max value
    m0 = min(clim)
    m1 = max(clim)
    num_ticks = 5
    ticks = np.linspace(m0, m1, num_ticks)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([unit_label(t) for t in ticks])


def unit_label(d:float):
    '''
    Returns value as string with SI unit prefix
    
    e.g. unit_label(1e-9) --> '1 n'
         unit_label(7.7e-10): --> '770 p'
    '''
    inc_prefixes = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
    dec_prefixes = ['m', 'µ', 'n', 'p', 'f', 'a', 'z', 'y']

    if d == 0:
        return f'0.0'

    degree = int(np.floor(np.log10(np.fabs(d)) / 3))

    prefix = ''

    if degree != 0:
        sign = degree / np.fabs(degree)
        if sign == 1:
            if degree - 1 < len(inc_prefixes):
                prefix = inc_prefixes[degree - 1]
            else:
                prefix = inc_prefixes[-1]
                degree = len(inc_prefixes)

        elif sign == -1:
            if -degree - 1 < len(dec_prefixes):
                prefix = dec_prefixes[-degree - 1]
            else:
                prefix = dec_prefixes[-1]
                degree = -len(dec_prefixes)

        scaled = float(d * pow(1000, -degree))

        s = f"{scaled:0.1f} {prefix}"

    else:
        s = f"{d:0.1f}"
    return s


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
            _, nearest = self.Plotter.master.expt.get_nearest_datapoint(corner[0], 
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
        
        self.minval = None    # Min/ max values for heatmap
        self.maxval = None    # Set as tk.StringVar in popup window

        self.rect = matplotlib.patches.Rectangle((0,0), 0, 0, fill=0,
                                                 edgecolor='red', lw=2)
        self.ax1.add_artist(self.rect)

        self.init_heatmap()
        self.init_echem_fig()

        self.connect_cids()
        self.RectangleSelector = RectangleSelector(self, self.fig1, self.ax1)
        
        
     
       
     
    ###########################
    #### GENERAL FUNCTIONS ####
    ###########################
    
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
            idx, closest_datapoint = self.select_datapoint(x, y)
            self.set_echemdata(closest_datapoint, sample_freq=10000)
            x0, y0, z0 = closest_datapoint.loc
            if type(z0) == tuple:
                z0 = z0[0] # Handle early bug in some saved data
            val = self.data1.flatten()[idx]
            print(f'Point: ({x0:0.2f}, {y0:0.2f}, {z0:0.2f}), Value: {unit_label(val)}')
        if event.inaxes == self.ax2:
            x, y = event.xdata, event.ydata
            print(f'({x:0.3f}, {unit_label(y)})')
        
        return 
    
    
    # Called every 100 ms by TK mainloop.
    # Check if data has updated. If so, plot it to
    # the appropriate figure.
    def update_figs(self, **kwargs):
        
        pollingData = self.master.ADC.pollingdata
        try:
            if checksum(self.data1) != self.last_data1checksum:
                self.update_fig1()
        except Exception as e:
            self.log(f'Error updating heatmap!')
            self.log(e)
        
        try:
            if checksum(pollingData) != self.last_data2checksum:
                if (hasattr(self, 'fig2data') and 
                    id(pollingData) != id(self.fig2data) and
                    not self.FIG2_FORCED):
                    self.init_echem_fig()
                self.update_fig2()       
        except Exception as e:
            self.log(f'Error updating echem figure!')
            self.log(e)
        
        self.master.GUI.root.after(100, self.update_figs)
        return
    
    
    def set_axlim(self, fig, xlim, ylim):
        if ((xlim[1] == xlim[0]) or (ylim[1] == ylim[0])):
            return
        
        if fig == 'fig1':
            self.ax1lim = (xlim, ylim)
            self.ax1.set_xlim(xlim)
            self.ax1.set_ylim(ylim)
        if fig == 'fig2':
            self.ax2lim = (xlim, ylim)
            self.ax2.set_xlim(xlim)
            self.ax2.set_ylim(ylim) 
    
    
    
    
    ###########################
    #### HEATMAP FUNCTIONS ####
    ###########################
    
    # Initialize heatmap
    def init_heatmap(self):
        self.image1 = self.ax1.imshow(np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32), cmap='afmhot', origin='upper')
        cb = self.fig1.colorbar(self.image1, ax=self.ax1, shrink=0.5,
                                pad=0.02, format="%0.1e")
        cb.ax.tick_params(labelsize=14)
        
        self.ax1.set_xlabel(r'$\mu$m')
        self.ax1.set_ylabel(r'$\mu$m')
        self.ax1.spines['right'].set_visible(True)
        self.ax1.spines['top'].set_visible(True)
        self.fig1.canvas.draw()
        self.fig1.tight_layout()
        self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.rect.set_bounds(0,0,0,0)
        self.ax1.draw_artist(self.image1)
        self.ax1.draw_artist(self.rect)
        plt.pause(0.001)
        return
    
    
    # Called from GUI by changing view selector
    # Update what is shown on the heatmap
    def update_heatmap(self, option=None, value=None):
        expt = self.master.expt
        pts = []
        
        if option == value == None:
            option = self.master.GUI.heatmapselection.get()
            value = self.master.GUI.HeatMapDisplayParam.get('1.0', 'end')
        
        if option == 'Max. current':
            pts = expt.get_heatmap_data('max')
        if option == 'Current @ ... (V)':
            try:
                value = float(value.replace('\n', ''))
                pts = expt.get_heatmap_data('val_at', value)
            except:
                return
        if option == 'Current @ ... (t)':
            try:
                value = float(value.replace('\n', ''))
                pts = expt.get_heatmap_data('val_at_t', value)
            except:
                return
        if option == 'Z height':
            pts = expt.get_heatmap_data('z')
        if option == 'Avg. current':
            pts = expt.get_heatmap_data('avg')
        
        if len(pts) > 0:
            self.data1 = pts #will update plot automatically
        return
    
    
    # Set new data on heatmap
    def update_fig1(self, **kwargs):
        arr = self.data1[::-1]
        self.image1.set_data(arr)
        
        if self.minval and self.maxval:
            minval = float(self.minval.get())
            maxval = float(self.maxval.get())
        else:
            minval, maxval = get_clim(arr)
            
        self.image1.set(clim=( minval, maxval) )
        set_cbar_ticklabels(self.image1.colorbar, [minval, maxval])
        
        left, right = self.ax1lim[0][0], self.ax1lim[0][1]
        bottom, top = self.ax1lim[1][0], self.ax1lim[1][1]
        self.image1.set_extent((left, right, bottom, top))
        self.ax1.draw_artist(self.image1)
        self.fig1.canvas.draw_idle()
        self.last_data1checksum = checksum(self.data1)
        plt.pause(0.001)
    
    
    def select_datapoint(self, event_x, event_y):
        '''
        Data point locations are offset from pixel locations and
        get stretched to fit the image grid
        
        Returns selected Datapoint object and draws a box on the heatmap
        '''
        
        datapts = self.master.expt.get_loc_data()
        
        left, right = self.ax1lim[0][0], self.ax1lim[0][1]
        pts_in_row = len(datapts[0]) + 1
        x_bounds = [n for n in np.linspace(left, right, pts_in_row)]
        y_bounds = [n for n in np.linspace(left, right, pts_in_row)]
        delta = x_bounds[1] - x_bounds[0]
        
        for xline in x_bounds:
            if event_x >= xline:
                continue
            break
        
        for yline in y_bounds:
            if event_y >= yline:
                continue
            break
        
        # xline is top and yline is left side of pixel
        # Draw rectangle around the selected point
        self.rect.set_x(xline - delta)
        self.rect.set_y(yline - delta)
        self.rect.set_width(delta)
        self.rect.set_height(delta)
        self.ax1.draw_artist(self.rect)
        self.fig1.canvas.draw_idle()
        
        
        def pt_in_rect(x, y, xline, yline, delta):
            if (x <= xline) and (x >= xline-delta):
                if (y <= yline) and (y >= yline-delta):
                    return True
            return False
        
        for row in datapts:
            for (x, y) in row:
                if pt_in_rect(x, y, xline, yline, delta):
                    return self.master.expt.get_nearest_datapoint(x, y)

    
    
    # Enter heatmap zoom mode
    def heatmap_zoom(self):
        self.disconnect_cids()
        self.RectangleSelector.connect() 
        # Plotter regains control of mouse inputs 
        # on RectangleSelector.disconnect()
        return
    
    # Heatmap line scan mode
    def heatmap_line_scan(self):
        pass
    
    
    # Popup to set color map
    def heatmap_color_popup(self):
        cmaps = ['afmhot', 'hot', 'gist_gray', 'viridis', 'plasma', 'inferno', 
                 'magma', 'cividis','Greys', 'Purples', 'Blues', 'Greens', 
                 'Oranges', 'Reds', 'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 
                 'BuPu','GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']
        
        popup = Toplevel()
        frame = Frame(popup)
        frame.grid(row=0, column=0)
        
        self.cmap = StringVar()
        OptionMenu(frame, self.cmap, cmaps[0], *cmaps, 
                   command=self.update_cmap).grid(row=0, column=1, columnspan=2)
        
        self.cmap_minval = StringVar(value='0')
        self.cmap_maxval = StringVar(value='1')
        Label(frame, text='Min: ').grid(row=1, column=0, sticky=(W,E))
        Entry(frame, textvariable=self.cmap_minval, width=3).grid(row=1, column=1, sticky=(W,E))
        Label(frame, text='Max: ').grid(row=1, column=2, sticky=(W,E))
        Entry(frame, textvariable=self.cmap_maxval, width=3).grid(row=1, column=3, sticky=(W,E))
        Button(frame, text='Apply', command=self.update_cmap).grid(row=2, column=1, columnspan=2)
    
    
    def update_cmap(self, _=None):
        cmap = self.cmap.get()
        base_cmap = matplotlib.cm.get_cmap(cmap, 1024)
        
        vmin = float(self.cmap_minval.get())
        vmax = float(self.cmap_maxval.get())
        
        if (vmin < 0) or (vmin > 1) or (vmax < 0) or (vmax > 1):
            print('\nInvalid input! Min and max must be between 0 and 1.\n')
            return
        
        new_cmap = matplotlib.colors.ListedColormap(
            base_cmap(
                np.linspace(vmin, vmax, 512)
                )
            )
            
        self.image1.set(cmap = new_cmap)
        self.update_fig1()
    
    
    # Popup to set min/max scale
    def heatmap_scale_popup(self):
        data = self.data1.flatten()
        data = [d for d in data if d != 0]
        print(f'\nMax: {max(data):0.4g}')
        print(f'Min: {min(data):0.4g}')
        print(f'Avg: {np.mean(data):0.4g}')
        print(f'Std: {np.std(data):0.4g}\n')
        
        self.popup_window = Toplevel()
        frame  = Frame(self.popup_window)
        frame.grid(row=0, column=0)
        
        minval, maxval = get_clim(self.data1[::-1])
        
        self.minval = StringVar(value=f'{minval:0.2g}')
        self.maxval = StringVar(value=f'{maxval:0.2g}')
        
        Label(frame, text='Scale: ').grid(row=0, column=0, sticky=(W,E))
        Button(frame, text='-', command=self.zoom_out).grid(row=0, column=1, sticky=(W,E))
        Button(frame, text='+', command=self.zoom_in).grid(row=0, column=2, sticky=(W,E))
        
        Entry(frame, textvariable=self.minval, width=5).grid(row=1, column=1, sticky=(W,E))
        Entry(frame, textvariable=self.maxval, width=5).grid(row=1, column=2, sticky=(W,E))
        
        Button(frame, text='Apply', command=self.update_fig1).grid(row=3, column=1, sticky=(W,E))
        Button(frame, text='Reset', command=self.cancel_popup).grid(row=3, column=2, sticky=(W,E))
        
        
    def zoom_in(self):
        minval = float(self.minval.get())
        maxval = float(self.maxval.get())
        mean = (maxval + minval) / 2
        diff = (maxval - minval) / 2
        diff *= 0.5
        new_minval = mean - diff
        new_maxval = mean + diff
        self.minval.set(f'{new_minval:0.3g}')
        self.maxval.set(f'{new_maxval:0.3g}')   
        self.update_fig1()
    
    def zoom_out(self):
        minval = float(self.minval.get())
        maxval = float(self.maxval.get())
        mean = (maxval + minval) / 2
        diff = (maxval - minval) / 2
        diff *= 1.5
        new_minval = mean - diff
        new_maxval = mean + diff
        self.minval.set(f'{new_minval:0.3g}')
        self.maxval.set(f'{new_maxval:0.3g}') 
        self.update_fig1()
        
        
    def cancel_popup(self):
        # Reset minval and maxval to None
        self.minval = None
        self.maxval = None
        self.update_fig1()
        

    

    #############################
    #### ECHEM FIG FUNCTIONS ####
    #############################
    
    # Draw blank echem figure
    def init_echem_fig(self):
        self.FIG2_FORCED = False
        self.data2 = [ [-1], [], [], [] ]
        self.ax2.cla()
        self.ln, = self.ax2.plot([], [])
        self.ln2, = self.ax2.plot([], [])
        self.ax2.set_xlabel('V')
        self.ax2.set_ylabel('I')
        self.fig2.canvas.draw()
        self.fig2.tight_layout()
        self.ax2bg = self.fig2.canvas.copy_from_bbox(self.ax2.bbox)
        self.ax2.draw_artist(self.ln)
        # self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)

    
    
    def update_fig2(self):
        DATAPOINT = self.master.ADC.pollingdata
        self.last_data2checksum = checksum(DATAPOINT)
        self.set_echemdata(DATAPOINT)

    
    def set_echemdata(self, DATAPOINT, sample_freq=10):
        # Determine what to plot
        _, _, xval, yval = get_axval_axlabels(
                                self.master.GUI.fig2selection.get()
                                )
        
        # Get the data
        if isinstance(DATAPOINT, ADCDataPoint):
            if self.FIG2_FORCED:
                # Don't update with new ADC data
                return
            t, V, I = DATAPOINT.get_data()
            V = np.array(V)/10
            I = np.array(I)/DATAPOINT.gain
            if not self.rect.get_width() == 0:
                # Unselect last point
                self.rect.set_bounds(0,0,0,0)
                self.ax1.draw_artist(self.rect)
                self.fig1.canvas.draw_idle()
            
        elif isinstance(DATAPOINT, CVDataPoint):
            t, V, I = DATAPOINT.get_data()
            self.FIG2_FORCED = True
        
        elif isinstance(DATAPOINT, SinglePoint):
            t, V, I = [0], [0], [0]
        
        else:
            print(type(DATAPOINT))
        
        d = {'t': t,
             'V': V,
             'I': I}
        
        t = d['t']
        x = d[xval]
        y = d[yval]
        
        
        # Plot the data
        # t always used to determine sampling frequency
        self.draw_echemfig(t, x, y, sample_freq)
        self.ax2.set_xlabel(xval)
        self.ax2.set_ylabel(yval)
        self.fig2.tight_layout()
        self.fig2.canvas.draw_idle()
        plt.pause(0.001)
        
        self.fig2data = DATAPOINT
        return
    

    def draw_echemfig(self, t, x, y, undersample_freq=10):
        # Undersample data if desiredd
        # (i.e. HEKA records CV at 10 Hz, but ADC samples at 234 Hz -
        #  we see every step in the digital CV and pick up excess noise
        #  as well as current spikes.)
                
        def average(arr, n):
            if n < 2:
                return arr
            # Undersample arr by averaging over n pts
            end =  n * int(len(arr)/n)
            return np.mean(arr[:end].reshape(-1, n), 1)
        
        if len(x) > undersample_freq:
            data_freq = 1/np.mean(np.diff(t))
            undersample_factor = int(data_freq//undersample_freq)
            
            plotx = average(np.array(x), undersample_factor)
            ploty = average(np.array(y), undersample_factor)
        else:
            plotx = x
            ploty = y
        
        self.ln.set_data(plotx, ploty)
        self.set_axlim('fig2', *get_plotlim(plotx, ploty) )
        return True

            
        
        
  
    

