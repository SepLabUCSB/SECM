from tkinter import *
from tkinter.ttk import *
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from ..utils.utils import Logger





class ImageCorrelator(Logger):
    
    def __init__(self, master):
        self.master = master
        self.master.register(self)
        
    
    def load_image(self, file):
        pass
    
    
    def draw_on_point(self, x, y):
        pass





