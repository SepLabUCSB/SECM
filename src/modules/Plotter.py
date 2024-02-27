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
        try:
            return sum(data.data[0])
        except:
            return data.data[0]
    
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
    if type(data) in (float, int):
        return data
    
    return 0


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
    inc_prefixes = ['k', 'M', 'G', 'T', 'P', 'E']
    dec_prefixes = ['m', 'µ', 'n', 'p', 'f', 'a']

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


def inv_unit_label(s:str):
    '''
    Return string as float
    '''
    if type(s) != str:
        return s
    prefixes = {'k':1e3, 
                'M':1e6, 
                'G':1e9, 
                'm':1e-3, 
                'u':1e-6, 
                'n':1e-9, 
                'p':1e-12, 
                'f':1e-15}
    
    if not s[-1] in prefixes:
        return float(s)
    
    val = float(s[:-1])*prefixes[s[-1]]
    return val
    

def square_axes(ax):
    mini = min(0, *ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)



class Heatmap():
    def __init__(self, fig, GUI):
        self.GUI = GUI
        self.expt = None
        
        self.fig = fig
        self.ax  = fig.gca()
        
        # Data array to display and its checksum
        self.data = np.array([0,])
        self.last_checksum = checksum(self.data)
        
        # Rectangle drawn around selected point
        self.rect = matplotlib.patches.Rectangle((0,0), 0, 0, fill=0,
                                                 edgecolor='red', lw=2)
        self.ax.add_artist(self.rect)
        
        self.force_minmax = False
        self.analysis_function = analysis_funcs.CV_decay_analysis
        
        self.initialize()
      
        
    def initialize(self):
        '''
        Draw the initial figure
        '''
        self.data = np.array([
            np.array([0 for _ in range(10)]) for _ in range(10)
            ], dtype=np.float32)
        self.image = self.ax.imshow(self.data, cmap='viridis', origin='upper')
        cb = self.fig.colorbar(self.image, ax=self.ax, shrink=0.5,
                                pad=0.02, format="%0.1e")
        cb.ax.tick_params(labelsize=14)
        
        self.ax.set_xlabel(r'$\mu$m')
        self.ax.set_ylabel(r'$\mu$m')
        self.ax.spines['right'].set_visible(True)
        self.ax.spines['top'].set_visible(True)
        self.fig.canvas.draw()
        self.fig.tight_layout()
        # self.ax1bg = self.fig1.canvas.copy_from_bbox(self.ax1.bbox)
        self.rect.set_bounds(0,0,0,0)
        self.ax.draw_artist(self.image)
        self.ax.draw_artist(self.rect)
        plt.pause(0.001)
    

    def load_experiment(self, expt):
        '''
        Load data from given experiment and display on heatmap
        
        expt : DataStorage.Experiment
        '''
        self.expt = expt
        self.data = expt.get_heatmap_data()
        self.ax.set_xlim(0, expt.length)
        self.ax.set_ylim(0, expt.length)
        
    
    def get_datapoint_on_click(self, event, pt_idx):
        '''
        Called by Plotter.onclick when user clicks on heatmap.
        Draws a box around that point on the heatmap.
        Return the closest DataPoint and its value.

        Parameters
        ----------
        event : matplotlib button_press_event
        pt_idx: int, defines which DataPoint in a PointsList to return

        Returns
        -------
        DataPoint : closest Datapoint to the click
        '''
        # event_x, y = event.xdata, event.ydata
        datapts = self.expt.get_loc_data()
        
        left, right = self.ax.get_xlim()
        pts_in_row = len(datapts[0]) + 1
        x_bounds = [n for n in np.linspace(left, right, pts_in_row)]
        y_bounds = [n for n in np.linspace(left, right, pts_in_row)]
        delta = x_bounds[1] - x_bounds[0]
        
        for xline in x_bounds:
            if event.xdata >= xline:
                continue
            break
        
        for yline in y_bounds:
            if event.ydata >= yline:
                continue
            break
        
        # xline is top and yline is left side of pixel
        # Draw rectangle around the selected point
        self.rect.set_x(xline - delta)
        self.rect.set_y(yline - delta)
        self.rect.set_width(delta)
        self.rect.set_height(delta)
        self.ax.draw_artist(self.rect)
        self.fig.canvas.draw_idle()
        
        def pt_in_rect(x, y, xline, yline, delta):
            if (x <= xline) and (x >= xline-delta):
                if (y <= yline) and (y >= yline-delta):
                    return True
            return False
        
        for row in datapts:
            for (x, y) in row:
                if pt_in_rect(x, y, xline, yline, delta):
                    i, DataPoint = self.expt.get_nearest_datapoint(x, y, pt_idx=pt_idx)
                    x0, y0, z0 = DataPoint.loc
                    if type(z0) == tuple:
                        z0 = z0[0] # Handle early bug in some saved data
                    val = self.data.flatten()[i]
                    print(f'Point: ({x0:0.2f}, {y0:0.2f}, {z0:0.2f}), Value: {unit_label(val, dec=3)}')
                    return DataPoint
       
                
    def update(self, force=False):
        '''
        Called periodically by Tk root (via Plotter.update_figs).
        Check if new points are appended to the experiment and plot them if so
        '''
                
        if ((checksum(self.data) == self.last_checksum) and not force):
            return
        
        self.update_data()
        
        self.image.set_data(self.data[::-1])
        
        if self.force_minmax:
            minval = inv_unit_label(self.GUI.heatmap_min_val.get())
            maxval = inv_unit_label(self.GUI.heatmap_max_val.get())
        else:
            minval, maxval = get_clim(self.data)
            self.update_minmaxval_fields()
            
        self.image.set(clim=( minval, maxval) )
        set_cbar_ticklabels(self.image.colorbar, [minval, maxval])
        
        left, right = self.ax.get_xlim()
        bottom, top = self.ax.get_ylim()
        self.image.set_extent((left, right, bottom, top))
        self.ax.draw_artist(self.image)
        self.fig.canvas.draw_idle()
        self.last_checksum = checksum(self.data)
        plt.pause(0.001)
    
        
    def update_data(self):
        '''
        Grabs display options from the GUI and pulls array of data from
        the current Experiment. Puts it in self.data
        
        Plot will be updated next time self.update() is called
        '''
        option = self.GUI.heatmapselection.get()
        value  = self.GUI.HeatMapDisplayParam.get()
        
        if option == 'Analysis func.':
            value = value.replace('\n', '')
            if not self.analysis_function:
                print('Error: no analysis function selected.')
                return
            pts = self.expt.do_analysis(self.analysis_function, value)
        
        else:
            # Keys to pass to Experiment
            d = {'Max. current': 'max',
                 'Current @ ... (V)': 'val_at',
                 'Current @ ... (t)': 'val_at_t',
                 'Z height': 'z',
                 'Avg. current': 'avg'}
            
            value = float(value.replace('\n', '')) if value else None
            pts = self.expt.get_heatmap_data(d[option], value)
        
        if len(pts) > 0:
            self.data = pts
        return
    
    
    def update_colormap(self, *args, **kwargs):
        cmap = self.GUI.heatmap_cmap.get()
        base_cmap = matplotlib.cm.get_cmap(cmap, 1024)
        
        vmin = float(self.GUI.heatmap_cmap_minval.get())
        vmax = float(self.GUI.heatmap_cmap_maxval.get())
        
        if (vmin < 0) or (vmin > 1) or (vmax < 0) or (vmax > 1):
            print('\nInvalid input! Min and max must be between 0 and 1.\n')
            return
        
        new_cmap = matplotlib.colors.ListedColormap(
            base_cmap(
                np.linspace(vmin, vmax, 512)
                )
            )
            
        self.image.set(cmap = new_cmap)
        self.update(force = True)
        
    ### Colormap updating functions
    def update_minmaxval_fields(self):
        minval, maxval = get_clim(self.data[::-1])
        self.GUI.heatmap_min_val.set(f'{minval:0.3g}')
        self.GUI.heatmap_max_val.set(f'{maxval:0.3g}') 
    
    def apply_minmax_fields(self, val=None):
        self.force_minmax = True
        self.update(force=True)
        
    def zoom_in(self):
        'Make the heatmap color scale smaller by 10%'
        self._zoom_bound('upper', 'subtract')
        self._zoom_bound('lower', 'add')
        self.update(force=True)
    
    def zoom_out(self):
        'Make the heatmap color scale larger by 10%'
        self._zoom_bound('upper', 'add')
        self._zoom_bound('lower', 'subtract')
        self.update(force=True)
    
    def zoom_lower_add(self):
        'Add 10% to lower heatmap color scale bound'
        self._zoom_bound('lower', 'add')
        self.update(force=True)
    
    def zoom_lower_subt(self):
        'Subtract 10% to lower heatmap color scale bound'
        self._zoom_bound('lower', 'subtract')
        self.update(force=True)
    
    def zoom_upper_add(self):
        'Add 10% to upper heatmap color scale bound'
        self._zoom_bound('upper', 'add')
        self.update(force=True)
    
    def zoom_upper_subt(self):
        'Subtract 10% to upper heatmap color scale bound'
        self._zoom_bound('upper', 'subtract')
        self.update(force=True)
    
    def _zoom_bound(self, bound, direction):
        minval = self.GUI.heatmap_min_val
        maxval = self.GUI.heatmap_max_val
                
        val = minval if bound == 'lower' else maxval
        
        floatval = inv_unit_label(val.get())
        delta = inv_unit_label(maxval.get()) - inv_unit_label(minval.get())
        if direction == 'add':
            floatval += abs(0.1*delta)
        elif direction == 'subtract':
            floatval -= abs(0.1*delta)
        
        val.set(f'{floatval:0.3g}')
        self.force_minmax = True
    
        
    def cancel_popup(self):
        # Reset minval and maxval to None
        self.force_minmax = False
        self.update_minmaxval_fields()
        self.update(force=True)
        
        
        

    
        
    
    

class EchemFig():
    def __init__(self, fig, GUI):
        # Set up this figure, axes, and line to plot to
        self.fig = fig
        self.ax  = fig.gca()
        self.ln, = self.ax.plot([0,1],[0,1])
        
        # Local reference to GUI object
        self.GUI = GUI
        
        # Keep track of what is currently being plotted
        self.DataPoint = None
        self.last_checksum = checksum(self.DataPoint)
        self.artists = []
        self._forced = False
        
        self.initialize()
        
        
    def initialize(self):
        '''
        Clear the figure
        '''
        self._forced = False
        self.ax.cla()
        self.ln, = self.ax.plot([],[])
        self.clear_artists()
        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.draw_artists()
    
    
    def reset(self):
        '''
        Allow new ADC points to be displayed in real time

        Returns
        -------
        None.
        '''
        self._forced = False
    
    
    def update(self, ADCDataPoint):
        '''
        Called by Plotter.update_figs every 100 ms. Check if new data exists
        in the ADCDataPoint to be plotted. Reset the figure if a new ADCDataPoint
        is passed.

        Parameters
        ----------
        ADCDataPoint : DataStorage.ADCDataPoint currently in the buffer
        
        Returns
        -------
        None.
        '''
        
        # Trying to display the same ADC data point. Update with new points.
        if id(ADCDataPoint) == id(self.DataPoint):
            if checksum(self.DataPoint) != self.last_checksum:
                return self.update_plot()
        
        # Trying to display a new data point. Refresh plot            
        if id(ADCDataPoint) != id(self.DataPoint):
            if self._forced:
                # Don't update if force displaying previous data.
                return
            self.initialize()
            self.set_datapoint(ADCDataPoint)
            
            
    
    def set_datapoint(self, DataPoint, forced=False):
        '''
        Display a given DataPoint. Called by i.e. clicking on Heatmap point
        or changing the selected viewing option (from I vs V to I vs t, for example)

        Parameters
        ----------
        DataPoint : DataStorage.DataPoint type.
        forced : bool, optional. Whether to force display over the current ADC buffer.
        
        Returns
        -------
        None.
        '''
        self._forced = forced
        if DataPoint:
            self.DataPoint = DataPoint  
        self.update_plot()
    
    
    def update_plot(self):
        '''
        Grab display options from the GUI and initiate redrawing the plot.

        Returns
        -------
        None.
        '''
        # IV_selection in ['V vs t','I vs t','I vs V',]
        # EIS_selection in ['Nyquist', '|Z| Bode', 'Phase Bode']
        IV_selection = self.GUI.fig2selection.get()
        EIS_selection = self.GUI.EIS_view_selection.get()
        pt_selection = self.GUI.fig2ptselection.get()
        
        DataPoint = self.DataPoint[pt_selection]
        self.last_checksum = checksum(self.DataPoint)
        if isinstance(DataPoint, EISDataPoint):
            self.plot_EIS(DataPoint, EIS_selection)
        else:
            self.plot_IV(DataPoint, IV_selection)
        
             
    def plot_IV(self, DataPoint, IV_selection):
        '''
        Function for drawing voltammetric (I-V, I-t, or V-t) data

        Parameters
        ----------
        DataPoint : DataStorage.ADCDataPoint, CVDataPoint, or SinglePoint
        IV_selection : string, display setting pulled from GUI

        Returns
        -------
        None.
        '''
        t, V, I = DataPoint.get_data(downsample=True) #Only passes downsampled arg to ADCDataPoint type
        
        if hasattr(DataPoint, 'gain'):
            # ADCDataPoints take 'gain' argument from GUI (set in HEKA), need to
            # convert output voltage -> current
            V = np.array(V)/10
            I = np.array(I)/DataPoint.gain
        
        d = {'t':t, 'V':V, 'I':I}
        
        ylabel, xlabel = IV_selection.split(' vs ')
        yvals, xvals = d[ylabel], d[xlabel]
        self.ln.set_data(xvals, yvals[:len(xvals)])
        self.ln.set_marker('')
        xlim, ylim = get_plotlim(xvals, yvals)
        self.ax.set_xscale('linear')
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        
        self.append_extra_artists(DataPoint, IV_selection)
        self.draw_artists()
        
        
    def plot_EIS(self, DataPoint, EIS_selection):
        if EIS_selection == 'Nyquist':
            self.plot_Nyquist(DataPoint)
        if EIS_selection == '|Z| Bode':
            self.plot_Bode(DataPoint, 'Z')
        if EIS_selection == 'Phase Bode':
            self.plot_Bode(DataPoint, 'Phase')
    
    
    def plot_Nyquist(self, DataPoint):
        '''
        Display a Nyquist plot.

        Parameters
        ----------
        DataPoint : DataStorage.EISDataPoint

        Returns
        -------
        None.
        '''
        freqs, _,_,Z = DataPoint.data
        
        valid_idxs = [i for i, z in enumerate(Z) if np.abs(z) <= 20e9]
        Z = [z for i, z in enumerate(Z) if i in valid_idxs]
    
        x = np.real(Z)
        y = -np.imag(Z)
        self.ln.set_data(x, y)
        self.ln.set_marker('o')
        self.ax.set_xscale('linear')
        self.ax.set_xlabel(r"Z'/ $\Omega$")
        self.ax.set_ylabel(r"Z''/ $\Omega$")
        xlim, ylim = get_plotlim(x, y)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        square_axes(self.ax)
        self.ax.xaxis.set_major_locator(matplotlib.ticker.AutoLocator())
        self.ax.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
        
        self.append_extra_artists(DataPoint, 'Nyquist')
        self.draw_artists()
        
    
    
    def plot_Bode(self, DataPoint, option):
        '''
        Make a Bode plot on Fig 2 for EIS-type data

        Parameters
        ----------
        DataPoint : DataStorage.EISDataPoint
        option : string, 'Z' or 'Phase'

        Returns
        -------
        None.
        '''
        freqs, _, _, Z = DataPoint.data
        x  = [float(f) for f in freqs]
        valid_idxs = [i for i, z in enumerate(Z) if np.abs(z) <= 20e9]
        
        Z = [z for i, z in enumerate(Z) if i in valid_idxs]
        x = [X for i, X in enumerate(x) if i in valid_idxs]
        
        if option == 'Z':
            y = np.abs(Z)
            ylabel = r'|Z|/ $\Omega$'
            self.ax.set_ylim(
                          min(y) - 0.05*abs(min(y)),
                          max(y) + 0.05*abs(max(y))
                          )
            
        elif option == 'Phase':
            y = np.angle(Z, deg=True)
            ylabel = r'Phase/ $\degree$'
            self.ax.set_ylim(min(y)-15, max(y)+15)
        
        self.ln.set_data(x,y)
        self.ln.set_marker('o')
        
        self.ax.set_xscale('log')
        self.ax.set_xticks([1e-2,1e-1,1e0,1e1,1e2,1e3,1e4,1e5,1e6])
        self.ax.set_xlim(min(x) - 0.05*min(x), max(x) + 0.05*max(x))
        self.ax.set_xlabel('Frequency/ Hz')
        self.ax.set_ylabel(ylabel)
        
        self.append_extra_artists(DataPoint, option)
        self.draw_artists()
        
    
            
    def clear_artists(self):
        '''
        Removes all artists (except for self.ln) from the figure.

        Returns
        -------
        None.
        '''
        if len(self.artists) != 0:
            for artist in self.artists:
                try:
                    artist.remove()
                except:
                    # Artist may have never been drawn
                    pass
        self.artists = []
        
    
    def append_extra_artists(self, DataPoint, selection):
        '''
        Adds any artists generated by an Analysis function to self.artists.

        Parameters
        ----------
        DataPoint : DataStorage.DataPoint
        selection : string, display option. Must match DataPoint.artist.draw_on_type
                    set by the analysis function.

        Returns
        -------
        None.
        '''
        self.clear_artists()
        if not hasattr(DataPoint, 'artists'):
            return
        for artist in DataPoint.artists:
            if ( (hasattr(artist, 'draw_on_type')) and
                artist.draw_on_type != selection):
                continue
            self.artists.append(artist)
        
        
    def draw_artists(self):
        '''
        Draw all artists in the figure and draw the canvas.

        Returns
        -------
        None.
        '''
        self.ax.draw_artist(self.ln)
        for artist in self.artists:
            try:
                self.ax.add_artist(artist)
                self.ax.draw_artist(artist)
                self.fig.canvas.draw_idle()
            except Exception as e:
                '''If reloading an old data file, it fails to draw
                previously-generated artists. Catch that and remove the
                artist. (Can be regenerated by running the same analysis
                function)'''
                # print(f'Error drawing artist: {artist=}')
                # print(e)
                artist.remove()
                self.artists.remove(artist)     
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
        
        




class Plotter(Logger):
    
    def __init__(self, master, fig1, fig2):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.Heatmap  = Heatmap(fig1, master.GUI)
        self.EchemFig = EchemFig(fig2, master.GUI)
        
        self.connect_cids()        
        

        
    ###########################
    #### GENERAL FUNCTIONS ####
    ###########################
    
    def connect_cids(self):
        self.cid1 = self.Heatmap.fig.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
        self.cid2 = self.EchemFig.fig.canvas.mpl_connect('button_press_event',
                                                 self.onclick)
    
    def disconnect_cids(self):
        for cid in (self.cid1, self.cid2):
            self.fig2.canvas.mpl_disconnect(cid)
    
    
    def load_from_expt(self, expt):
        self.Heatmap.load_experiment(expt)
    
    
    def onclick(self, event):
        # Clicking on pixel in SECM histogram displays that CV ( or
        # CA, or EIS, ...) in the lower figure
        if event.inaxes == self.Heatmap.ax:
            pt_idx = int(self.master.GUI.fig2ptselection.get())
            DataPoint = self.Heatmap.get_datapoint_on_click(event, pt_idx)
            self.EchemFig.set_datapoint(DataPoint, forced=True)
            self.master.ImageCorrelator.draw_on_pt(DataPoint.loc[0],
                                                   DataPoint.loc[1])
            
        if event.inaxes == self.EchemFig.ax:
            x, y = event.xdata, event.ydata
            print(f'({unit_label(x, dec=3)}, {unit_label(y, dec=3)})')
        
        return 
    
    
    # Called every 100 ms by TK mainloop.
    # Check if data has updated. If so, plot it to
    # the appropriate figure.
    def update_figs(self, **kwargs):
        
        if self.master.expt != self.Heatmap.expt:
            self.Heatmap.load_experiment(self.master.expt)
        self.Heatmap.update()
        self.EchemFig.update(self.master.ADC.pollingdata)
                
        self.master.GUI.root.after(100, self.update_figs)
        return
    

    ###########################
    #### HEATMAP CALLBACKS ####
    ###########################   
    
    # Called from GUI by changing view selector
    # Update what is shown on the heatmap
    def update_heatmap(self, option=None, value=None):
        self.Heatmap.update(force=True)   
    
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
        self.Heatmap.update_colormap()
                 
    
    def set_analysis_popup(self):
        # Opens a window where user can choose what function to apply
        # to each datapoint in the heatmap
        if not hasattr(self, 'AnalysisFuncSelector'):
            self.AnalysisFuncSelector = AnalysisFunctionSelector(self.master.GUI.root)
        func = self.AnalysisFuncSelector.get_selection()
        self.analysis_function = func
        self.Heatmap.analysis_function = func

        
    
        
        


class FigureExporter():
    
    def __init__(self, GUI):
        self.GUI = GUI
        self.fig = plt.Figure(figsize=(4,4), dpi=100, constrained_layout=True)
        self.fig.add_subplot(111)
        self.ax = self.fig.gca()
        self.dpi = 300
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
            self.dpi_field       = StringVar(value=f'{self.dpi}')
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
                                pad=0.02, format=lambda val,idx:unit_label(val))
        cb.ax.tick_params(labelsize=14)
        self.artists.append(cb)
        
        for sp in ['right', 'top', 'left', 'bottom']:
            self.ax.spines[sp].set_visible(True)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        minval = inv_unit_label(self.GUI.heatmap_min_val.get())
        maxval = inv_unit_label(self.GUI.heatmap_max_val.get())
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
            self.dpi_field = StringVar(value=f'{self.dpi}')
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
        
  
    

