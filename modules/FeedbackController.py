import numpy as np
import time
import matplotlib.pyplot as plt


def get_xy_coords(length, n_points):
        # Generate ordered list of xy coordinates for a scan
        # ----->
        # <-----
        # ----->
        points = []
        order  = []
        coords = np.linspace(0, length, n_points)
        
        reverse = False
        i, j = 0, 0 # i -> x, j -> y
        for x in coords:
            if reverse:
                for j, y in reversed(list(enumerate(coords))):
                    points.append((x,y))
                    order.append((i,j))
                reverse = False
                i += 1
            else:
                for j, y in enumerate(coords):
                    points.append((x,y))
                    order.append((i,j))
                reverse = True
                i += 1
        return points, order




class FeedbackController():
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        self.willStop = False
        
        # Get local refs to other modules
        self.Piezo = self.master.Piezo
        self.ADC = self.master.ADC
        self.HekaWriter = self.master.HekaWriter

    

    def approach_curve(self, i_cutoff):
        
        # current = self.ADC.get_current()
        current = np.random.rand()
        return current
    
    def hopping_mode(self, params, fig):
        
        length = params['size'].get('1.0', 'end')
        height = params['Z'].get('1.0', 'end')
        n_pts  = params['n_pts'].get('1.0', 'end')
        
        length = float(length) 
        height = float(height)
        n_pts  = int(n_pts)
        
        points, order = get_xy_coords(length, n_pts)
        
        # Setup figure, need blitting to plot fast enough
        gridpts = np.array([
            np.array([0 for _ in range(n_pts)]) for _ in range(n_pts)
            ], dtype=np.float32)
        
        ax = fig.gca()
        image = ax.imshow(gridpts, cmap='afmhot')
        fig.canvas.draw()
        
        bg = fig.canvas.copy_from_bbox(ax.bbox)
        ax.draw_artist(image)
        fig.canvas.blit(ax.bbox)
        
        
        for i, (x, y) in enumerate(points):
            if self.master.STOP:
                return
            self.Piezo.goto(x, y, height)
            
            # TODO: run variable echem experiment(s) at each pt
            I = self.approach_curve(0)
            
            grid_i, grid_j = order[i]
            # gridpts[grid_i][grid_j] = I
            gridpts[grid_i][grid_j] = i
            
            image.set_data(gridpts)
            minval = min(gridpts.flatten())
            maxval = max(gridpts.flatten())
            image.set(clim=( minval - abs(0.1*minval), # Update color scale
                             maxval + abs(0.1*maxval)) 
                      ) 
            
            ax.draw_artist(image)
            fig.canvas.blit(ax.bbox)
            
            fig.canvas.draw_idle()
            plt.pause(0.001)
        
        
        return

    


