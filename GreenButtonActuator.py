# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 19:34:01 2014

@author: Jason
"""

datafile = 'DailyElectricUsage.csv'



import pandas
import numpy as np
import matplotlib.pylab as plt
plt.close('all')

# Read in usage log (csv format, probably specific to PECO)
df = pandas.read_csv(datafile, skiprows=4)

# Convert times
makeTimestamp = lambda x: pandas.Timestamp(x)
df['ts'] = (df['DATE']+' '+df['START TIME']).apply(makeTimestamp)
df.set_index('ts', drop=False, inplace=True)

df['hr'] = df['ts'].apply(lambda x: int(x.strftime('%H')))


# Create a few tags
df['Weekday'] = df['ts'].apply(lambda x: 'Weekday' if x.weekday() else 'Weekend')
df['DayOfWeek'] = df['ts'].apply(lambda x: x.strftime('%a'))
def getSeason(x):
    month = x.month
    if 6 <= month <= 8:
        return 'Summer'
    elif 9 <= month <= 11:
        return 'Fall'
    elif 3 <= month <= 5:
        return 'Spring'
    else:
        return 'Winter'    
df['Season'] = df['ts'].apply(getSeason)
df['Month'] = df['ts'].apply(lambda x: x.strftime('%b'))


# Look at only data since high-resolution started
#df = df.ix['2013-11-20':]

assert len(df['UNITS'].unique()) == 1, "Energy values in inconsistent units"


# Create a profile for day of week
maxY = df['USAGE'].max()
for dayOfWeek, data in df.groupby('DayOfWeek'):    
    
    # Find every 10th percentile
    percentiles = {}
    for p in xrange(10,100,10):
        percentiles[p] = data.groupby('hr')['USAGE'].apply(
                                lambda x: np.percentile(x, p))
    percentiles = pandas.DataFrame(percentiles)
    
    # Find mean
    mean = data.groupby('hr')['USAGE'].agg('mean')           
        

    # Create a density cloud of the MW
    X = np.zeros([24, 100]) # Hours by resolution
    Y = np.zeros([24, 100])
    C = np.zeros([24, 100])    
    for hr, data2 in data.groupby('hr'):        
        freq = []
        step = 1
        rng = range(0,51,step)[1:]
        freq += rng
        bins = np.percentile(data2['USAGE'], rng)
        
        rng = range(50,101,step)[1:]
        freq += [100 - a for a in rng]
        bins = np.hstack([bins, np.percentile(data2['USAGE'], rng)])
        freq = np.array(freq)
           
        X[hr,:] = np.ones(len(bins))*hr
        Y[hr,:] = bins
        C[hr,:] = freq
    
    plt.figure()
    plt.xkcd()
    plt.pcolor(X, Y, C, cmap=plt.cm.YlOrRd)
    plt.plot(X[:,1], mean, color='k', label='Mean')
    plt.colorbar().set_label('Probability Higher/Lower than Median')    
    plt.legend(loc='upper left')
    plt.xlabel('Hour of Day')
    plt.ylabel('Usage (kWh)')
    plt.ylim([0, maxY])
    plt.xlim([0,23])
    plt.title('Typical usage on %s' % str(dayOfWeek))
    plt.grid(axis='y')
    plt.show()