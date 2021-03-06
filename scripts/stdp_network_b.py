#!/usr/bin/python
# -*- coding: utf8 -*-

import brian_no_units
from brian import *
import numpy as np
import matplotlib.pyplot as plt
import os
from detect_oscillations import ripple, gamma

fIn = 'spikeTrainsR.npz'
fOut = 'wmxR.txt'

SWBasePath = os.path.split(os.path.split(__file__)[0])[0] # '/home/bandi/workspace/KOKI/SharpWaves'

N = 4000  # #{neurons}

# importing spike times from file
fName = os.path.join(SWBasePath, 'files', fIn)
npzFile = np.load(fName)
spikeTrains = npzFile['spikeTrains']

spiketimes = []

for neuron in range(N):
    nrn = neuron * np.ones(len(spikeTrains[neuron]))
    z = zip(nrn, spikeTrains[neuron])
    spiketimes.append(z)

spiketimes = [item for sublist in spiketimes for item in sublist]

PC = SpikeGeneratorGroup(N, spiketimes)


def learning(spikingNeuronGroup):
    '''
    Takes a spiking group of neurons, connects the neurons sparsely with each other,
    and learns a 'pattern' via STDP
    :param spikingNeuronGroup: Brian class of spiking neurons
    :return weightmx: numpy ndarray with the learned synaptic weights
            sp: SpikeMonitor of the network (for plotting and further analysis)
    '''

    Conn = Connection(spikingNeuronGroup, spikingNeuronGroup, weight=0.1e-9, sparseness=0.16)

    # f(s) = A_p * exp(-s/tau_p) (if s > 0)
    # A_p = 0.01, tau_p = 20e-3
    # see more: https://brian.readthedocs.org/en/1.4.1/reference-plasticity.html#brian.ExponentialSTDP
    stdp = ExponentialSTDP(Conn, 20e-3, 20e-3, 0.01, -0.01, wmax=40e-9, interactions='all', update='additive')

    # run simulation
    sp = SpikeMonitor(spikingNeuronGroup, record=True)
    run(400, report='text')

    # weight matrix
    weightmx = [[Conn[i, j] for j in range(N)] for i in range(N)]

    return weightmx, sp


weightmx, sp = learning(PC)

tmp = np.asarray(weightmx)
weightmx = np.reshape(tmp, (4000, 4000))

np.fill_diagonal(weightmx, 0)

# save weightmatrix
fName = os.path.join(SWBasePath, 'files', fOut)
np.savetxt(fName, weightmx)


# Plots
figure(figsize=(10, 8))
raster_plot(sp, spacebetweengroups=1, title='Raster plot', newfigure=False)

fig2 = plt.figure(figsize=(10, 8))
ax = fig2.add_subplot(1, 1, 1)
i = ax.imshow(weightmx, interpolation='None')
fig2.colorbar(i)
ax.set_title('Learned weight matrix')

plt.show()
