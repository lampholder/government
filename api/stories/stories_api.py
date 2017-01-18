import sys
sys.stdout = sys.stderr

import re
import atexit
import json
import cherrypy
import requests
import MySQLdb

from collections import OrderedDict

import ConfigParser

from cherrypy import _cperror

cherrypy.config.update({'environment': 'embedded'})
cherrypy.config['log.error_file'] = '/home/gov/var/log/cherrypy.log'

if cherrypy.__version__.startswith('3.0') and cherrypy.engine.state == 0:
  cherrypy.engine.start(blocking=False)
  atexit.register(cherrypy.engine.stop)

config = ConfigParser.ConfigParser()
config.read(['/home/gov/.picolo.cfg'])
#cabinet_url = config.get('parliament', 'cabinet')
#opposition_url = config.get('parliament', 'opposition')

class Root(object):

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def index(self, days=1):
    db = MySQLdb.connect(host="localhost", user="root", passwd="passworm", db="gov", use_unicode=True)
    cur = db.cursor()
    cur.execute("""select mp, title, source, url, timestamp from articles where datediff(curdate(), date) <= %s;""" , (days));
    mps = {}
    for row in cur.fetchall():
      (mp, title, source, url, date) = row
      if mp not in mps:
        mps[mp] = []
      mps[mp].append((title, source, url, date.isoformat()))#date.strftime('%Y-%M-%DT%H:%m:%sZ'))
    db.close()
    return mps

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def count(self, days=1):
    db = MySQLdb.connect(host="localhost", user="root", passwd="passworm", db="gov", use_unicode=True)
    stories = {}
    cabinet = requests.get('http://gov.3cu.eu/api/cabinet/v1/').json()['government']['cabinet']
    for minister in cabinet:
      stories[minister['name']] = 0;

    cur = db.cursor()
    cur.execute("""select mp, count(*) from articles where datediff(curdate(), date) <= %s group by mp;""" , (days));
    for row in cur.fetchall():
      (mp, story_count) = row
      stories[mp] = story_count
    db.close()
    return OrderedDict(sorted(stories.iteritems(), key=lambda (k,v): v, reverse=True))

  def handle_error():
    cherrypy.response.status = 500
    cherrypy.response.body = ["<html><body>Sorry, an error occured %s</body></html>" % _cperror.format_exc()]

  _cp_config = {'request.error_response': handle_error}

application = cherrypy.Application(Root(), script_name=None, config=None)
