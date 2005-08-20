import urllib
import HTMLParser
from xml.parsers import expat
import itertools

class API:
	title = 'OCAL'
	"An implementation of the clip art navigator repo api for ocal"

	def __init__(self, config):
		if config.has_option('ocal', 'searchurl'):
			self.url = config.get('ocal', 'searchurl')
		else:
			self.url = 'http//openclipart.org/cgi-bin/keyword_search.cgi'

		if config.has_option('ocal', 'maxresults'):
			self.maxresults = config.get('ocal', 'maxresults')
		else:
			self.maxresults = 10

	def query(self, q):
		"Given a query, return a list of (path, None) duples"
		data = urllib.urlencode({'keywords':q, 'howmany':self.maxresults})
		resultsPage = urllib.urlopen(self.url, data)
		p = _Parser()
		p.resultHrefs = []
		p.feed(resultsPage.read())
		return zip(p.resultHrefs, itertools.repeat(None))

	def getImage(self, path):
		"Given an image path return the svg xml contents"
		xml = file(urllib.urlretrieve(path)[0]).read()
		return (xml, None)

def getMetadata(svg):
    metadata = {}
    parser = expat.ParserCreate(namespace_separator=':')
    m = Metadata()
    parser.StartElementHandler = m.metadata_startElement
    parser.EndElementHandler = m.metadata_endElement
    parser.CharacterDataHandler = m.metadata_charData
    parser.Parse(svg)
    metadata['title'] = getattr(m, 'title', None)
    metadata['keywords'] = getattr(m, 'keywords', [])
    return metadata

class Metadata:
    def __init__(self):
        self.path = []
        self.result = None
        self.keywords = [] # This will be implemented later
        
    def metadata_startElement(self, name, attrs):
        self.path.append(name)

    def metadata_endElement(self, name):
        self.path.pop()

    def metadata_charData(self, data):
        if self.path[-1] == 'http://purl.org/dc/elements/1.1/:title' and self.path[-2] == 'http://web.resource.org/cc/:Work':
            self.title = data
        if self.path[-1] == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#:li' and self.path[-3] == 'http://purl.org/dc/elements/1.1/:subject':
            if getattr(self, 'keywords', None) is None:
	        self.keywords = [data]
            else:
	        self.keywords.append(data)
        
class _Parser(HTMLParser.HTMLParser):
        
    resultHrefs = []
    flag = False
    def handle_starttag(self, tag, attrs):
        if tag == 'div' and ('class', 'results') in attrs:
            self.flag = True

        if not self.flag:
            return

        if tag == 'a':
            for key, value in attrs:
                if key == 'href' and value.endswith('.svg'):
                    self.resultHrefs.append(value)

    def handle_endtag(self, tag):
        if tag == 'div':
            self.flag = False
