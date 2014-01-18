import urllib2
import pandas
import time
import random

date_range = pandas.date_range('04/01/2013','01/17/2014')
root = r"D:\Projects\GreenButtonActuator\weather_data\\"


# Takes year, month, and day as paramaters
template = "http://www.wunderground.com/history/airport/KLOM/%(year)d/%(month)d/%(day)d/DailyHistory.html?req_city=Norristown&req_state=PA&req_statename=Pennsylvania&format=1"

dates = [d for d in date_range]
random.shuffle(dates)

for d in dates:
    print "Fectching %s..." % d
    u = urllib2.urlopen(template % dict(day=d.day, month=d.month, year=d.year))
    localFile = open(root+str(d)[:10]+'.csv', 'w')
    localFile.write(u.read())
    localFile.close()
    time.sleep(random.randrange(01,39)/10)


print "Joining..."

master = open(root+"_all.csv",'w')
master.write('TimeEDT,TemperatureF,Dew PointF,Humidity,Sea Level PressureIn,VisibilityMPH,Wind Direction,Wind SpeedMPH,Gust SpeedMPH,PrecipitationIn,Events,Conditions,WindDirDegrees,DateUTC\n')

for d in date_range:
    f = open(root+str(d)[:10]+'.csv', 'r')
    lines = f.readlines()
    if len(lines) <= 5:
        print "  %s had no data" % d
        continue
    lines = lines[2:]   # Cut header
    master.write(''.join(lines).replace('<br />',''))
    f.close()

master.close()

print "Done."
    

