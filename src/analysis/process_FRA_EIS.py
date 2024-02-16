from io import StringIO
import numpy as np
import matplotlib.pyplot as plt
import matplotlib


file = r'D:/SECM/Data/20240124/10MOhm.asc'
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

def extract_data(file):
    def isFloat(x):
        try: 
            float(x)
            return True
        except: 
            return False
        
    s = StringIO()
    with open(file, 'r') as f:
        for line in f:
            if isFloat(line.split(',')[0]) == 1:
                s.write(line)
    s.seek(0)
    array = np.genfromtxt(s, delimiter=',')
    array = array.T
    sweep, f, logf, adY, logadY, reY, imY, phase, reZ, imZ, magZ, logZ = array
    Z = reZ -1j*imZ
    return f, Z

def correct_Z(f, Z):
    correction_file = 'FRA_Z_corrections.csv'
    corr_f, corr_Z, corr_phase = np.loadtxt(correction_file, unpack=True,
                                            delimiter=',')
    
    corr = {freq:(cZ, pZ) for freq, cZ, pZ in zip(corr_f, corr_Z, corr_phase)}
    
    magZ = np.abs(Z)
    phaZ = np.angle(Z, deg=True)
    
    for i in range(len(f)):
        magZ[i] /= corr[f[i]][0]
        phaZ[i] -= corr[f[i]][1]
    
    Z = magZ*np.exp(1j*phaZ*np.pi/180)
    return f, Z
    
    
        


def plot_data(f, Z):
    
    fig, ax = plt.subplots(figsize=(5,5), dpi=300)
    ax.plot(f, np.abs(Z)/1e6, 'o-', color=colors[0])
    ax.set_xscale('log')
    ax2 = ax.twinx()
    ax2.plot(f, np.angle(Z, deg=True), 'o-', color=colors[1])
    ax.set_xlabel('Frequency/ Hz')
    ax.set_ylabel('|Z|/ M$\Omega$')
    ax2.set_ylabel('Phase/ $\degree$')
    
    fig, ax = plt.subplots(figsize=(5,5), dpi=300)
    ax.plot(np.real(Z)/1e6, -np.imag(Z)/1e6, 'o-', color=colors[0])
    ax.set_xlabel("Z'/ M$\Omega$")
    ax.set_ylabel("Z''/ M$\Omega$")
    mini = min(*ax.get_xlim(), *ax.get_ylim())
    maxi = max(*ax.get_xlim(), *ax.get_ylim())
    ax.set_xlim(mini, maxi)
    ax.set_ylim(mini, maxi)
    
    
def save_corrections(f, Z):
    out_file = 'FRA_Z_corrections.csv'
    magn = np.abs(Z)/10e6
    phase = np.angle(Z, deg=True)
    with open(out_file, 'w') as file:
        for freq,mag,pha in zip(f, magn, phase):
            file.write(f'{freq},{mag},{pha}\n')

def export_data(f, Z, path):
    with open(path, 'w') as file:
        file.write("<Frequency>\t<Re(Z)>\t<Im(Z)>\n")
        for freq, z in zip(f, Z):
            file.write(f'{freq}\t{np.real(z)}\t{np.imag(z)}\n')


def main(file):
    f, Z = extract_data(file)
    f, Z = correct_Z(f, Z)
    plot_data(f, Z)
    
    # export_path = file.replace('.asc', '_EIS.txt')
    # export_data(f, Z, export_path)


main(file)


