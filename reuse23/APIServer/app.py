import os.path

from flask import Flask, render_template, request, jsonify, send_file
from flask_restx import Api, Resource, reqparse
from dateutil.parser import parse
import psycopg2, json, fnmatch, math

configs = ['int', 'jit', 'nok', 'nokfold','noisel','nomr']
suites = ['ostrich', 'libsodium', 'polybench']
nightlyRunID = 'NIGHTLY_RUN'  # Data is tagged with this in the database to show only nightly run results on UI

app = Flask(__name__)

with open('config.json', 'r') as config_file:
    config_data = json.load(config_file)
    db = config_data['db']
    user = config_data['user']
    pwd = config_data['pwd']

@app.after_request
def set_cors(response):
   response.headers.add("Access-Control-Allow-Origin", "*")
   return response

# landing page and generate main graph with jsc default on subgraph
@app.route('/', methods=['GET'])
def index():
   return render_template('index.html', engine="jsc")

# creates the subgraph on the landing page
@app.route('/total-time/<string:engine>')
def home(engine):
   return render_template('index.html', engine=engine)

# about page
@app.route('/about')
def about():
   return render_template('about.html')

# engines and configs page
@app.route('/engine-config-details')
def eng_config_details():
   return render_template('engine-config-details.html')

# research overview page
@app.route('/research-overview')
def methodology():
   return render_template('research-overview.html')

@app.route('/full-data')
def fullData():
   return render_template('full-data.html')

@app.route('/tester')
def tester():
   return render_template('testgraph5.html')

api = Api(app) # initialize AFTER @app.route('/') to show landing page

# total_time metric
# TODO change table to correct one to collect data
@api.route('/get_all_execution')
class getExecution(Resource):
   def get(self):
      results = []
      conn = psycopg2.connect(database=db,user=user,password=pwd)
      cur = conn.cursor()
      cur.execute("SELECT DISTINCT engine FROM summary") 
      engines = cur.fetchall()
      for engine in engines:
         if engine[0] == 'wavm': continue # wavm excluded
         cur.execute("SELECT DISTINCT exp_date FROM summary WHERE engine = %s", (engine[0],))
         exp_dates = cur.fetchall()
         for date in exp_dates:
            cur.execute("SELECT avg FROM summary WHERE engine = %s AND exp_date = %s AND metric_type = %s", (engine[0], date[0],"total_time"))
            data = cur.fetchall()
            avgs = [row[0] for row in data]
            geomean = round(math.sqrt(sum(avgs)), 6)
            results.append({'experiment_date': str(date[0]),'engine': engine[0], 'total_time': geomean})
      cur.close()
      conn.close()
      return results

# data for the engine graph displaying geomean of each suite
@api.route('/get_suites/<string:engine>')
class getSuites(Resource):
   def get(self, engine):
      results = []
      conn = psycopg2.connect(database=db,user=user,password=pwd)
      cur = conn.cursor()
      cur.execute("SELECT DISTINCT exp_date FROM summary WHERE engine = %s", (engine,))
      exp_dates = cur.fetchall()
      for suite in suites:
         for date in exp_dates:
            cur.execute("SELECT avg , percentile_5, percentile_95 FROM summary WHERE engine = %s and exp_date = %s and benchmark_suite = %s", (engine, date[0], suite))
            data = cur.fetchall()
            values = [row[0] for row in data]
            pct5 = [row[1] for row in data]
            pct95 = [row[2] for row in data]
            geomean = round(math.sqrt(sum(values)), 6)
            geomean_pct5 = round(math.sqrt(sum(pct5)), 6)
            geomean_pct95 = round(math.sqrt(sum(pct95)), 6)
            results.append({'experiment_date': str(date[0]), 'suite': suite, 'total_time': geomean,'pct5': geomean_pct5, 'pct95': geomean_pct95})
      cur.close()
      conn.close()
      return results

# calculates geomean for each suite
@api.route('/calculate_geomean/<string:suite>')
class geomeanCalc(Resource):
   def get(self, suite):
      results = []
      conn = psycopg2.connect(database=db,user=user,password=pwd)
      cur = conn.cursor()
      for config in configs:
         cur.execute("SELECT avg FROM summary WHERE benchmark_suite = %s AND config = %s", (suite, config))
         data = cur.fetchall()
         values = [avg[0] for avg in data]
         geomean = round(math.sqrt(sum(values)), 6)
         results.append({'config': config, 'geomean': geomean})
      cur.close()
      conn.close()
      return results

'''
# maybe needed in the future: calculates geomeans from a given experiment, grouped by suites and returns a json format
@api.route('/calculate_geomean/<string:experiment>')
class geomeanCalc(Resource):
   def get(self, experiment):
      results = []
      conn = psycopg2.connect(database=db,user=user,password=pwd)
      cur = conn.cursor()
      data_table = ""
      if experiment == "speedup":
         data_table = 'testsummary1'
      else: # experiment == 'execution'
         data_table = 'testsummary2'
      if data_table != "":
         for config in configs: # what configs for execution?? currently configs for speedup
            cur.execute("SELECT avg FROM " + data_table)
            data = cur.fetchall()
            values = [avg[0] for avg in data]
            geomean = round(math.sqrt(sum(values)), 6)
            results.append({'suites': , 'config': config, 'geomean': geomean})
      else:
         return "Provide a different experiment."
'''
if __name__ == "__main__":
   app.run(host='grammont.lan.local.cmu.edu',port=6363, debug=True)
