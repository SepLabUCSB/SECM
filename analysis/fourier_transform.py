from io import StringIO
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
plt.style.use(r'C:/Users/BRoehrich/Desktop/git/SECM/secm.mplstyle')


file = r'C:/Users/BRoehrich/Desktop/New folder/EIS off surface.asc'


def read_heka_data(file):
    # Use StringIO to parse through file (fastest method I've found)
    # Convert only floats to np arrays
    
    def isFloat(x):
        try: 
            float(x)
            return True
        except: 
            return False
    
    s = StringIO()
    with open(file, 'r') as f:
        for line in f:
            if isFloat(line.split(',')[0]):
                # Check for index number
                s.write(line)
    if s.getvalue() != '':
        s.seek(0)
        array = np.genfromtxt(s, delimiter=',')
        array = array.T
        return array



_, t, I, _, V = read_heka_data(file)

#%%

freq = 10000*np.fft.rfftfreq(len(V))[1:]
ft_V = np.fft.rfft(V)[1:]
ft_I = np.fft.rfft(I)[1:]


idxs = [i for i, v in enumerate(abs(ft_V)) if v > 5]

freq = freq[idxs]
ft_V = ft_V[idxs]
ft_I = ft_I[idxs]

Z = ft_V/ft_I


fig, ax = plt.subplots()
ax.plot(np.real(Z)/1e6, -np.imag(Z)/1e6, 'o-')
ax.set_xlabel(r"Z'/ M$\Omega$")
ax.set_ylabel(r"Z''/ M$\Omega$")
low = min(ax.get_xlim()[0], ax.get_ylim()[0])
high = max(ax.get_xlim()[1], ax.get_ylim()[1])
ax.set_xlim(low, high)
ax.set_ylim(low, high)
# ax.set_xticks([0,100,200,300,400,500])
# ax.set_yticks([0,100,200,300,400,500])
ax.set_title('EIS off surface')






