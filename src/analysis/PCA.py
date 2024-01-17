import os
import numpy as np
import matplotlib.pyplot as plt



folder = r'C:/Users/BRoehrich/Desktop/all_export'

data = []

for file in os.listdir(folder):
    if 'EIS' in file:
        continue
    t, V, I = np.loadtxt(os.path.join(folder,file), skiprows=3, unpack=True,
                         delimiter=',')
    data.append(I)

data = np.array(data)

#%%
colors = plt.cm.Blues(np.linspace(0.2,0.8, data.shape[0]))

fig, ax = plt.subplots()
i = 0
for CV in data:
    ax.plot(V, CV, color=colors[i])
    i += 1
    
#%%

from sklearn.decomposition import PCA

pca = PCA(n_components=7)
principal_components = pca.fit_transform(data)

components, variance = pca.components_, pca.explained_variance_

for i, (dist,curve) in enumerate(zip(principal_components.T, components)):
    fig, ax = plt.subplots()
    ax.plot(V, curve)
    ax.set_title(f'Component {i}')
    
    fig, ax = plt.subplots()
    ax.set_title(f'Component {i}')
    ax.hist(dist, bins=50)
    ax.set_yscale('log')


