# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 19:34:01 2014

@author: Jason
"""


datafile = 'DailyElectricUsage'
pnodes = ['BARBADOES35 KV  ABU2',
          'BETZWOOD230 KV  LOAD1',
          'PECO',
          '_ENERGY_ONLY']
weather_station = 'KLOM_norristown'


import pandas
import numpy as np
import matplotlib.pylab as plt
import os, sys
from datetime import datetime

root = os.path.dirname(os.path.realpath(__file__))+os.sep

plt.ioff()

makeTimestamp = lambda x: pandas.Timestamp(x)

def read_PECO_csv(datafile):
    """Read csv file from PECO into a pandas dataframe"""
    if hasattr(datafile, 'read'):
        # Read buffer directly
        df = pandas.read_csv(datafile, skiprows=4)
    else:        
        # Read in usage log (csv format, probably specific to PECO)
        df = pandas.read_csv(root+datafile+'.csv', skiprows=4)
    
    # Convert costs (drop dollar sign and convert to float)
    df['COST'] = df['COST'].str.slice(1).apply(lambda x: float(x))
    
    df = _add_convieant_cols(df)
    
    return df

def _add_convieant_cols(df):
    # Convert times
    df['ts'] = (df['DATE']+' '+df['START TIME']).apply(makeTimestamp)
    df.set_index('ts', drop=False, inplace=True)
    
    df['hr'] = df['ts'].apply(lambda x: int(x.strftime('%H')))
    
    
    # Create a few tags
    weekdayTagger = lambda x: 'Weekday' if x.weekday() else 'Weekend'
    df['Weekday'] = df['ts'].apply(weekdayTagger)
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
    
    assert len(df['UNITS'].unique()) == 1, "Energy units inconsistent"
    
    return df

def read_GB_xml(datafile):
    """Read xml file in GB format"""
    from BeautifulSoup import BeautifulStoneSoup
    
    if hasattr(datafile, 'read'):
        # Read buffer directly
        soup = BeautifulStoneSoup(datafile.read())
    else:        
        # Read in usage log (csv format, probably specific to PECO)
        with open(datafile) as f:
            soup = BeautifulStoneSoup(f.read())
    # Create data appropriate for current dataframe fromat
    data = []
    getDate = lambda x: datetime.fromtimestamp(x).strftime('%Y-%m-%d')
    getStart = lambda x: datetime.fromtimestamp(x).strftime('%H:%M')
    getEnd = lambda x, y: datetime.fromtimestamp(x+y).strftime('%H:%M')
    for r in soup.findAll('intervalreading'):
        dt = int(r.start.string)
        dur = int(r.duration.string)
        row = ['Electric usage', getDate(dt), getStart(dt), getEnd(dt, dur),
               #TYPE            DATE            START TIME  END TIME
               float(r.value.string), 'kWh', -1.0, '']
               #USAGE   UNIT  COST  NOTES
        data.append(row)

    df = pandas.DataFrame(data=data,columns=['TYPE', 'DATE', 'START TIME', 
                              'END TIME','USAGE', 'UNITS', 'COST', 'NOTES'])
    
    df = _add_convieant_cols(df)
    
    return df


def density_cloud_by_tags(df, columns, silent=False):
    """Create density cloud of data for a given tag or group of tags
    For example:
        columns='DayOfWeek' --> Plots for Mon, Tue, Wed, Thur, ...
        columns='Weekday' --> Plots of weekends vs weekday
        columns=['Season','Weekday'] 
            --> Plots of Summer, Spring, Winter, Fall Weekdays and Weekends
    """
    figures = []
    if columns == 'hr' or 'hr' in columns:
        raise ValueError("Columns cannot contain hr tag")
        
    # Create a profile for day of week
    maxY = df['USAGE'].max()
    for label, data in df.groupby(columns):    
        
        # Find mean
        mean = data.groupby('hr')['USAGE'].agg('mean')
        # Add in any missing hours
        for h in set(range(24)) - set(data['hr']):
            mean = mean.set_value(h, None)
            
    
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
        #plt.xkcd()
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
        figures.append(plt.gcf())
        if not silent:
            plt.show()
        
    return figures
        

############################################################################

# What if we paid wholesale prices at our local pnode?

def price_at_pnodes(df, pnodes):
    """ Given a green button dataframe, price that energy at PJM pnodes"""
    for pnode in pnodes:
        # Bring in PJM prices from DataMiner
        pnode_prices = pandas.read_csv(root+'pnode_data/%s.csv' % pnode)
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
    
    return df
#cols = ['COST'] + ['pnode_'+p for p in pnodes]
#df[cols].plot()
#df[cols].cumsum().plot()



#############################################################################
# Lets look at some weather correlations
def load_weather(df, weather_station):
    """Add weather tags to green button dataframe for a given station"""
    weather = pandas.read_csv(root+
        r'weather_data/%s.csv' % weather_station, na_values=['N/A'])
    weather['ts'] = weather['DateUTC'].apply(makeTimestamp)
    weather = weather.set_index('ts', drop=False)
    weather['Wind SpeedMPH'] = weather['Wind SpeedMPH'].str.replace('Calm','0')
    weather['Wind SpeedMPH'] = weather['Wind SpeedMPH'].apply(lambda x: float(x))
    
    # Handle unclean data
    weather = weather.drop(weather[weather['TemperatureF'] < -20].index)
    weather = weather.drop(weather[weather['Wind SpeedMPH'] < 0].index)
    
    
    # Resample to hourly (taking average)
    weather2 = weather.resample('h')
    
    # Grab most frequest condition for hour
    condMode = lambda x: x.value_counts().index[0]
    makeTimestampKey = lambda x: makeTimestamp(x.strftime("%d-%b-%Y %H:00"))
    weather['ts_k'] = weather['ts'].apply(makeTimestampKey)
    weather2['Conditions'] = weather.groupby('ts_k')['Conditions'].apply(condMode)
    weather = weather2
        
    
    # Add some weather related tags
    df['Temp'] = weather['TemperatureF']
    df['Wind'] = weather['Wind SpeedMPH']
    df['Conditions'] = weather['Conditions']
    # 10 deg temp categories (ie, 50-60 deg)
    tempGrads = lambda x: '%d-%d'% ((int(x/10)*10),(int(x/10)*10)+10)
    df['TempGrads'] = df['Temp'].fillna(0).apply(tempGrads)

    return df



############################################################################
# Line Chart Test
# API sandbox: https://code.google.com/apis/ajax/playground/?type=visualization#annotated_time_line
# API docs: https://developers.google.com/chart/interactive/docs/gallery/annotatedtimeline?csw=1
# DataTable docs: https://developers.google.com/chart/interactive/docs/reference?csw=1
def google_linechart(df):
    template = "        {c:[{v: 'Date(%(ts)s)'}, {v: %(USAGE)s}, {v: %(COST)s}]},\n"
    html = """
    <!--
    You are free to copy and use this sample in accordance with the terms of the
    Apache license (http://www.apache.org/licenses/LICENSE-2.0.html)
    -->
    
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
      <meta http-equiv="content-type" content="text/html; charset=utf-8" />
      <title>Google Visualization API Sample</title>
      <script type="text/javascript" src="http://www.google.com/jsapi"></script>
      <script type="text/javascript">
        google.load('visualization', '1', {packages: ['annotatedtimeline']});
        function drawVisualization() {
          var data = new google.visualization.DataTable(
          {
           cols: [{id: 'date', label: 'Date', type: 'datetime'},
                  {id: 'USAGE', label: 'Usage (kWh)', type: 'number'},
                  {id: 'COST', label: 'Cost ($)', type: 'number'}],
           rows: [
    """
    for lbl, r in df.iterrows():
        r['ts']=r['ts'].strftime('%Y,%m,%d,%H,%M,%S')
        html+= template % r.fillna('null')
    html +="""
                ]
          });
        
          var annotatedtimeline = new google.visualization.AnnotatedTimeLine(
              document.getElementById('visualization'));
          annotatedtimeline.draw(data, {'displayAnnotations': true});
        }
        
        google.setOnLoadCallback(drawVisualization);
      </script>
    </head>
    <body style="font-family: Arial;border: 0 none;">
    <div id="visualization" style="width: 800px; height: 400px;"></div>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    plt.close('all')
    
    # Load data
    datafile = r"gb.xml"
    df = read_GB_xml(datafile)
    
    # Load data
    #df = read_PECO_csv(datafile)
    
    # Add in the prices at nearby PJM pnodes
    df = price_at_pnodes(df, pnodes)
    density_cloud_by_tags(df, 'DayOfWeek')
    density_cloud_by_tags(df, 'Weekday')
    density_cloud_by_tags(df, ['Season','Weekday'])
    
    raise Exception
    
    # Add in some weather info
    df = load_weather(df, weather_station)
    density_cloud_by_tags(df, 'TempGrads')
    density_cloud_by_tags(df, 'Conditions')


