from tkinter import *
from tkinter.ttk import *
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
# from libtiff import TIFF
from PIL import Image
from ..utils.utils import Logger





class ImageCorrelator(Logger):
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        self.clicked = False
        self._popup_shown = False
        
    
    def load_image(self, file):
        '''
        Make the popup and show the selected image in self.ax
        '''
        
        # Open the image file
        try:        
            # tif = TIFF.open(file)
            # img = tif.read_image()
            img = Image.open(file)
            self.img = np.array(img)
        except:
            self.log(f'Error: cannot open {file}')
            return
        
        # Make popup
        self.popup = Toplevel()
        self.topframe = Frame(self.popup)
        self.topframe.grid(row=0, column=0)
        self.botframe = Frame(self.popup)
        self.botframe.grid(row=1, column=0)
        
        
        # Show image
        self.fig = plt.Figure(figsize=(5,5), dpi=150)
        self.fig.add_subplot(111)
        self.ax = self.fig.gca()
        
        
        
        self.image1 = self.ax.imshow(self.img, cmap='gray', origin='upper')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for sp in ['right', 'top', 'left', 'bottom']:
            self.ax.spines[sp].set_visible(False)
        
        self.original_axlim = [self.ax.get_xlim(), self.ax.get_ylim()]
        self.rect = matplotlib.patches.Rectangle((0,0), 0, 0, fill=0,
                                                 edgecolor='red', lw=2)
        FigureCanvasTkAgg(self.fig, master=self.botframe
                          ).get_tk_widget().grid(row=0, column=0)
        
        plt.pause(0.001)
        
        
        
        # Connect mouse clicks to draw zoom square
        self.clickedcid = self.fig.canvas.mpl_connect('button_press_event',
                                                      self.on_press)
        self.releasecid = self.fig.canvas.mpl_connect('button_release_event',
                                                      self.on_release)
        self.dragcid    = self.fig.canvas.mpl_connect('motion_notify_event',
                                                      self.on_drag)
        
        # Make other buttons in popup
        Button(self.topframe, text='\n     Reset     \n', command=self.reset).grid(
            row=0, column=0, sticky=(W,E), )
        Button(self.topframe, text='\n     Draw Grid     \n', command=self.draw_grid
               ).grid(row=0, column=1, sticky=(W,E))
        Button(self.topframe, text='\n     Rotate 180     \n', command=self.rotate_180
               ).grid(row=0, column=2, sticky=(W,E))
        Button(self.topframe, text='\n     Flip Vertical     \n', command=self.flip_vert
               ).grid(row=0, column=3, sticky=(W,E))
        Button(self.topframe, text='\n     Flip Horizontal     \n', command=self.flip_horiz
               ).grid(row=0, column=4, sticky=(W,E))
        
        self._popup_shown = True
    
        
    def rotate_180(self):
        self.img = np.rot90(self.img, 2)
        self._redraw()
        
    
    def flip_vert(self):
        self.img = np.flipud(self.img)
        self._redraw()
        
    
    def flip_horiz(self):
        self.img = np.fliplr(self.img)
        self._redraw()
        
        
    def _redraw(self):
        self.image1.set_data(self.img)
        
        self.ax.draw_artist(self.image1)
        self.fig.canvas.draw_idle()
        plt.pause(0.001)
        
        
    def reset(self):
        '''
        Redraw entire original image
        '''
        self.ax.set_xlim(self.original_axlim[0])
        self.ax.set_ylim(self.original_axlim[1])
        self.loc1   = self.loc2   = (0,0)
        self.coord1 = self.coord2 = (0,0)
        self.clear_gridlines()
        self.draw_rect()
        plt.pause(0.001)
     
        
    def on_press(self, event):
        # Click. Start rectangle dragging
        if event.inaxes != self.ax:
            return
        self.clicked = True
        self.loc1   = (event.x, event.y)
        self.coord1 = (event.xdata, event.ydata)
    
    
    def on_release(self, event):
        # Release. Zoom in to rectangle
        self.clicked = False
        self.zoom_to(self.coord1, self.coord2) 
    
    
    def on_drag(self, event):
        if (not self.clicked or event.inaxes != self.ax):
            return
        self.loc2   = (event.x, event.y)
        self.coord2 = (event.xdata, event.ydata)
        
        # Force it to be a square
        def force_square(coord1, coord2):
            x1, y1 = coord1
            x2, y2 = coord2
            width  = x2 - x1
            height = y2 - y1
            
            delta = min(abs(width), abs(height))
            if delta == 0:
                return (x2, y2)
            
            force_x2 = x1 + delta * width/abs(width)
            force_y2 = y1 + delta * height/abs(height)
            return (force_x2, force_y2)
        
        # self.loc2   = force_square(self.loc1, self.loc2)
        # self.coord2 = force_square(self.coord1, self.coord2)
        
        self.draw_rect()
            
        
    def draw_rect(self):
        x1, y1 = self.loc1
        x2, y2 = self.loc2
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
        
        
    def zoom_to(self, corner1, corner2):
        if corner1 == (0,0) or corner2 == (0,0):
            return
        x1, y1 = corner1
        x2, y2 = corner2
        xlim = [x1, x2]
        xlim.sort()
        ylim = [y1, y2]
        ylim.sort(reverse=True)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.loc1   = self.loc2   = (0,0)
        self.coord1 = self.coord2 = (0,0)
        self.draw_rect()
        plt.pause(0.001)
   
    def clear_gridlines(self):
        if hasattr(self, 'gridlns'):
            for artist in self.gridlns:
                artist.remove()
        self.gridlns = []
            
    
    def draw_grid(self):
        self.clear_gridlines()
        plt.pause(0.001)
        
        n_pts = len(self.master.expt.data[0]) # points per row/ column
        
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        v_lines = [n for n in np.linspace(xmin, xmax, n_pts + 1)]
        h_lines = [n for n in np.linspace(ymin, ymax, n_pts + 1)]
        
        self.gridlns = []
        
        for ln in v_lines:
            self.gridlns.append(self.ax.axvline(ln, color='red', lw=0.5))
        for ln in h_lines:
            self.gridlns.append(self.ax.axhline(ln, color='red', lw=0.5))
        for artist in self.gridlns:
            self.ax.draw_artist(artist)
        
        self.fig.canvas.draw_idle()
        plt.pause(0.01)
        
    
    
    def draw_on_pt(self, x, y):
        '''
        Draw a box around the selected point
        '''
        if not self._popup_shown:
            return
        
        width = height = self.master.expt.length
        
        x_frac = x/width
        y_frac = (height - y)/height
        
        n_pts = len(self.master.expt.data[0]) # points per row/ column
        
        xmin, xmax = self.ax.get_xlim()
        ymax, ymin = self.ax.get_ylim()
        
        # Get the relative location in image coordinates
        x_loc = xmin + x_frac*(xmax - xmin)
        y_loc = ymin + y_frac*(ymax - ymin)
        
        x_lines = [n for n in np.linspace(xmin, xmax, n_pts + 1)]
        y_lines = [n for n in np.linspace(ymin, ymax, n_pts + 1)]
        
        
        # Find what box the point falls in
        for xline in x_lines:
            if x_loc >= xline:
                continue
            break
        for yline in y_lines:
            if y_loc >= yline:
                continue
            break
        
        x_delta = x_lines[1] - x_lines[0]
        y_delta = y_lines[1] - y_lines[0]
        
        # Box drawing limits
        y_min = (yline-y_delta-ymax)/(-ymax + ymin)
        y_max = (yline-ymax)/(-ymax + ymin)
        
        x_min = (xline-x_delta-xmin)/(xmax - xmin)
        x_max = (xline-xmin)/(xmax - xmin)
         
        # Lines to draw the box
        lns = [
            self.ax.axvline(xline, ymin=y_min, ymax=y_max, color='red', 
                            lw=1, alpha=0.7),
            self.ax.axvline(xline - x_delta, ymin=y_min, ymax=y_max, color='red', 
                            lw=1, alpha=0.7),
            
            self.ax.axhline(yline, xmin=x_min, xmax=x_max, color='red', 
                            lw=1, alpha=0.7),
            self.ax.axhline(yline - y_delta, xmin=x_min, xmax=x_max, color='red', 
                            lw=1, alpha=0.7),
            ]
        
        # Draw the box
        self.clear_gridlines()
        self.gridlns.extend(lns)
        for artist in self.gridlns:
            self.ax.draw_artist(artist)
        self.fig.canvas.draw_idle()
        plt.pause(0.01)
        
        





