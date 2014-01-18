# A very simple Flask Hello World app for you to get started with...
import imp, os, sys
import traceback
from flask import Flask, request, session
from redis_session import RedisSessionInterface

app = Flask(__name__)
app.debug = True
app.session_interface = RedisSessionInterface()

root = root = os.path.dirname(os.path.realpath(__file__))+os.sep


try:
    GBA = imp.load_source('GBA', root+'..'+os.sep+'GreenButtonActuator.py')
except:
    debug_info = "<pre>"+str(traceback.format_exc())+"</pre>"

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return 'PROBLEM IMPORTING GBA:<br>'+debug_info
    
    


@app.route('/')
def hello_world():
    if 'df' in session.keys():
        msg = 'You already have a dataframe loaded.  Good!<br><pre>%s</pre>' % session['df']
        session.pop('df',None)
        return msg
    else:        
        df = GBA.read_PECO_csv('DailyElectricUsage')
        session['df'] = df
        return 'Loaded daily electric usage.'

@app.route('/raw')
def viewraw():
    return 'NotImplemented'



app.secret_key = 'v\xfc\x9d\xfb\xa2\xc7uj\x97F\xc2\xb2\x14\xa4\xaa\xef\x8e\xedz\xe4\xc0daI'

if __name__=='__main__':
    app.run()