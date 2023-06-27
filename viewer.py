from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib

matplotlib.use('TkAgg')
plt.style.use('secm.mplstyle')







class MainWindow():
    def __init__(self, root):
        self.root = root
        
        root.title("SECM Data Viewer")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0) 
        root.option_add('*tearOff', FALSE)
        
        menubar = Menu(root)
        root['menu'] = menubar
        menu_file = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        
        menu_file.add_command(label='Open...', command=self.open_file)
        menu_file.add_command(label='Save Settings', command=self.save_settings)
        menu_file.add_command(label='Quit', command=self.Quit)
        
        
        topframe = Frame(root)
        topframe.grid(row=0, column=0, sticky=(N,S,E,W))
        
        botframe = Frame(root)
        botframe.grid(row=1, column=0, sticky=(N,S,E,W))
        
        ### Figures setups ###
        
        topleft = Frame(topframe)
        topleft.grid(row=0, column=0, sticky=(N,S,E,W))
        Separator(topframe, orient='vertical').grid(
            row=0, column=1, sticky=(N,S), padx=10)
        topright = Frame(topframe)
        topright.grid(row=0, column=2, sticky=(N,S,E,W))
        
        self.HeatmapFig = plt.Figure(figsize=(4,4), dpi=100)
        self.HeatmapFig.add_subplot(111)
        self.EchemFig = plt.Figure(figsize=(4,4), dpi=100)
        self.EchemFig.add_subplot(111)
        
        FigureCanvasTkAgg(self.HeatmapFig, master=topleft).get_tk_widget().grid(
            row=0, column=0, padx=10, pady=10)
        Button(topleft, text='Save...', command=self.save_heatmap).grid(
            row=1, column=0, sticky=(E))
        FigureCanvasTkAgg(self.EchemFig, master=topright).get_tk_widget().grid(
            row=0, column=0, padx=10, pady=10)
        Button(topright, text='Save...', command=self.save_echem).grid(
            row=1, column=0, sticky=(E))
        
        
        ### Display options ###
        
        
        
        
        
        
    def open_file(self):
        f = filedialog.askopenfilename(initialdir='D:\SECM\Data')
        if not f.endswith('.secmdata'):
            return
        self.expt = load_from_file(f)
        self.update()
    
    def save_settings(self):
        pass
    
    
    def Quit(self):
        self.root.destroy()
        
    
    def update(self):
        '''
        Redraw all figures
        '''
        pass
    
    
    def save_heatmap(self):
        pass
    
    
    def save_echem(self):
        pass


if __name__ == '__main__':
    root = Tk()
    window = MainWindow(root)
    root.mainloop()
    root.quit()


