#!/usr/bin/python
# -*- coding: utf8 -*-

from brian import *
from brian.library.IF import *
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import os

fIn = 'wmxR.txt'

SWBasePath = os.path.split(os.path.split(__file__)[0])[0]

NE = 4000
NI = 1000

# sparseness
eps_pyr = 0.16
eps_bas = 0.4

# parameters for pyr cells
z = 1*nS
gL_Pyr = 4.333e-3 * uS  # 3.3333e-3
tauMem_Pyr = 60.0 * ms
Cm_Pyr = tauMem_Pyr * gL_Pyr
Vrest_Pyr = -70.0 * mV
reset_Pyr = -53.0*mV
theta_Pyr = -50.0*mV
tref_Pyr = 5*ms

# Adaptation parameters for pyr cells
a_Pyr = -0.8*nS  # nS    Subthreshold adaptation conductance
b_Pyr = 0.04*nA  # nA    Spike-triggered adaptation
delta_T_Pyr = 2.0*mV  # Slope factor
tau_w_Pyr = 300*ms  # Adaptation time constant

v_spike_Pyr = theta_Pyr + 10*delta_T_Pyr

# parameters for bas cells
gL_Bas = 5.0e-3*uS  # 7.14293e-3
tauMem_Bas = 14.0*ms
Cm_Bas = tauMem_Bas * gL_Bas
Vrest_Bas = -70.0*mV
reset_Bas = -64.0*mV  # -56.0
theta_Bas  = -50.0*mV
tref_Bas = 0.1*ms  # 0.1*ms

# synaptic weights
J_PyrInh = 0.125  # nS
J_BasExc = 5.2083
J_BasInh = 0.15  # 0.08333 #0.15

print 'J_PyrInh:', J_PyrInh
print 'J_BasExc:', J_BasExc
print 'J_BasInh:', J_BasInh

J_PyrMF = 5.0  #8.0 #2.0 #5.0

# Synaptic reversal potentials
E_Exc = 0.0*mV
E_Inh = -70.0*mV

# Synaptic time constants
tauSyn_PyrExc = 10.0*ms
tauSyn_PyrInh = 3.0*ms
tauSyn_BasExc = 3.0*ms
tauSyn_BasInh = 1.5*ms

# Synaptic delays
delay_PyrExc = 3.0*ms
delay_PyrInh = 1.5*ms
delay_BasExc = 3.0*ms
delay_BasInh = 1.5*ms

p_rate_mf = 5.0*Hz  #10.0*Hz

# Creating populations
eqs_adexp = '''
dvm/dt = (-gL_Pyr*(vm-Vrest_Pyr) + gL_Pyr*delta_T_Pyr*exp((vm- theta_Pyr)/delta_T_Pyr)-w - (g_ampa*z*(vm-E_Exc) + g_gaba*z*(vm-E_Inh)))/Cm_Pyr : volt
dw/dt = (a_Pyr*(vm- Vrest_Pyr )-w)/tau_w_Pyr : amp
dg_ampa/dt = -g_ampa/tauSyn_PyrExc : 1
dg_gaba/dt = -g_gaba/tauSyn_PyrInh : 1
'''

reset_adexp = '''
vm = reset_Pyr
w += b_Pyr
'''

eqs_bas = '''
dvm/dt = (-gL_Bas*(vm-Vrest_Bas) - (g_ampa*z*(vm-E_Exc) + g_gaba*z*(vm-E_Inh)))/Cm_Bas :volt
dg_ampa/dt = -g_ampa/tauSyn_BasExc : 1
dg_gaba/dt = -g_gaba/tauSyn_BasInh : 1
'''

def myresetfunc(P, spikes):
    P.vm[spikes] = reset_Pyr   # reset voltage
    P.w[spikes] += b_Pyr  # low pass filter of spikes (adaptation mechanism)


SCR = SimpleCustomRefractoriness(myresetfunc, tref_Pyr, state='vm')

PE = NeuronGroup(NE, model=eqs_adexp, threshold=v_spike_Pyr, reset=SCR)

PI = NeuronGroup(NI, model=eqs_bas, threshold=theta_Bas, reset=reset_Bas, refractory=tref_Bas)

PE.vm = Vrest_Pyr
PE.g_ampa = 0
PE.g_gaba = 0

PI.vm  = Vrest_Bas
PI.g_ampa = 0
PI.g_gaba = 0

MF = PoissonGroup(NE, p_rate_mf)

print 'Connecting the network'

Cext = IdentityConnection(MF, PE, 'g_ampa', weight=J_PyrMF)

Cee = Connection(PE, PE, 'g_ampa', delay=delay_PyrExc)

fName = os.path.join(SWBasePath, 'files', fIn)
f = file(fName, 'r')

Wee = [line.split() for line in f]

f.close()

for i in range(NE):
    Wee[i][:] = [float(x) * 1.e9 for x in Wee[i]]
    Wee[i][i] = 0.

Cee.connect(PE, PE, Wee)

Cei = Connection(PE, PI, 'g_ampa', weight=J_BasExc, sparseness=eps_pyr, delay=delay_BasExc)
Cie = Connection(PI, PE, 'g_gaba', weight=J_PyrInh, sparseness=eps_bas, delay=delay_PyrInh)
Cii = Connection(PI, PI, 'g_gaba', weight=J_BasInh, sparseness=eps_bas, delay=delay_PyrInh)

print 'Connections done'

# Monitors
sme = SpikeMonitor(PE)
smi = SpikeMonitor(PI)
popre = PopulationRateMonitor(PE, bin=1*ms)
popri = PopulationRateMonitor(PI, bin=1*ms)
poprext = PopulationRateMonitor(MF, bin=0.001)
bins = [0*ms, 50*ms, 100*ms, 150*ms, 200*ms, 250*ms, 300*ms, 350*ms, 400*ms, 450*ms, 500*ms,
        550*ms, 600*ms, 650*ms, 700*ms, 750*ms, 800*ms, 850*ms, 900*ms, 950*ms, 1000*ms]
isi = ISIHistogramMonitor(PE, bins)

run(10000*ms, report='text')

def replay(isi):
    '''
    Decides if there is a replay or not:
    searches for the max # of spikes (and plus one bin one left- and right side)
    if the 90% of the spikes are in that 3 bins then it's periodic activity: replay
    :param isi: Inter Spike Intervals of the pyr. pop.
    :return avgReplayInterval: counted average replay interval
    '''

    binsROI = isi
    binMeans = np.linspace(175, 825, 14)
    maxInd = np.argmax(binsROI)

    if 1 <= maxInd <= len(binsROI) - 2:
        bins3 = binsROI[maxInd-1:maxInd+2]
        tmp = binsROI[maxInd-1]*binMeans[maxInd-1] + binsROI[maxInd]*binMeans[maxInd] + binsROI[maxInd+1]*binMeans[maxInd+1]
        avgReplayInterval = tmp / (binsROI[maxInd-1] + binsROI[maxInd] + binsROI[maxInd+1])
    else:
        bins3 = []

    if sum(int(i) for i in binsROI) * 0.9 < sum(int(i) for i in bins3):
        print 'Replay,', 'avg. replay interval:', avgReplayInterval, '[ms]'
    else:
        avgReplayInterval = np.nan
        print 'Not replay'

    return avgReplayInterval

def ripple(rate):
    '''
    Decides if there is a high freq. ripple oscillation or not
    calculates the autocorrelation and the power spectrum of the activity
    :param rate: firing rate of the neuron population
    :return: meanr, rAC: mean rate, autocorrelation of the rate
             maxAC, tMaxAC: maximum autocorrelation, time interval of maxAC
             maxACR, tMaxAC: maximum autocorrelation in ripple range, time interval of maxACR
             f, Pxx: sample frequencies and power spectral density (results of PSD analysis)
    '''

    meanr = np.mean(rate)
    rUb = rate - meanr
    rVar = np.sum(rUb**2)
    rAC = np.correlate(rUb, rUb, mode='same') / rVar  # cross correlation of reub and reub -> autocorrelation
    rAC = rAC[len(rAC)/2:]

    maxAC = rAC[1:].max()
    tMaxAC = rAC[1:].argmax()+1
    maxACR = rAC[3:9].max()
    tMaxACR = rAC[3:9].argmax()+3

    # see more: http://docs.scipy.org/doc/scipy-dev/reference/generated/scipy.signal.welch.html
    fs = 10000
    f, Pxx = signal.welch(rate, fs)

    return meanr, rAC, maxAC, tMaxAC, maxACR, tMaxACR, f, Pxx

avgReplayInterval = replay(isi.count[3:17])  # bins from 150 to 850 (range of interest)

meanEr, rEAC, maxEAC, tMaxEAC, maxEACR, tMaxEACR, fE, PxxE = ripple(popre.rate)
meanIr, rIAC, maxIAC, tMaxIAC, maxIACR, tMaxIACR, fI, PxxI = ripple(popri.rate)


print 'Mean excitatory rate: ', meanEr
print 'Maximum exc. autocorrelation:', maxEAC, 'at', tMaxEAC, '[ms]'
print 'Maximum exc. AC in ripple range:', maxEACR, 'at', tMaxEACR, '[ms]'
print 'Mean inhibitory rate: ', meanIr
print 'Maximum inh. autocorrelation:', maxIAC, 'at', tMaxIAC, '[ms]'
print 'Maximum inh. AC in ripple range:', maxIACR, 'at', tMaxIACR, '[ms]'


# Plots

# Population activity, ISI
fig = plt.figure(figsize=(10, 8))

subplot(2, 1, 1)
raster_plot(sme, spacebetweengroups=1, title='Raster plot', newfigure=False)

subplot(2, 1, 2)
hist_plot(isi, title='ISI histogram', newfigure=False)
xlim([0, 1000])

fig.tight_layout()

# Exc. autocorrelolgram, PSD
rEACPlot = rEAC[2:201]  # 500 - 5 Hz interval
rEACRipple = rEAC[3:9]  # 333 - 125 Hz interval

fERoi = np.where(fE < 550)  # tuple with indices
fEPlot = fE[0:fERoi[0][-1]]
PxxEPlot = PxxE[0:fERoi[0][-1]]
ftmp1 = np.where(fEPlot > 125)
ftmp2 = np.where(fEPlot < 333)
fERipple = fEPlot[ftmp1[0][0]:ftmp2[0][-1]]
PxxERipple = PxxEPlot[ftmp1[0][0]:ftmp2[0][-1]]

fig2 = plt.figure(figsize=(10, 8))

ax = fig2.add_subplot(2, 1, 1)
ax.plot(np.linspace(2, 200, len(rEACPlot)), rEACPlot, 'b-', label='AC of exc. firing rates (2-200 ms)')
ax.plot(np.linspace(3, 8, 6), rEACRipple, 'r-', linewidth=2, label='AC of exc. firing rates (3-8 ms)')
ax.set_title('Autocorrelogram (of firing rates in pyr. pop.)')
ax.set_xlabel('Time (ms)')
ax.set_xlim([2, 200])
ax.set_ylabel('AutoCorrelation')
ax.legend()

ax2 = fig2.add_subplot(2, 1, 2)
ax2.semilogy(fEPlot, PxxEPlot, 'b-', label='PSD of exc. firing rates (0-500 Hz)')
ax2.semilogy(fERipple, PxxERipple, 'r-', linewidth=2, label='PSD of exc. firing rates (125-333 Hz)')
ax2.set_xlim([0, 500])
ax2.set_xlabel('frequency [Hz]')
ax2.set_title('Power Source Density (of firing rates in pyr. pop.)')
ax2.legend()

fig2.tight_layout()

# Inh. autocorrelolgram, PSD
rIACPlot = rIAC[2:201]  # 500 - 5 Hz interval
rIACRipple = rIAC[3:9]  # 333 - 125 Hz interval

fIRoi = np.where(fI < 550)  # tuple with indices
fIPlot = fI[0:fIRoi[0][-1]]
PxxIPlot = PxxI[0:fIRoi[0][-1]]
ftmp1 = np.where(fIPlot > 125)
ftmp2 = np.where(fIPlot < 333)
fIRipple = fIPlot[ftmp1[0][0]:ftmp2[0][-1]]
PxxIRipple = PxxIPlot[ftmp1[0][0]:ftmp2[0][-1]]

fig3 = plt.figure(figsize=(10, 8))

ax = fig3.add_subplot(2, 1, 1)
ax.plot(np.linspace(2, 200, len(rIACPlot)), rIACPlot, 'g-', label='AC of inh. firing rates (2-200 ms)')
ax.plot(np.linspace(3, 8, 6), rIACRipple, 'r-', linewidth=2, label='AC of inh. firing rates (3-8 ms)')
ax.set_title('Autocorrelogram (of firing rates in bas. pop.)')
ax.set_xlabel('Time (ms)')
ax.set_xlim([2, 200])
ax.set_ylabel('AutoCorrelation')
ax.legend()

ax2 = fig3.add_subplot(2, 1, 2)
ax2.semilogy(fIPlot, PxxIPlot, 'g-', label='PSD of inh. firing rates (0-500 Hz)')
ax2.semilogy(fIRipple, PxxIRipple, 'r-', linewidth=2, label='PSD of inh. firing rates (125-333 Hz)')
ax2.set_xlim([0, 500])
ax2.set_xlabel('frequency [Hz]')
ax2.set_title('Power Source Density (of firing rates in bas. pop.)')
ax2.legend()

fig3.tight_layout()

plt.show()
