#!/usr/bin/python
import re
import urllib
import HTMLParser
import tempfile
from xml.dom import minidom
from xml.parsers import expat
import gtk
import gtk.glade
import gobject
import tempfile
import gtk.gdk
import tempfile
import sys
import os

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
            self.result = data
        
def getMetadata(svg):
    parser = expat.ParserCreate(namespace_separator=':')
    m = Metadata()
    parser.StartElementHandler = m.metadata_startElement
    parser.EndElementHandler = m.metadata_endElement
    parser.CharacterDataHandler = m.metadata_charData
    parser.Parse(svg)
    return m.result

class Parser(HTMLParser.HTMLParser):
        
    resultHrefs = []
    resultImgs = []
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

	elif tag == 'img':
	    for key, value in attrs:
		if key == 'src':
		    self.resultImgs.append(value)

    def handle_endtag(self, tag):
        if tag == 'div':
            self.flag = False
     
def search(query):
    'Given a keyword query, returns a list of (source url, preview image url) duples'
    data = urllib.urlencode({'keywords':query, 'howmany':10})
    url = 'http://openclipart.org/cgi-bin/keyword_search.cgi'
    resultsPage = urllib.urlopen(url, data)
    p = Parser()
    p.resultHrefs, p.resultImgs = [], []
    p.feed(resultsPage.read())
    return zip(p.resultHrefs, p.resultImgs)


def insertPic(doc, url):
    "Given an svg document and the url of another svg document, insert the second into the first and return the first"

    newPic = minidom.parseString(urllib.urlopen(url).read()).documentElement
    
    # If invoked from the commandline (not inkscape), just return the fetched clipart
    if doc is None:
        return newPic

    # Otherwise, insert the clipart into the document, and return the altered document
    svgElem = minidom.parseString(doc).documentElement
    try:
        newPic.removeAttribute('height')
    except:
        pass
    newPic.setAttribute('width', '50%')

    svgElem.appendChild(newPic)

    return svgElem
        
class GUI:
	def __init__(self, doc=None):
            "Optional doc arg is the filename that the original svg doc, if any, can be read from"

            # Store the original svg doc, if any
            self.doc = (doc and doc.read()) or None

            # Load the libglade gui description (which should be stored in the same dir as this script)
            extDir = os.path.abspath(os.path.dirname((sys.argv[0])))
            self.xml = gtk.glade.XML(os.path.join(extDir, "ocal.glade"))

            self.mainwindow = self.xml.get_widget('mainwindow')
            self.searchInput = self.xml.get_widget('searchInput')

            self.statusbar = self.xml.get_widget('statusbar')
            self.context = self.statusbar.get_context_id('main')

            # Setup the datastructure for icons returned from searches
            self.iconview = self.xml.get_widget('iconview')
            self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, str) # png preview data, svg href, title
            self.iconview.set_model(self.store)
            self.iconview.set_pixbuf_column(0)
            self.iconview.set_text_column(2)
	    self.xml.signal_autoconnect(self)

	def on_mainwindow_delete_event(self, widget, event):
            "If the gui is closed without chosing clipart, return the original doc to keep inkscape from crashing"
            
            print self.doc
            return False

	def on_mainwindow_destroy(self, widget):
		gtk.main_quit()

	def main(self):
		gtk.main()

	def on_searchInput_activate(self, widget):

		self.store.clear()
		results = search(self.searchInput.get_text())
		for srcHref, previewHref in results:

			previewFile, foo = urllib.urlretrieve(previewHref)

			newPixbuf = gtk.gdk.pixbuf_new_from_file_at_size(previewFile, 60, 60)
			self.store.append((newPixbuf, srcHref, getMetadata(urllib.urlopen(srcHref).read())))
		self.statusbar.push(self.context, '%i images found' % len(self.store))

	def on_iconview_item_activated(self, widget, data):
		href = self.store[data[0]][1]
		output = insertPic(self.doc, href).toxml()
		file('output.svg', 'w').write(output)
		print output
		gtk.main_quit()
	

if __name__ == '__main__':

        
        if len(sys.argv ) > 1:
            inputDoc = file(sys.argv[-1])
        else:
            inputDoc = None
	
	g = GUI(inputDoc)
	g.main()
