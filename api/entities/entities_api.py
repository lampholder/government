import sys
sys.stdout = sys.stderr

import re
import atexit
import json
import cherrypy
import requests

from BeautifulSoup import BeautifulSoup
from collections import OrderedDict

import ConfigParser

from cherrypy import _cperror

cherrypy.config.update({'environment': 'embedded'})

if cherrypy.__version__.startswith('3.0') and cherrypy.engine.state == 0:
  cherrypy.engine.start(blocking=False)
  atexit.register(cherrypy.engine.stop)

config = ConfigParser.ConfigParser()
config.read(['/home/gov/.picolo.cfg'])
cabinet_url = config.get('parliament', 'cabinet')
opposition_url = config.get('parliament', 'opposition')

class Root(object):

  @cherrypy.expose
  @cherrypy.tools.json_out()
  def index(self):
    #cabinet = self._get_cabinet(cabinet_url)
    #opposition = self._get_cabinet(opposition_url)
    d = OrderedDict()
    d['government'] = self._get_cabinet(cabinet_url)
    d['opposition'] = self._get_cabinet(opposition_url)
    return d
    #return {'government': cabinet, 'opposition': opposition}

  def _get_cabinet(self, source):
    html = requests.get(source)
    soup = BeautifulSoup(html.text, convertEntities=BeautifulSoup.HTML_ENTITIES)
    rows = map(lambda x: x, soup.findAll("table")[0].findAll("td"))

    also_attend_dividers = [rows.index(x) for x in rows if x.find('h3') != None]
    divider = also_attend_dividers[0]
    rows = [x for x in rows if x.find('h3') == None]
    cabinet = rows[0:divider]
    extended_cabinet = rows[divider:]
    d = OrderedDict()
    d['cabinet'] = list(self._process(cabinet))
    d['extended_cabinet'] = list(self._process(extended_cabinet))
    return d
    #return {'cabinet': list(self._process(cabinet)),
    #        'extended_cabinet': list(self._process(extended_cabinet))}

    #sub_lists = [rows[i:j] for i, j in zip([0]+also_attend_dividers, also_attend_dividers+[None])]
    #identified_lists = {'cabinet': list(self._process(sub_lists[0]))}
    #for a in range(len(also_attend_dividers)):
    #  sub_lists[a+1] = sub_lists[a+1][1:] 
    #  identified_lists[rows[also_attend_dividers[a]].text.lower().replace(' ', '_')] = list(self._process(sub_lists[a + 1]))
    #return identified_lists

  """Aw fuck me this is an ugly method"""
  def _process(self, input_list):
    party_long_names = {'Lab': 'Labour', 'Con': 'Conservative', 'LD': 'Liberal Democrat'}
    for i in range(0, len(input_list), 2):
      val = input_list[i:i+2]
      if len(val) == 2:
        partyMatch = re.match(r'(.*?) \((.*?)\)', val[1].text)
        if partyMatch:
          full_name = partyMatch.group(1)
          party = partyMatch.group(2)
          if party in party_long_names:
            party = party_long_names[party]
        else:
          full_name = val[1].text
          party = 'NOT FOUND'
        junk = re.compile(r'\b(MP|Rt Hon|CBE|The|QC|Dr|Mr|Mrs|Miss|Ms)\b', re.I)
        short_name = junk.sub("", full_name).strip(" .")
        d = OrderedDict()
        d['position'] = val[0].text
        d['name'] = short_name
        d['full_name'] = full_name
        d['party'] = party
        d['url'] = val[1].find("a", href=True)['href']
        yield d
        #yield {'position': val[0].text, 'full_name': full_name, 'name': short_name, 'party': party, 'url': val[1].find("a", href=True)['href']}

  def handle_error():
    cherrypy.response.status = 500
    cherrypy.response.body = ["<html><body>Sorry, an error occured %s</body></html>" % _cperror.format_exc()]

  _cp_config = {'request.error_response': handle_error}

application = cherrypy.Application(Root(), script_name=None, config=None)
