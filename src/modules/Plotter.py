import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import numpy as np
import os
from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
from ..utils.utils import Logger, nearest
from .DataStorage import (ADCDataPoint, CVDataPoint, 
                                 SinglePoint, EISDataPoint, PointsList)

# Import any analysis functions here and add to Plotter.set_analysis_popup()!
from ..analysis import analysis_funcs
from ..analysis.analysis_funcs import AnalysisFunctionSelector


# For time domain plotting
x_maxes = [5, 10, 30, 60] + [120*i for i in range(1, 60)]

def checksum(data):
    # TODO: make this simpler
    
    if isinstance(data, ADCDataPoint):
        return sum(data.data[0])
    
    if isinstance(data, CVDataPoint):
        return sum(data.data[0])
    
    if isinstance(data, EISDataPoint):
        return sum(data.data[1])
    
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
    if len(arr) == 0:
        return -1, 1
    avg = np.average(arr)
    std = np.std(arr)
    
    if abs(std/avg) < 0.1:
        std = 0.1*abs(avg)
    
    minval = avg - 2*std
    maxval = avg + 2*std
    
    return minval, maxval


def set_cbar_ticklabels(cbar, clim, n_ticks=5):
    # m0=int(np.floor(arr.min()))            # colorbar min value
    # m1=int(np.ceil(arr.max()))             # colorbar max value
    m0 = min(clim)
    m1 = max(clim)
    ticks = np.linspace(m0, m1, n_ticks)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([unit_label(t) for t in ticks])


def unit_label(d:float,dec=0):
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

    if abs(degree) > 1:
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

        s = f"{scaled:0.{dec}f}".rjust(4, ' ') + f" {prefix}"

    else:
        s = f"{d:0.2f}".rjust(4, ' ')
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
        self.analysis_function = analysis_funcs.CV_decay_analysis
        
        self.fig1 = fig1
        self.fig2 = fig2
        self.ax1  = fig1.gca()
        self.ax2  = fig2.gca()
        
        self.data1 = np.array([0,])
        self.data2 = [ [-1], [], [], [] ] #keep track of all fig2 data for later replotting
        self.fig2DataPoint = None  # Keep track of DataPoint object fig 2 is plotting from. 
                                   # Can be a PointsList. Not necessarily the same as self.fig2data,
                                   # which is what is actually plotted to the axes
        
        self.last_data1checksum = checksum(self.data1)
        self.last_data2checksum = checksum(self.data2)
        
        self.force_minmax = False

        self.rect = matplotlib.patches.Rectangle((0,0), 0, 0, fill=0,
                                                 edgecolor='red', lw=2)
        self.ax1.add_artist(self.rect)
        
        self.fig2_extra_artists = [] # Store any extra artists given by DataPoint's analysis

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
            self.master.ImageCorrelator.draw_on_pt(x0, y0)
            print(f'Point: ({x0:0.2f}, {y0:0.2f}, {z0:0.2f}), Value: {unit_label(val, dec=3)}')
        if event.inaxes == self.ax2:
            x, y = event.xdata, event.ydata
            print(f'({unit_label(x, dec=3)}, {unit_label(y, dec=3)})')
        
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
        
        self.master.GUI.notebook_frame.after(100, self.update_figs)
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
        self.data1 = np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32)
        self.image1 = self.ax1.imshow(self.data1, cmap='viridis', origin='upper')
        cb = self.fig1.colorbar(self.image1, ax=self.ax1, shrink=0.5,
                                pad=0.02, format="%0.1e")
        cb.ax.tick_params(labelsize=14)
        
        self.ax1.set_xlabel(r'$\mu$m')
        self.ax1.set_ylabel(r'$\mu$m')
        self.ax1.spines['right'].set_visible(True)
        self.ax1.spines['top'].set_visible(True)
        self.fig1.canvas.draw()
        self.fig1.tight_layout()
        # self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
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
            value = self.master.GUI.HeatMapDisplayParam.get()
        
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
        if option == 'Analysis func.':
            if not self.analysis_function:
                print('No analysis function selected!')
                return
            value = value.replace('\n', '')
            
            pts = expt.do_analysis(self.analysis_function, value)            
                    
                      
        if len(pts) > 0:
            self.data1 = pts #will update plot automatically
        return
    
    
    # Set new data on heatmap
    def update_fig1(self, **kwargs):
        arr = self.data1[::-1]
        self.image1.set_data(arr)
        
        if self.force_minmax:
            minval = float(self.master.GUI.heatmap_min_val.get())
            maxval = float(self.master.GUI.heatmap_max_val.get())
        else:
            minval, maxval = get_clim(arr)
            self.update_minmaxval_fields()
            
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
        
        pt_idx_selection = int(self.master.GUI.fig2ptselection.get())
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
                    return self.master.expt.get_nearest_datapoint(x, y, 
                                                                  pt_idx=pt_idx_selection)

    
    
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
           
    
    def update_cmap(self, _=None):
        cmap = self.master.GUI.heatmap_cmap.get()
        base_cmap = matplotlib.cm.get_cmap(cmap, 1024)
        
        vmin = float(self.master.GUI.heatmap_cmap_minval.get())
        vmax = float(self.master.GUI.heatmap_cmap_maxval.get())
        
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
            
    
    def update_minmaxval_fields(self):
        minval, maxval = get_clim(self.data1[::-1])
        self.master.GUI.heatmap_min_val.set(f'{minval:0.3g}')
        self.master.GUI.heatmap_max_val.set(f'{maxval:0.3g}') 
    
    def apply_minmax_fields(self):
        self.force_minmax = True
        self.update_fig1()
        
    def zoom_in(self):
        'Make the heatmap color scale smaller by 10%'
        self._zoom_bound('upper', 'subtract')
        self._zoom_bound('lower', 'add')
        self.update_fig1()
    
    def zoom_out(self):
        'Make the heatmap color scale larger by 10%'
        self._zoom_bound('upper', 'add')
        self._zoom_bound('lower', 'subtract')
        self.update_fig1()
    
    def zoom_lower_add(self):
        'Add 10% to lower heatmap color scale bound'
        self._zoom_bound('lower', 'add')
        self.update_fig1()
    
    def zoom_lower_subt(self):
        'Subtract 10% to lower heatmap color scale bound'
        self._zoom_bound('lower', 'subtract')
        self.update_fig1()
    
    def zoom_upper_add(self):
        'Add 10% to upper heatmap color scale bound'
        self._zoom_bound('upper', 'add')
        self.update_fig1()
    
    def zoom_upper_subt(self):
        'Subtract 10% to upper heatmap color scale bound'
        self._zoom_bound('upper', 'subtract')
        self.update_fig1()
    
    def _zoom_bound(self, bound, direction):
        minval = self.master.GUI.heatmap_min_val
        maxval = self.master.GUI.heatmap_max_val
                
        val = minval if bound == 'lower' else maxval
        
        floatval = float(val.get())
        delta = float(maxval.get()) - float(minval.get())
        if direction == 'add':
            floatval += abs(0.1*delta)
        elif direction == 'subtract':
            floatval -= abs(0.1*delta)
        
        val.set(f'{floatval:0.3g}')
        self.force_minmax = True
    
        
    def cancel_popup(self):
        # Reset minval and maxval to None
        self.force_minmax = False
        self.update_fig1()
        self.update_minmaxval_fields()
     
    
    def set_analysis_popup(self):
        # Opens a window where user can choose what function to apply
        # to each datapoint in the heatmap
        if not hasattr(self, 'AnalysisFuncSelector'):
            self.AnalysisFuncSelector = AnalysisFunctionSelector(self.master.GUI.notebook_frame)
        func = self.AnalysisFuncSelector.get_selection()
        self.analysis_function = func

    

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
        self.ax2.set_xscale('linear')
        self.fig2.canvas.draw()
        self.fig2.tight_layout()
        self.clear_fig2_artists()
        self.ax2bg = self.fig2.canvas.copy_from_bbox(self.ax2.bbox)
        self.ax2.draw_artist(self.ln)
        # self.fig2.canvas.blit(self.ax2.bbox)
        plt.pause(0.001)
        
    
    def clear_fig2_artists(self):
        if len(self.fig2_extra_artists) != 0:
            for artist in self.fig2_extra_artists:
                artist.remove()
            self.fig2_extra_artists = []

    
    
    def update_fig2(self):
        DATAPOINT = self.master.ADC.pollingdata
        self.last_data2checksum = checksum(DATAPOINT)
        self.fig2_datapoint = DATAPOINT
        self.set_echemdata(DATAPOINT)

    
    def set_echemdata(self, DATAPOINT, sample_freq=1000):
        # Determine what to plot
        _, _, xval, yval = get_axval_axlabels(
                                self.master.GUI.fig2selection.get()
                                )
        
        self.fig2DataPoint = DATAPOINT
        
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
                
        if isinstance(DATAPOINT, PointsList):
            # Determine which to plot
            selected_idx = self.master.GUI.fig2ptselection.get()
            DATAPOINT = DATAPOINT[selected_idx]
            
        if isinstance(DATAPOINT, CVDataPoint):
            t, V, I = DATAPOINT.get_data()
            self.FIG2_FORCED = True
        
        if isinstance(DATAPOINT, SinglePoint):
            t, V, I = [0], [0], [0]
            
        if isinstance(DATAPOINT, EISDataPoint):
            self.FIG2_FORCED = True
            option = self.master.GUI.EIS_view_selection.get()
            if option == 'Nyquist':
                return self.draw_nyquist(DATAPOINT)
            elif option == '|Z| Bode':
                return self.draw_Bode(DATAPOINT, 'Z')
            elif option == 'Phase Bode':
                return self.draw_Bode(DATAPOINT, 'Phase')
        
        try:
            d = {'t': t,
                 'V': V,
                 'I': I}
        except:
            self.log(f'Plotting error plotting {type(DATAPOINT)}')
        
        t = d['t']
        x = d[xval]
        y = d[yval]
        
        
        # Plot the data
        # t always used to determine sampling frequency
        self.ax2.set_xscale('linear')
        self.draw_echemfig(t, x, y, sample_freq)
        
        # Clear old artists
        self.clear_fig2_artists()
        
        # Draw any extra artists generated by analysis function(s)
        if hasattr(DATAPOINT, 'artists'):
            for artist in DATAPOINT.artists:
                self.ax2.add_artist(artist)
                self.ax2.draw_artist(artist)
                self.fig2_extra_artists.append(artist)
                
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
        self.ln.set_marker('')
        self.set_axlim('fig2', *get_plotlim(plotx, ploty) )
        return True
    
    
    def draw_nyquist(self, EISDataPoint):
        '''
        Make a Nyquist plot on Fig 2 for EIS-type data
        '''
        freqs, _,_,Z = EISDataPoint.data
        x = np.real(Z)
        y = -np.imag(Z)
        
        minimum = min(0, min(min(x), min(y)))
        maximum = max(max(x), max(y))
        maximum += 0.1*maximum
        
        # Clear old artists
        self.clear_fig2_artists()
        
        self.ln.set_data(x, y)
        self.ln.set_marker('o')
        self.ax2.set_xscale('linear')
        self.set_axlim('fig2', (minimum, maximum), (minimum, maximum))
        self.ax2.set_xlabel(r"Z'/ $\Omega$")
        self.ax2.set_ylabel(r"-Z''/ $\Omega$")
        self.ax2.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())
        self.ax2.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
        self.fig2.tight_layout()
        self.fig2.canvas.draw_idle()
        plt.pause(0.001)
        self.fig2data = EISDataPoint
        return
    
    
    def draw_Bode(self, EISDataPoint, option):
        '''
        Make a Bode plot on Fig 2 for EIS-type data
        option = 'Z' or 'Phase'
        '''
        freqs, _, _, Z = EISDataPoint.data
        x  = [float(f) for f in freqs]
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        
        if option == 'Z':
            y = np.abs(Z)
            ylabel = r'|Z|/ $\Omega$'
            self.ax2.set_ylim(
                          min(y) - 0.05*abs(min(y)),
                          max(y) + 0.05*abs(max(y))
                          )
            
        elif option == 'Phase':
            y = np.angle(Z, deg=True)
            ylabel = r'Phase/ $\degree$'
            self.ax2.set_ylim(min(y)-15, max(y)+15)
        
        self.ln.set_data(x,y)
        self.ln.set_marker('o')
        
        self.ax2.set_xscale('log')
        self.ax2.set_xticks([1e-2,1e-1,1e0,1e1,1e2,1e3,1e4,1e5,1e6])
        self.ax2.set_xlim(min(x) - 0.05*min(x), max(x) + 0.05*max(x))
        self.ax2.set_xlabel('Frequency/ Hz')
        self.ax2.set_ylabel(ylabel)
        
        self.clear_fig2_artists()
        
        self.fig2.tight_layout()
        self.fig2.canvas.draw_idle()
        plt.pause(0.001)
        self.fig2data = EISDataPoint
        
        


class FigureExporter():
    
    def __init__(self, GUI):
        self.GUI = GUI
        self.fig = plt.Figure(figsize=(4,4), dpi=100, constrained_layout=True)
        self.fig.add_subplot(111)
        self.ax = self.fig.gca()
        self.dpi = 600
        self.make_popup()
        self.fill_leftframe()
        self.draw()
        
    def make_popup(self):
        self.popup = Toplevel()
        self.leftframe  = Frame(self.popup)
        self.rightframe = Frame(self.popup)
        self.leftframe.grid(row=0, column=0)
        self.rightframe.grid(row=0, column=1)
        FigureCanvasTkAgg(self.fig, master=self.rightframe
                          ).get_tk_widget().grid(row=0, column=0)
        plt.pause(0.001)
        
        
    def fill_leftframe(self):
        pass
    
    def draw(self):
        pass
        
    def save(self):
        path = filedialog.asksaveasfilename(defaultextension='.png')
        if hasattr(self, 'dpi_field'):
            self.dpi = int(self.dpi_field.get())
        self.fig.savefig(path, dpi=self.dpi)
    
    def set_dpi(self, dpi):
        self.dpi = dpi
        
    
    
    


class HeatmapExporter(FigureExporter):
    def __init__(self, GUI, heatmap_data):
        self.data = heatmap_data[::-1]
        self.artists = []
        super().__init__(GUI=GUI)
    
    def fill_leftframe(self):
        # Put relevant buttons in self.leftframe
        frame = self.leftframe
        
        length = self.GUI.master.expt.length
        if not hasattr(self, 'dpi_field'):
            # Will already have these attributes if it's being reinitialized
            self.dpi_field       = StringVar(value='600')
            self.scale           = StringVar(value=str(length))
            self.scalebar_length = StringVar(value=f'{length/4:.0f}')
            self.n_cbar_ticks    = StringVar(value='5')
        
        Label(frame, text='Heatmap Exporter       ').grid(row=0, column=0, columnspan=2)
        Button(frame, text='Redraw', command=self.redraw).grid(row=0, column=2, sticky=(W,E))
        
        Label(frame, text='dpi: ').grid(row=1, column=0, sticky=(W,E))
        Entry(frame, textvariable=self.dpi_field, width=4).grid(row=1, column=1,
                                                                sticky=(W,E))
        Button(frame, text='Save', command=self.save).grid(row=1, column=2, sticky=(W,E))
        
        
        Label(frame, text='Scalebar Length: ').grid(row=2, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.scalebar_length, width=5).grid(
            row=2, column=2, sticky=(W,E))
        
        Label(frame, text='# Colorbar Ticks: ').grid(row=3, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.n_cbar_ticks, width=5).grid(
            row=3, column=2, sticky=(W,E))
        
        return
    
     
    def redraw(self):
        self.ax.clear()
        for artist in self.artists:
            try:
                artist.remove()
            except:
                pass
        self.artists = []
        self.draw()
    
    
    def draw(self):
        image1 = self.ax.imshow(self.data, cmap='viridis', 
                                     origin='upper', extent=[0,1,0,1])
        cb = self.fig.colorbar(image1, ax=self.ax, shrink=0.5,
                                pad=0.02, format="%0.1e")
        cb.ax.tick_params(labelsize=14)
        self.artists.append(cb)
        
        for sp in ['right', 'top', 'left', 'bottom']:
            self.ax.spines[sp].set_visible(True)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        minval = float(self.GUI.heatmap_min_val.get())
        maxval = float(self.GUI.heatmap_max_val.get())
        image1.set(clim=(minval, maxval))
        
        n_ticks = int(self.n_cbar_ticks.get())
        set_cbar_ticklabels(image1.colorbar, [minval, maxval], n_ticks)
        
        cmap = self.get_cmap()
        image1.set(cmap = cmap)
        
        self.fig.canvas.draw()
        self.ax.draw_artist(image1)
        self.draw_scalebar()
        self.fig.canvas.draw()
        
        plt.pause(0.001)
        
        
    def get_cmap(self):
        cmap = self.GUI.heatmap_cmap.get()
        base_cmap = matplotlib.cm.get_cmap(cmap, 1024)
        
        vmin = float(self.GUI.heatmap_cmap_minval.get())
        vmax = float(self.GUI.heatmap_cmap_maxval.get())
        
        new_cmap = matplotlib.colors.ListedColormap(
            base_cmap(
                np.linspace(vmin, vmax, 512)
                )
            )
        return new_cmap   
        
    
    def draw_scalebar(self):
        scale  = float(self.scale.get())
        length = float(self.scalebar_length.get())
        
        frac = length/scale
        label = f'{self.scalebar_length.get()}' + r' $\mu$m'
        
        scalebar = AnchoredSizeBar(self.ax.transData,
                           frac, label, 'lower right', 
                           pad=0.1,
                           color='black',
                           frameon=False,
                           size_vertical=0.2*frac,
                           label_top=False,
                           bbox_to_anchor=matplotlib.transforms.Bbox.from_bounds(0.5,-0.3,0.5,0.3),
                           bbox_transform=self.ax.transAxes)
        
        self.ax.add_artist(scalebar)
        self.ax.draw_artist(scalebar)
        self.artists.append(scalebar)
        



class EchemFigExporter(FigureExporter):
    def __init__(self, GUI, echem_data):
        self.data = echem_data
        super().__init__(GUI=GUI)
    
    def fill_leftframe(self):
        # Put relevant buttons in self.leftframe
        frame = self.leftframe
        
        if not hasattr(self, 'dpi_field'):
            # Will already have these attributes if it's being reinitialized
            self.dpi_field = StringVar(value='600')
            self.xlabel = StringVar(value='')
            self.ylabel = StringVar(value='')
            self.xticks = StringVar(value='')
            self.yticks = StringVar(value='')
            self.n_xticks = StringVar(value='')
            self.n_yticks = StringVar(value='')
            self.div_const = StringVar(value='1')
        
        Label(frame, text='Heatmap Exporter       ').grid(row=0, column=0, columnspan=2)
        Button(frame, text='Redraw', command=self.redraw).grid(row=0, column=2, sticky=(W,E))
        
        Label(frame, text='dpi: ').grid(row=1, column=0, sticky=(W,E))
        Entry(frame, textvariable=self.dpi_field, width=4).grid(row=1, column=1,
                                                                sticky=(W,E))
        Button(frame, text='Save', command=self.save).grid(row=1, column=2, sticky=(W,E))
        
        
        Label(frame, text='X label: ').grid(row=2, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.xlabel, width=20).grid(
            row=2, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='Y label: ').grid(row=3, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.ylabel, width=20).grid(
            row=3, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='X ticks: ').grid(row=4, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.xticks, width=20).grid(
            row=4, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='Y ticks: ').grid(row=5, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.yticks, width=20).grid(
            row=5, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='# X ticks: ').grid(row=6, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.n_xticks, width=20).grid(
            row=6, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='# Y ticks: ').grid(row=7, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.n_yticks, width=20).grid(
            row=7, column=1, columnspan=2, sticky=(W,E))
        
        Label(frame, text='Div. const.: ').grid(row=8, column=0, 
                                                    columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self.div_const, width=20).grid(
            row=8, column=1, columnspan=2, sticky=(W,E))
        pass
    
    
    def redraw(self):
        self.ax.clear()
        self.draw()
    
    
    def draw(self):
        x,y = zip(*self.data)
        x,y = np.array(x), np.array(y)
        y /= float(self.div_const.get())
        self.ax.plot(x,y)
        self.set_xlabel()
        self.set_ylabel()
        self.set_xticks()
        self.set_yticks()
        
        self.fig.canvas.draw()
        plt.pause(0.001)
    
    
    def divide_by_const(self, constant):
        pass
    
    
    def set_xlabel(self):
        xlabel = self.xlabel.get()
        self.ax.set_xlabel(f'{xlabel}')
    
    def set_ylabel(self):
        ylabel = self.ylabel.get()
        self.ax.set_ylabel(f'{ylabel}')
        
    def set_xticks(self):
        xticks = self.xticks.get()
        if xticks == '':
            return self.set_n_xticks()
        xticks = xticks.split(',')
        xticks = [float(n) for n in xticks]
        self.ax.set_xticks(xticks)
        
    def set_yticks(self):
        yticks = self.yticks.get()
        if yticks == '':
            return self.set_n_yticks()
        yticks = yticks.split(',')
        yticks = [float(n) for n in yticks]
        self.ax.set_yticks(yticks)
        
    def set_n_xticks(self):
        try:
            n_xticks = int(self.n_xticks.get())
        except:
            return
        self.ax.xaxis.set_major_locator(plt.MaxNLocator(n_xticks))
        
    def set_n_yticks(self):
        try:
            n_yticks = int(self.n_yticks.get())
        except:
            return
        self.ax.yaxis.set_major_locator(plt.MaxNLocator(n_yticks))
        

            
class ExporterGenerator():
    '''
    Class for generating or returning the current Exporters
    '''
    def __init__(self):
        self.HeatmapExporter = None
        self.EchemExporter   = None
    
    def get(self, exporter_type, GUI, data):
        
        # Either reinitialize to remake window with old settings,
        # or create a new Exporter object
        
        if exporter_type == 'Heatmap':
            if self.HeatmapExporter:
                return self.HeatmapExporter.__init__(GUI, data)
            self.HeatmapExporter = HeatmapExporter(GUI, data)
            return
            
        if exporter_type == 'Echem':
            if self.EchemExporter:
                return self.EchemExporter.__init__(GUI, data)
            self.EchemExporter = EchemFigExporter(GUI, data)
            return 
        
  
    

