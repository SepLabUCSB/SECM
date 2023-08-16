import numpy as np
import matplotlib.pyplot as plt
import scipy
import scipy.ndimage as ndimage
from libtiff import TIFF









class ImageCorrelator():
    
    def __init__(self, img_file):
        # if img_file.endswith('.tif'):
        #     img_file += 'f'
        self.file = img_file
        self.fig, self.ax = plt.subplots(figsize=(4,4), dpi=100)
        self.show_image()
        self.find_gridpts()
        
    
    def show_image(self):
        tif = TIFF.open(self.file)
        self.img = tif.read_image()
        self.ax.imshow(self.img)
        
        
    def find_gridpts(self, n_pts = 10):
        '''
        https://stackoverflow.com/questions/5298884/finding-number-of-colored-shapes-from-picture-using-python/5304140#5304140
        https://stackoverflow.com/questions/9111711/get-coordinates-of-local-maxima-in-2d-array-above-certain-value
        '''
        neighborhood_size = 40
        threshold = 30
        
        data = ndimage.gaussian_filter(self.img, 4)
        
        data_max = ndimage.filters.maximum_filter(data, neighborhood_size)
        maxima = (data == data_max)
        data_min = ndimage.filters.minimum_filter(data, neighborhood_size)
        diff = ((data_max - data_min) > threshold)
        maxima[diff == 0] = 0
        
        labeled, num_objects = ndimage.label(maxima)
        slices = ndimage.find_objects(labeled)
        x, y = [], []
        for dy,dx,_ in slices:
            x_center = (dx.start + dx.stop - 1)/2
            x.append(x_center)
            y_center = (dy.start + dy.stop - 1)/2    
            y.append(y_center)
        
        self.ax.plot(x,y, 'ro')
        self.points = [*zip(x, y)]
        
        ylen, xlen, _ = data.shape
        xlns = np.linspace(0, xlen, n_pts+1)
        ylns = np.linspace(0, ylen, n_pts+1)
        for x,y in zip(xlns, ylns):
            self.ax.axvline(x, color='r')
            self.ax.axhline(y, color='r')
        
        
    
    def assign_gridpts(self):
        '''
        Translate pixel coordinates i.e. (101, 205) to relative coordinates (1, 2)
        '''
        pass




if __name__ == '__main__':
    file = r'C:/Users/BRoehrich/Desktop/images/T1_region4_029.tif'
    IC = ImageCorrelator(file)
    