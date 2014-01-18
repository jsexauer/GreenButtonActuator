# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 19:34:01 2014

@author: Jason
"""

datafile = 'DailyElectricUsage.csv'
pnodes = ['BARBADOES35 KV  ABU2','BETZWOOD230 KV  LOAD1','PECO','_ENERGY_ONLY']



import pandas
import numpy as np
import matplotlib.pylab as plt
plt.close('all')

# Read in usage log (csv format, probably specific to PECO)
df = pandas.read_csv(datafile, skiprows=4)

# Convert costs (drop dollar sign and convert to float)
df['COST'] = df['COST'].str.slice(1).apply(lambda x: float(x))

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


def densityCloudByTags(df, columns):
    """Create density cloud of data for a given tag or group of tags
    For example:
        columns='DayOfWeek' --> Plots for Mon, Tue, Wed, Thur, ...
        columns='Weekday' --> Plots of weekends vs weekday
        columns=['Season','Weekday'] 
            --> Plots of Summer, Spring, Winter, Fall Weekdays and Weekends
    """
    if columns == 'hr' or 'hr' in columns:
        raise ValueError("Columns cannot contain hr tag")
        
    # Create a profile for day of week
    maxY = df['USAGE'].max()
    for label, data in df.groupby(columns):    
        
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
        plt.title('Typical usage on %s' % str(label))
        plt.grid(axis='y')
        plt.show()

#densityCloudByTags(df, 'DayOfWeek')
#densityCloudByTags(df, 'Weekday')
#densityCloudByTags(df, ['Season','Weekday'])

############################################################################

# What if we paid wholesale prices at our local pnode?

for pnode in pnodes:
    # Bring in PJM prices from DataMiner
    pnode_prices = pandas.read_csv('pnode_data/%s.csv' % pnode)
    assert len(pnode_prices['PRICINGTYPE'].unique()) == 1
    assert pnode_prices['PRICINGTYPE'].unique()[0] == 'TotalLMP'
    
    # Unpiviot the data
    pnode_prices = pandas.melt(pnode_prices, id_vars=['PUBLISHDATE'],
                value_vars=['H%d'%i for i in xrange(1,25)])
    pnode_prices = pnode_prices.rename(columns={
                'variable':'Hour',
                'value':'Price'})
    # Convert hour to standard format and to hour beginning standard
    cvtHr = lambda x: "%d:00" % (int(x)-1)
    pnode_prices['Hour'] = pnode_prices['Hour'].str.slice(1).apply(cvtHr)
    pnode_prices['ts'] = \
        (pnode_prices['PUBLISHDATE']+' '+
         pnode_prices['Hour'])              .apply(makeTimestamp)
    pnode_prices = pnode_prices.set_index('ts', drop=False)
    # Convert prices to $/kWhr (currently $/MWhr)
    pnode_prices['Price'] = pnode_prices['Price']/1000

    # Figure out what our wholesale price would have been
    df['pnode_'+pnode] = df['USAGE'] * pnode_prices['Price']

cols = ['COST'] + ['pnode_'+p for p in pnodes]
df[cols].plot()
df[cols].cumsum().plot()








