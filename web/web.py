# A very simple Flask Hello World app for you to get started with...
import imp, os, sys
import traceback
from flask import (Flask, request, session, redirect, url_for, render_template,
                       make_response, abort)
from serverside_sessions import create_managed_session
from StringIO import StringIO
from werkzeug import secure_filename

root = os.path.dirname(os.path.realpath(__file__))+os.sep

app = Flask(__name__)
app.secret_key = 'v\xfc\x9d\xfb\xa2\xc7uj\x97F\xc2\xb2\x14\xa4\xaa\xef\x8e\xedz\xe4\xc0daI'
app.debug = True
# Server-side session handeling
app.config['SESSION_PATH'] = root+'_SESSION_DATA'+os.sep
app.session_interface = create_managed_session(app)
# File uploads
app.config['UPLOAD_FOLDER'] = root+'_UPLOADS'+os.sep
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = set(['xml'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

class DataNotLoaded(Exception):
    pass

try:
    GBA = imp.load_source('GBA', root+'..'+os.sep+'GreenButtonActuator.py')
except:
    debug_info = "<pre>"+str(traceback.format_exc())+"</pre>"

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return 'PROBLEM IMPORTING GBA:<br>'+debug_info
    # Don't let anyone else route over us
    null_func = lambda x: None
    app.route = lambda x: null_func


@app.route('/')
def hello_world():
    if 'df' in session.keys():
        msg = 'You already have a dataframe loaded.  Good!<br><pre>%s</pre>' % session['df']
        return msg+'<p><a href="/dashboard">Go to dashboard</a>'
    else:        
        return redirect(url_for('read_usage'))

@app.errorhandler(DataNotLoaded)
def gotoread_usage(exception):
    return redirect(url_for('read_usage'))
    
@app.route('/read_usage', methods=['POST','GET'])
def read_usage(excpetion=None):
    if request.method == 'POST':
        # Read in usage statistics
        f = request.files['file']
        if f and allowed_file(f.filename):
            try:
                df = GBA.read_GB_xml(f.stream)
                df = GBA.load_weather(df, 'KLOM_norristown')
            except:
                return "Unable to load data.  Bad format"
            else:
                session['df'] = df
                msg = "Loaded your data..."
        else:
            # Read in default dataset
            df = GBA.read_PECO_csv('DailyElectricUsage')
            df = GBA.load_weather(df, 'KLOM_norristown')
            session['df'] = df
            msg =  "Loaded default dataset..."
            return redirect(url_for('dashboard'))
    else:
        return """
        <h1>Green Button Analysis</h1>
        <p>If your utiltiy supports Green-Button export, upload the xml
        data using the dialog below.  </p>
        <p>Otherwise, leave box blank to 
        load a sample dataset.</p>
        <form action="" method="post" enctype="multipart/form-data" >
        <input type=file name=file />
        <p><input type='submit' /></p>
        <p><input type='submit' value="I have no data, use default" /></p>
        </form>
        """

@app.route('/drop')
def drop_dataframe():
    for k in session.keys():
        session.drop(k)
    return redirect(url_for('read_usage'))


####################################################################
# Dashboard
from wtforms import Form, TextField, SelectMultipleField, validators

class DashboardForm(Form):
    idx = TextField("Slice (Leave blank unless you know what you're doing)")
    tags = SelectMultipleField('Tags', choices=[
                ('--T','-------TIME TAGS-------'),
                ('Weekday',     'Weekday vs Weekend'),
                ('DayOfWeek',   'Day of Week (ie, Mon, Tue, etc...)'),
                ('Season',      'Season (ie, Spring, Fall, etc...)'),
                ('Month',       'Month (ie, Jan, Feb, etc...)'),
                ('--W','-------WEATHER-------'),
                ('TempGrads',    'Tempearture in 10 deg increments'),
                #('Wind',         'Wind Speed'),
                ('Conditions',    'Condition (Clear, Cloudy, etc...)'),
            ],
            validators=[validators.NoneOf(['--T','--P'],
                                          "Don't select headers")]
            
            )
    pnodes = SelectMultipleField('Alternate Pricings', choices=[
                ('--P','-------PJM PNODES-------'),
                ('BARBADOES35 KV  ABU2',    'BARBADOES35 KV  ABU2'),
                ('BETZWOOD230 KV  LOAD1',   'BETZWOOD230 KV  LOAD1'),
                ('PECO',                    'PECO (Zone)'),
                ('_ENERGY_ONLY',            'System Energy Price'),
            ],
            validators=[validators.NoneOf(['--T','--P'],
                                          "Don't select headers")]
            
            )
@app.route('/dashboard', methods=['POST','GET'])
def dashboard():
    form = DashboardForm(request.form)
    if request.method == 'POST' and form.validate():
        session['tags'] = form.tags.data
        session['pnodes'] = form.pnodes.data
        session['idx'] = form.idx.data
        return redirect(url_for('report'))
    return render_template('dashboard.html', form=form)

@app.route('/report')
def report(): 
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    assert_data()
    df = session['df']
    
    if 'idx' in session.keys() and len(session['idx'])>0:
        idx = session['idx']
        if idx.find(':') > -1:
            lidx, ridx = idx.split(':')
            df = df[lidx:ridx]
        else:
            df = df[idx]
    
    figures = []
    if 'tags' in session.keys() and len(session['tags'])>0:
        figures += GBA.density_cloud_by_tags(df, session['tags'], 
                                            silent=True)
                                            
    if 'pnodes' in session.keys() and len(session['pnodes'])>0:
        import matplotlib.pylab as plt
        plt.ioff()
        
        pnodes = session['pnodes']
        df = GBA.price_at_pnodes(df, pnodes)
        cols = ['COST',] + ['pnode_'+p for p in pnodes]
        figures.append(df[cols].plot().figure)        
        figures.append(df[cols].cumsum().plot().figure)
        
    session.drop('tags')
    s = '<h1>Figures</h1>'
    figures_rendered = []
    for n, fig in enumerate(figures):
        s+='<img src="plt/%d.png" /><br />' % n
        canvas=FigureCanvas(fig)
        png_output = StringIO()
        canvas.print_png(png_output)
        figures_rendered.append(png_output.getvalue())
    session['figures'] = figures_rendered
    s += '<p><a href="/dashboard">Back to dashboard</a></p><br /><br />'
    return s
        

@app.route("/plt/<int:fig_id>.png")
def render_figure(fig_id): 
    
     
    #    fig=Figure()
    #    ax=fig.add_subplot(111)
    #    x=[]
    #    y=[]
    #    now=datetime.datetime.now()
    #    delta=datetime.timedelta(days=1)
    #    for i in range(10):
    #        x.append(now)
    #        now+=delta
    #        y.append(random.randint(0, 1000))
    #    ax.plot_date(x, y, '-')
    #    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    #    fig.autofmt_xdate()
     
    if 'figures' not in session.keys():
        abort(404)
    try:
        fig = session['figures'][fig_id]
    except IndexError:
        abort(404)

    response=make_response(fig)
    response.headers['Content-Type'] = 'image/png'
    return response
     

@app.route('/raw')
def viewraw():
    assert_data()
    return GBA.google_linechart(session['df'])

@app.route('/css/bootstrap-responsive.css')
def serveBootstrapResponsivecss():
    f=open("templates/css/bootstrap-responsive.css")
    return f.read()
    
@app.route('/css/bootstrap.css')
def serveBootstrapcss():
    f=open("templates/css/bootstrap.css")
    return f.read()

@app.route('/css/styles.css')
def serveStyles():
    f=open("templates/css/styles.css")
    return f.read()

@app.route('/js/bootstrap.js')
def serveJSBootstrap():
    f=open("templates/js/bootstrap.js")
    return f.read()

@app.route('/js/jquery-1.8.2.js')
def serveJquery():
    f=open("templates/js/jquery-1.8.2.js")
    return f.read()

@app.route('/js/script.js')
def serveScript():
    f=open("templates/js/script.js")
    return f.read()



def assert_data():
    if 'df' not in session.keys():
        raise DataNotLoaded

if __name__=='__main__':
    app.run()