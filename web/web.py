# A very simple Flask Hello World app for you to get started with...
import imp, os, sys
import traceback
from flask import Flask, request, session

root = root = os.path.dirname(os.path.realpath(__file__))+os.sep
#GBA = imp.load_source('GBA', root+'..\GreenButtonActuator.py')

app = Flask(__name__)
app.debug = True

@app.route('/')
def hello_world():
    return 'Hello from Flask!<br>'

@app.route('/raw')
def viewraw():
    #return 'wtf'
    try:
        GBA = imp.load_source('GBA', root+'..'+os.sep+'GreenButtonActuator.py')
        return GBA.html
    except:
        return "ERROR:<pre>"+str(traceback.format_exc())+'</pre><br>'+root


if __name__=='__main__':
    app.run()