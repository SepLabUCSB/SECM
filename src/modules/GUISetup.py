from tkinter import *
from tkinter.ttk import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


heatmapOptions = [
    'Max. current',
    'Current @ ... (V)',
    'Current @ ... (t)',
    'Z height',
    'Avg. current',
    'Analysis func.'
    ]

fig2Options = ['V vs t','I vs t','I vs V',]
EIS_options = ['Nyquist', '|Z| Bode', 'Phase Bode']

cmaps = ['viridis', 'hot', 'gist_gray', 'afmhot', 'plasma', 'inferno', 
         'magma', 'cividis','Greys', 'Purples', 'Blues', 'Greens', 
         'Oranges', 'Reds', 'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 
         'BuPu','GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
         'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu', 'RdYlBu',
         'RdYlGn', 'coolwarm', 'bwr']

filter1options = ['Bessel 100 kHz', 'Bessel 30 kHz', 'Bessel 10 kHz']
filter2types = ['Bessel', 'Butterworth', 'Bypass']
stimfilters  = ['2 us', '20 us']
elecmodes    = ['2 Electrode', '3 Electrode']

gains = ['0.005 mV/pA','0.01 mV/pA', '0.02 mV/pA', '0.05 mV/pA',
         '0.1 mV/pA', '0.2 mV/pA', '--', '0.5 mV/pA',
         '1 mV/pA', '2 mV/pA', '5 mV/pA', '10 mV/pA',
         '20 mV/pA', '--', '50 mV/pA', '100 mV/pA',
         '200 mV/pA', '500 mV/pA', '1000 mV/pA', '2000 mV/pA']

hopping_methods = ['CV', 'CV then EIS', 'CV then 5x EIS amps', 
           'CV then 5x EIS wait', 'CA', 'hopping CA', 'Custom']


def where(l, val):
    for i, value in enumerate(l):
        if value == val:
            return i
    raise IndexError


def convert_to_index(amp_params):
    params = {'E Vhold': amp_params['Vhold'].get().rstrip('\n'),
              'E Filter1': where(filter1options, 
                               amp_params['filter1'].get()),
              'E F2Response': where(filter2types, 
                               amp_params['filter2type'].get()),
              'E Filter2': amp_params['filter2'].get().rstrip('\n'),
              'E StimFilter': where(stimfilters, 
                               amp_params['stimfilter'].get()),
              'E ElectrMode': where(elecmodes, 
                               amp_params['elecmode'].get()),
              'E Gain': where(gains, amp_params['gain'].get()),
              'float_gain': float(amp_params['gain'].get().split(' ')[0])}
    return params    


def focus_next_widget(event):
    widget = event.widget.tk_focusNext()
    widget.focus()
    try:
        widget.select_range(0, 'end')
    except:
        pass
    return("break")


def OptionMenuStringVar(frame, options,row,col,sticky,idx=0, return_widget=False):
    var = StringVar()
    menu = OptionMenu(frame, var, options[idx],*options)
    menu.grid(row=row, column=col, sticky=sticky)
    if return_widget:
        return var, menu
    return var


def OptionMenuIntVar(frame, options,row,col,sticky,idx=0, return_widget=False):
    var = IntVar()
    menu = OptionMenu(frame, var, options[idx],*options)
    menu.grid(row=row, column=col, sticky=sticky)
    if return_widget:
        return var, menu
    return var


def EntryStringVar(frame, width, row, col, sticky, default='', bind_key=None,
                   bind_func=None, tab=False, returnTab = False, return_widget=False):
    var = StringVar(value=str(default))
    entry = Entry(frame, width=width, textvariable=var)
    entry.grid(row=row, column=col, sticky=sticky)
    if tab:
        entry.bind('<Tab>', focus_next_widget)
    if returnTab:
        entry.bind('<Return>', focus_next_widget)
    if bind_key:
        entry.bind(bind_key, bind_func)
    if return_widget:
        return var, entry
    return var



def Labels_in_column(frame, labels, column, start_row, sticky):
    widgets = [Label(frame, text=string) for string in labels]
    widgets_in_column(widgets, column, start_row, sticky)
    
        
def widgets_in_column(widgets, column, start_row, sticky):
    row = start_row
    for widget in widgets:
        widget.grid(column=column, row=row, sticky=sticky)
        row += 1


class GUISetupMethods():
    
    def MakeStopButtonFrame(self, frame):
        Button(frame, text='Stop', command=self.master.abort, width=50).grid(
            row=0, column=0, columnspan=2, sticky=(W,E))
        
        Label(frame, text='Estimated time remaining: ').grid(
            row=1, column=0, sticky=(W))
        self._time_est = StringVar()
        Label(frame, textvariable=self._time_est, width=20).grid(
            row=1, column=1, sticky=(W))
        
        
        
        
    def MakePstatFrame(self, frame):
        tabs = Notebook(frame)
        AmpFrame = Frame(tabs)
        CVFrame  = Frame(tabs)
        EISFrame = Frame(tabs)
        CAFrame  = Frame(tabs)
        
        tabs.add(AmpFrame, text='Amplifier')
        tabs.add(CVFrame, text='  CV  ')
        tabs.add(EISFrame, text='  EIS  ')
        tabs.add(CAFrame, text='  CA  ')
        tabs.pack(expand=1, fill='both')
        
        self.MakeAmpFrame(AmpFrame)
        self.MakeCVFrame(CVFrame)
        self.MakeEISFrame(EISFrame)
        self.MakeCAFrame(CAFrame)
        
    
    def MakeAmpFrame(self, frame):
        left_labels = ['V-hold: ', 'Filter 1: ', 'Filter 2: ', 'Filter 2: ', 
                       'Stim. Filter: ', 'Electrode Mode: ', 'Gain: ']
        right_labels = ['mV', '', '', '', 'kHz']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        
        Vhold = EntryStringVar(frame, 6, 0, 1, (E,W), tab=True, returnTab=True,
                                        default='0')
        filter1 = OptionMenuStringVar(frame, filter1options, 1, 1, (E,W), 2)
        filter2type = OptionMenuStringVar(frame, filter2types, 2, 1, (W,E))
        f2_field = EntryStringVar(frame, 6, 3, 1, (W,E), tab=True,
                                        returnTab=True, default='0.5')
        stimfilter = OptionMenuStringVar(frame, stimfilters, 4, 1, (W,E))
        elecmode   = OptionMenuStringVar(frame, elecmodes, 5, 1, (W,E))
        gain       = OptionMenuStringVar(frame, gains, 6, 1, (W,E), idx=8)
        
        Button(frame, text='Apply settings', command=self.set_amplifier).grid(column=1, row=7)
        
        self.params['amp'] = {'Vhold': Vhold,
                      'filter1': filter1,
                      'filter2type': filter2type,
                      'filter2': f2_field,
                      'stimfilter': stimfilter,
                      'elecmode': elecmode,
                      'gain': gain}
        self.amp_params = convert_to_index(self.params['amp'])
        return
    
    
    def MakeCVFrame(self, tab_frame):
        frame = Frame(tab_frame)
        figframe = Frame(tab_frame)
        frame.grid(row=0, column=0)
        figframe.grid(row=0, column=1)
        
        left_labels = ['E0 = ', 't0 = ', 'E1 = ', 'E2 = ', 'Ef = ', 'v = ', 'Nc = ']
        right_labels = ['V', 's', 'V', 'V', 'V', 'V/s', 'cycles']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        E0 = EntryStringVar(frame, 6, 0, 1, (W,E), tab=True, 
                               returnTab=True, default= '0')
        t0 = EntryStringVar(frame, 6, 1, 1, (W,E), tab=True, 
                               returnTab=True, default= '0.2')
        E1 = EntryStringVar(frame, 6, 2, 1, (W,E), tab=True, 
                               returnTab=True, default= '0.5')
        E2 = EntryStringVar(frame, 6, 3, 1, (W,E), tab=True, 
                               returnTab=True, default= '0')
        Ef = EntryStringVar(frame, 6, 4, 1, (W,E), tab=True, 
                               returnTab=True, default= '0')
        v  = EntryStringVar(frame, 6, 5, 1, (W,E), tab=True, 
                               returnTab=True, default= '0.1')
        Nc = EntryStringVar(frame, 6, 6, 1, (W,E), tab=True,
                               returnTab = True, default= '1')
        
        Button(frame, text='Run CV', command = self.run_CV).grid(row=7, column=1, sticky=(W,E))
        
        fig = plt.Figure(figsize=(3,2), dpi=50)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=figframe)
        canvas.get_tk_widget().grid(row=0, column=0)
        make_CV_fig(ax)
        
        self.params['CV'] = {'E0': E0, 'E1': E1, 'E2': E2, 
                             'Ef': Ef, 't0': t0, 'v':v, 'Nc': Nc}
        return
    
    
    def MakeEISFrame(self, frame):
        
        left_labels = ['DC bias:', 'Scan from...', 'To...', 'Collect:', 'Cycles:', 'Amplitude:', '']
        right_labels = ['mV', 'Hz', 'Hz', 'points', '', 'mVpp', '']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        DC = EntryStringVar(frame, 6, 0, 1, (W,E), default=0, tab=True, returnTab=True)
        f0 = EntryStringVar(frame, 6, 1, 1, (W,E), default=1, tab=True, returnTab=True)
        f1 = EntryStringVar(frame, 6, 2, 1, (W,E), default=1000, tab=True, returnTab=True)
        n_pts = EntryStringVar(frame, 6, 3, 1, (W,E), default=18, tab=True, returnTab=True)
        n_cycles = EntryStringVar(frame, 6, 4, 1, (W,E), default=1, tab=True, returnTab=True)
        amp = EntryStringVar(frame, 6, 5, 1, (W,E), default=20, tab=True, returnTab=True)
        
        Button(frame, text='Run EIS', command=self.run_EIS).grid(row=6, column=1,
                                                                 sticky=(W,E))
        
        self.params['EIS'] = {'E0':DC, 'f0':f0, 'f1':f1, 
                              'n_pts':n_pts, 'n_cycles':n_cycles, 'amp':amp}
        return
    
    
    def MakeCAFrame(self, frame):
        left_labels = ['E = ', 't = ', '']
        right_labels = ['V', 's', '']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        V = EntryStringVar(frame, 10, 0, 1, (W,E), tab=True, 
                               returnTab=True, default= '0')
        t = EntryStringVar(frame, 10, 1, 1, (W,E), tab=True, 
                               returnTab=True, default= '10')
        
        Button(frame, text='Run CA', command=self.run_CA).grid(
            row=2, column=1)
        Button(frame, text='Poll ADC', command=self.master.ADC.polling).grid(
            row=3, column=1)
        Button(frame, text='Run Custom', command=self.run_custom).grid(
            row=4, column=1)
        
        # CA_params_all = []
        # for i in range(len(t)):
        #     g = {'voltage': V[i], 't': t[i]}
        #     CA_params_all.append(g)
        
        #self.params['CA'] = CA_params_all[0]
        
        self.params['CA'] = {'voltage': V, 't': t}
        return




    def MakeSECMFrame(self, frame):
        tabs = Notebook(frame)
        
        ApproachFrame = Frame(tabs)
        HoppingFrame  = Frame(tabs)
                
        tabs.add(ApproachFrame, text=' Approach ')
        tabs.add(HoppingFrame, text=' Hopping ')
        tabs.pack(expand=1, fill='both')
        
        self.MakeApproachFrame(ApproachFrame)
        self.MakeHoppingFrame(HoppingFrame)
        return
    
    
    def MakeApproachFrame(self, frame):
        left_labels = ['Voltage: ', 'Cutoff: ', 'Height: ', 'Step: ']
        right_labels = ['mV', 'pA', 'μm', 'nm']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        V = EntryStringVar(frame, 6, 0, 1, (W,E), tab=True, returnTab=True, 
                           default=400)
        I = EntryStringVar(frame, 6, 1, 1, (W,E), tab=True, returnTab=True, 
                           default=5)
        Z = EntryStringVar(frame, 6, 2, 1, (W,E), tab=True, returnTab=True, 
                           default=80)
        step = EntryStringVar(frame, 6, 3, 1, (W,E), tab=True, returnTab=True, 
                           default=10)
        
        rel_current = OptionMenuStringVar(frame, ['Relative', 'Absolute'], 1, 3, (W))
        
        Button(frame, text='Approach', command=self.run_approach_curve).grid(
            row=4, column=1, sticky=(W,E))
        Button(frame, text='Retract', command=self.run_retract).grid(
            row=5, column=1, sticky=(W,E))
        Button(frame, text='Auto. Approach', command=self.run_automatic_approach).grid(
            row=6, column=1, sticky=(W,E))
        
        self.params['approach'] = {'voltage': V, 'cutoff': I, 'z_height': Z,
                                   'step_size': step, 'rel_current': rel_current}
        return
    
    
    def MakeHoppingFrame(self, frame):
        left_labels = ['Length:', 'Z height:', 'Points per line:']
        right_labels = ['μm', 'μm', '(n x n grid)']
        Labels_in_column(frame, left_labels, 0, 0, (E))
        Labels_in_column(frame, right_labels, 2, 0, (W))
        
        length = EntryStringVar(frame, 6, 0, 1, (W,E), tab=True, returnTab=True, 
                           default=50)
        height = EntryStringVar(frame, 6, 1, 1, (W,E), tab=True, returnTab=True, 
                           default=-5)
        n_pts = EntryStringVar(frame, 6, 2, 1, (W,E), tab=True, returnTab=True, 
                           default=10)
        
        method = OptionMenuStringVar(frame, hopping_methods, 3, 1, (W,E))
        
        Button(frame, text='Hopping mode scan', command=self.run_hopping).grid(
            row=4, column=1, sticky=(W,E))
        Button(frame, text='Multi hopping scan', command=self.run_multi_hopping).grid(
            row=5, column=1, sticky=(W,E))
        Button(frame, text='Image pattern mode', command=self.run_hopping_image).grid(
            row=6, column=1, sticky=(W,E))
        # Button(frame, text= 'Multi hopping multi CA scan', command=self.run_multi_CA_hopping).grid(
        #     row=7, column=1, sticky=(W,E))
        
        self.params['hopping'] = {'size': length, 'Z': height, 'n_pts': n_pts, 
                                  'method': method}
        return




    def MakePiezoFrame(self, frame):
        tabs = Notebook(frame)
        PiezoControlFrame = Frame(tabs)
        PicoMotorFrame = Frame(tabs)
        tabs.add(PiezoControlFrame, text='Piezo')
        tabs.add(PicoMotorFrame, text='Coarse Piezos')
        tabs.pack(expand=1, fill='both')
        
        self.MakePiezoControlFrame(PiezoControlFrame)
        self.MakePicoMotorFrame(PicoMotorFrame)
        return
    
    
    def MakePiezoControlFrame(self, frame):
        self._x_display = StringVar()
        self._y_display = StringVar()
        self._z_display = StringVar()
        
        self._x_set = StringVar(value='0')
        self._y_set = StringVar(value='0')
        self._z_set = StringVar(value='0')
        
        Label(frame, text='  X:').grid(row=0, column=0, sticky=(W,E))
        Label(frame, textvariable=self._x_display).grid(row=0, column=1, sticky=(W,E))
        Label(frame, text='  Y:').grid(row=0, column=2, sticky=(W,E))
        Label(frame, textvariable=self._y_display).grid(row=0, column=3, sticky=(W,E))
        Label(frame, text='  Z:').grid(row=0, column=4, sticky=(W,E))
        Label(frame, textvariable=self._z_display).grid(row=0, column=5, sticky=(W,E))
        Label(frame, text= ' (μm)').grid(row=0, column=6, sticky=(W))
        
        Entry(frame, textvariable=self._x_set, width=6).grid(row=1, column=0, columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self._y_set, width=6).grid(row=1, column=2, columnspan=2, sticky=(W,E))
        Entry(frame, textvariable=self._z_set, width=6).grid(row=1, column=4, columnspan=2, sticky=(W,E))
        Button(frame, text='Set', command=self.piezo_goto).grid(row=1, column=6, sticky=(W,E))
        
        Button(frame, text='Restart Position Monitoring', command=self.piezo_reading_reset).grid(
            row=2, column=0, columnspan=7, sticky=(W,E))
        return
    
    
    def MakePicoMotorFrame(self, frame):
        self._z_piezosteps  = StringVar(value='0')
        self._y_piezosteps  = StringVar(value='0')
        
        Label(frame, text='Z Dist:').grid(row=0, column=0, sticky=(W,E))
        Entry(frame, textvariable=self._z_piezosteps, width=8).grid(row=0, column=1, sticky=(W,E))
        Button(frame, text='Go Z', command=self.z_piezo_go).grid(row=0, column=2, sticky=(W,E))
        
        Label(frame, text='Y Dist:').grid(row=1, column=0, sticky=(W,E))
        Entry(frame, textvariable=self._y_piezosteps, width=8).grid(row=1, column=1, sticky=(W,E))
        Button(frame, text='Go Y', command=self.y_piezo_go).grid(row=1, column=2, sticky=(W,E))
        
        Label(frame, text='μm (positive is up, negative is down)').grid(row=0, column=3, sticky=(W))
        Label(frame, text='μm').grid(row=1, column=3, sticky=(W))
        Button(frame, text='Stop', command=self.z_piezo_stop).grid(row=2, column=1, columnspan=2, sticky=(W,E))
        return




    def MakeHeatmapFrame(self, frame):
        self.HeatmapFig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        self.HeatmapFig.add_subplot(111)
        
        Label(frame, text='SECCM').grid(row=0, column=0, sticky=(W,E))
        Label(frame, text='Display:').grid(row=0, column=2, sticky=(W,E))
        self.heatmapselection = OptionMenuStringVar(frame, heatmapOptions,
                                                    row=1,col=2,sticky=(W,E))
        self.heatmapselection.trace('w', self.heatmap_opt_changed)
        
        self.HeatMapDisplayParam = EntryStringVar(frame, width=8, row=1,
                                            col=3, sticky=(W,E), bind_key='<Return>',
                                            bind_func = self.heatmap_opt_changed)
        Button(frame, text='Zoom to grid...', 
               command=self.heatmap_rect_zoom).grid(column=0, row=1,
                                                    sticky=(W,E))
        Button(frame, text='Set new area',
               command=self.set_new_area).grid(column=1, row=1,
                                               sticky=(W,E))
        
        FigureCanvasTkAgg(self.HeatmapFig, master=frame).get_tk_widget().grid(
                                              row=2, column=0, columnspan=10)
        return
        
                              
                              
                              
    def MakeEchemFrame(self, frame):
        self.EchemFig = plt.Figure(figsize=(4.5,4.5), dpi=75)
        self.EchemFig.add_subplot(111)
        
        Label(frame, text='Electrochemistry').grid(column=0, row=0)
        
        # Voltammetry view options
        self.fig2selection, self.fig2typeoptmenu = OptionMenuStringVar(
                                                frame, fig2Options,idx=2,
                                                row=1, col=0, sticky=(W,E),
                                                return_widget=True)
        
        # PointsList selection options
        self.fig2ptselection, self.fig2ptoptmenu = OptionMenuIntVar(frame, [0,], 1, 1, (W,E),
                                                                    return_widget=True)                    
        
        # EIS view options
        self.EIS_view_selection = OptionMenuStringVar(frame, EIS_options, 1, 2, (W,E))
        
                       
        # Reset ADC view button
        Button(frame, text='View ADC', command=self.reset_ADC_monitor).grid(
                   column=3, row=1, sticky=(E))
                       
        FigureCanvasTkAgg(self.EchemFig, master=frame).get_tk_widget().grid(
                                              row=2, column=0, columnspan=10)  
        return
        
        
        
        
    def MakeOptionFrame(self, frame):
        tabs = Notebook(frame)
        
        HeatMapScaleFrame = Frame(tabs)
        HeatMapColorFrame = Frame(tabs)
        
        self.MakeHeatMapScaleFrame(HeatMapScaleFrame)
        self.MakeHeatMapColorFrame(HeatMapColorFrame)
        
        tabs.add(HeatMapScaleFrame, text='Heatmap Scale')
        tabs.add(HeatMapColorFrame, text='Colormap')
        tabs.pack(expand=1, fill='both')
        
    
    def MakeHeatMapScaleFrame(self, frame):
        Button(frame, text='Zoom out', 
               command=self.master.Plotter.Heatmap.zoom_out).grid(
               row=1, column=2, sticky=(W,E))
        Button(frame, text='Zoom in', 
               command=self.master.Plotter.Heatmap.zoom_in).grid(
               row=1, column=3, sticky=(W,E))
        
        Button(frame, text='-', width=1,
               command=self.master.Plotter.Heatmap.zoom_lower_subt).grid(
               row=2, column=0, sticky=(W,E))  
        Button(frame, text='+', width=1,
               command=self.master.Plotter.Heatmap.zoom_lower_add).grid(
               row=2, column=1, sticky=(W,E))    
        
        self.heatmap_min_val = EntryStringVar(frame, 5, 2, 2, (W,E), bind_key='<Return>',
                                              bind_func=self.master.Plotter.Heatmap.apply_minmax_fields,
                                              tab=True, default='0')          
        
        self.heatmap_max_val = EntryStringVar(frame, 5, 2, 3, (W,E), bind_key='<Return>',
                                              bind_func=self.master.Plotter.Heatmap.apply_minmax_fields,
                                              tab=True, default='0')
        
        Button(frame, text='-', width=1,
               command=self.master.Plotter.Heatmap.zoom_upper_subt).grid(
               row=2, column=4)
        Button(frame, text='+', width=1,
               command=self.master.Plotter.Heatmap.zoom_upper_add).grid(
               row=2, column=5)
        
        Button(frame, text='Apply', 
               command=self.master.Plotter.Heatmap.apply_minmax_fields).grid(
               row=3, column=2, sticky=(W,E))
        Button(frame, text='Reset', 
               command=self.master.Plotter.Heatmap.cancel_popup).grid(
               row=3, column=3, sticky=(W,E))
        return
    
    
    def MakeHeatMapColorFrame(self, frame):
        self.heatmap_cmap = OptionMenuStringVar(frame, cmaps, 0, 1, (W,E))
        
        self.heatmap_cmap_minval = StringVar(value='0')
        self.heatmap_cmap_maxval = StringVar(value='1')
        
        Label(frame, text='Min: ').grid(row=1, column=0, sticky=(W,E))
        self.heatmap_cmap_minval = EntryStringVar(frame, 3, 1, 1, (W,E), tab=True,
                                                  bind_key='<Return>', bind_func=
                                                  self.master.Plotter.Heatmap.update_colormap,
                                                  default='0')
        Label(frame, text='Max: ').grid(row=1, column=2, sticky=(W,E))
        self.heatmap_cmap_maxval = EntryStringVar(frame, 3, 1, 3, (W,E), tab=True,
                                                  bind_key='<Return>', bind_func=
                                                  self.master.Plotter.Heatmap.update_colormap,
                                                  default='1')
        Button(frame, text='Apply', command=self.master.Plotter.Heatmap.update_colormap).grid(
            row=2, column=1, columnspan=2)
        return


def make_CV_fig(ax):
    arr = np.concatenate((
        np.zeros(10),
        np.linspace(0,1,10),
        np.linspace(1,-1,20),
        np.linspace(-1,0,10)        
        ))
    ax.plot(arr)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(0, 0.1, 'E 0')
    ax.text(0, -0.3, 't 0 -->')
    ax.text(22, 0.8, 'E 1')
    ax.text(42, -0.95, 'E 2')
    ax.text(46, 0.1, 'E f')
    ax.text(0, -0.95, 'v = scan rate')


