#!/usr/bin/python
"""localocal.py- A module for local clip art repositories for the Clip Art Browser
Copyright (C) 2005 Greg Steffensen, greg.steffensen@gmail.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import shelve
import os
import shlex
from xml.dom import minidom
from xml.parsers import expat
import md5


class API:
    title = 'Local Clip Art'
    def __init__(self, config):
        self.config = config
        self.repodir = config.get('localocal', 'repodir')
        indexFile = config.get('localocal', 'indexfile')
        try:
            index = shelve.open(indexFile, writeback=False)
            self.kwIndex = index['keywords']
        except KeyError:
            foo = self.__indexGTK()
            if not foo:
                raise Exception, "No clip art directory selected"
            repodir, indexfile = foo
            self.__updateConfig(os.path.expanduser('~/.clipartbrowser/clipartbrowser.conf'), repodir, indexfile)
            index = shelve.open(indexFile, writeback=False)
            self.kwIndex = index['keywords']
        self.pathIndex = index['paths']
        self.catIndex = index['categories']
        self.catsXML = index['catsXML']
        self.actions = [('Index local clip art', self.indexGTK)]
            

    def __updateConfig(self, configFile, repodir, indexfile):
        "Update the configuration file with a (possibly) new repository directory and index file path"
        import ConfigParser
        c = ConfigParser.ConfigParser()
        if not c.has_section('localocal'):
            c.add_section('localocal')
        c.set('localocal', 'repodir', os.path.abspath(repodir))
        c.set('localocal', 'indexfile', os.path.abspath(indexfile))
        c.write(file(configFile, 'w'))

        self.config.set('localocal', 'repodir', os.path.abspath(repodir))
        self.config.set('localocal', 'indexfile', os.path.abspath(indexfile))

    def indexGTK(self, widget, configPath):
        foo = self.__indexGTK()
        if not foo:
            return
        repodir, indexfile = foo
        self.__updateConfig(configPath, repodir, indexfile)
        dialog = gtk.MessageDialog(message_format='Your clip art was indexed successfully.  The Clip Art Browser must now be restarted.  Click OK to close the Clip Art Browser.', buttons=gtk.BUTTONS_OK)
        dialog.run()
        gtk.main_quit()
        sys.exit()

    def __indexGTK(self):
        "Provide a GTK interface to indexing local clip art and updating the config file"

        global gtk
        import gtk
        import gtk.glade
        xml = gtk.glade.XML('modules/localocal.glade')
        chooseDialog = xml.get_widget('indexchoosedialog')
        repodirButton = xml.get_widget('dirchoosebutton')
        response = chooseDialog.run()
        repodir = repodirButton.get_filename()
        chooseDialog.destroy()
        if response == gtk.RESPONSE_OK:
            print 'repodir chosen:', repodir
        else:
            return
        waitDialog = xml.get_widget('indexwaitdialog')
        waitDialog.connect('delete-event', lambda a, b: True)
        progressbar = xml.get_widget('progressbar')
        def startDir(dirpath):
            progressbar.set_text('Indexing %s...' % dirpath)
            while gtk.events_pending():
                gtk.main_iteration()
        interface = GTKInterface()
        interface.startDir = startDir
        i = Indexer(interface)
        waitDialog.show()
        while gtk.events_pending():
            gtk.main_iteration()
        indexfile = os.path.abspath('modules/index.dat')
        i.index(repodir, indexfile)
        waitDialog.destroy()
        return (repodir, indexfile)


    def query(self, q):
        "Query using some custom query string format"
        queryTerms = [word.lower().replace(' ', '') for word in shlex.split(q)]
        if len(queryTerms) is 0:
            return []
        results = None
        
        for term in queryTerms:
            results = self.__processTerm(term, results)
        return [(img[0], img[1]) for img in results]

    def __processTerm(self, term, results):
        "Given a query term and a set of results retrieved so far, return the results with the new term factored in"
        if term.startswith('category:'):
            r = self.catIndex.get(term[len('category:'):], set()) 
        else:
            r = self.kwIndex.get(term, set())
        if results is None: # If this is the first query term in a list
            return r
        return results.intersection(r)

    def getImage(self, ID):
        # The second element should be a metadata dict, but we'll skip that for now
        img = self.pathIndex[ID]
        m = {'title':img[2], 'artist':img[3], 'keywords':img[4]}
        return (file(os.path.join(self.repodir, ID)).read(), m)

# Code for the indexer

class Indexer:

    def __init__(self, interface=None):
        self.interface = interface

    def index(self, rootdir, indexFile=None):
        "Provide a gtk interface for indexing clipart... intended to be used by the clip art browser only"
        self.rootdir = os.path.normpath(rootdir) # remove the trailing slash, if any
        if indexFile is None:
            indexFile = os.path.join(rootdir, 'index.dat')
        self.indexFile = indexFile

        self.kwIndex = {}
        self.pathIndex = {}
        self.categoryIndex = {}

#       Setup the xml object that will be used to generate the xml category hierarchy
        self.xmlPaths = {}
        self.xmlDoc = minidom.Document()
        self.cat_hier = self.xmlDoc.createElement('category-hierarchy')
        self.xmlDoc.appendChild(self.cat_hier)
        self.xmlPaths[''] = self.cat_hier

        for dirpath, subdirs, filenames in os.walk(rootdir):
            if dirpath != rootdir:
                self.__processDir(dirpath) # add the dir to the xml hierarchy
                for filename in filenames:
                    xml = file(os.path.join(dirpath, filename))
                    self.__processFile(dirpath, filename)
        self.__saveIndex()

    def __processDir(self, dirpath):
#       The following code adds the directory to the xml category hierarchy
#       Since the root element gets a "category-hierarchy" element (already created),
#       not a "category" element, we skip this code for the root dir

#       A hook to update the interface
        if hasattr(self.interface, 'startDir'):
            self.interface.startDir(dirpath)

        relativeDir = dirpath[len(self.rootdir) + 1:] # the relative path to the dir within the repository
        parentCategory, catname = os.path.split(relativeDir)
        el = self.xmlDoc.createElement('category')
        el.setAttribute('name', catname)
        el.setAttribute('id', relativeDir)
        self.xmlPaths[parentCategory].appendChild(el)
        self.xmlPaths[relativeDir] = el
        self.categoryIndex[relativeDir] = set()

    def __processFile(self, dirpath, filename):
        if not filename.endswith('.svg'): # we only index svg files (for now...)
            return
        fullpath = os.path.join(dirpath, filename)

#       A hook to update the interface
        if hasattr(self.interface, 'startFile'):
            self.interface.startFile(fullpath)

        relpath = fullpath[len(self.rootdir) + 1:]
        try:
            xml = file(fullpath).read()
            m = getMetadata(xml)
        except: # If the metadata was not parsable, skip the image
            return
        contentsHash = md5.new(xml).hexdigest()
        c = (relpath, contentsHash, m.get('title', None), m.get('artist', None), tuple(m.get('keywords', [])))
        self.pathIndex[relpath] = c
        category = os.path.dirname(relpath)
        self.categoryIndex[category].add(c)
        for word in m.get('keywords', []):
            if self.kwIndex.has_key(word):
                self.kwIndex[word.lower()].update([c])
            else:
                self.kwIndex[word.lower()] = set([c])
                
    def __saveIndex(self):
        print 'saving index'
        persist = shelve.open(self.indexFile)
        print 'saving keywords'
        persist['keywords'] = self.kwIndex
        print 'saving paths'
        persist['paths'] = self.pathIndex
        print 'saving categories'
        persist['categories'] = self.categoryIndex
        print 'saving category xml'
        persist['catsXML'] = self.xmlDoc.toprettyxml()
        print 'index saved'


class _Metadata:

	svgNS = 'http://www.w3.org/2000/svg'
	dcNS = 'http://purl.org/dc/elements/1.1/'
	ccNS = 'http://web.resource.org/cc/'
	rdfNS = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'

	def __init__(self):
		self.path = []
		self.result = None
		self.keywords = [] # This will be implemented later
        
	def metadata_startElement(self, name, attrs):
		self.path.append(name)

	def metadata_endElement(self, name):
		self.path.pop()

	def metadata_charData(self, data):

		# Get title
 		if self.path[-1] == self.dcNS + ':title' and self.path[-2] == self.ccNS + ':Work':
			self.title = data

		# Get artist
		if self.path[-1] == self.dcNS + ':title' and self.path[-3] == self.dcNS + ':creator':
			self.artist  = data

		# Get keywords
		if self.path[-1] == self.rdfNS + ':li' and self.path[-3] == self.dcNS + ':subject':
			if getattr(self, 'keywords', None) is None:
				self.keywords = [data]
			else:
				self.keywords.append(data)
        
def getMetadata(svg):
	"Given the xml contents of an svg image, return a dict of its main metadata"
	metadata = {}
	parser = expat.ParserCreate(namespace_separator=':')
	m = _Metadata()
	parser.StartElementHandler = m.metadata_startElement
	parser.EndElementHandler = m.metadata_endElement
	parser.CharacterDataHandler = m.metadata_charData
	parser.Parse(svg)
	metadata['title'] = getattr(m, 'title', None)
	metadata['artist'] = getattr(m, 'artist', None)
	metadata['keywords'] = getattr(m, 'keywords', [])
	return metadata



class GTKInterface:
    pass

