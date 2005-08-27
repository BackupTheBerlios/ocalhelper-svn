#!/usr/bin/python
"""indexClipart.py- A python script that creates an index for a clip art collection
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

# Script for creating your own local clipart index for the localocal module

import HTMLParser
from xml.parsers import expat
import itertools
import os
import md5
import shelve
import ConfigParser
from xml.dom import minidom

verbose = False

def makeIndex(rootdir, indexFile='index.dat'):
	rootdir = os.path.normpath(rootdir) # Remove the trailing slash, if any
	kwIndex = {}
	pathIndex = {}
        categoryIndex = {}

#       These lines are for generating the xml description of the category hierarchy
        xmlPaths = {}
        xmlDoc = minidom.Document()
        cat_hier = xmlDoc.createElement('category-hierarchy')
        xmlDoc.appendChild(cat_hier)
        xmlPaths[''] = cat_hier

	for dirpath, subdirs, filenames in os.walk(rootdir):
            if dirpath != rootdir:
                parentCategory, catName = os.path.split(dirpath[len(rootdir) + 1:])
                el = xmlDoc.createElement('category')
                el.setAttribute('name', catName)
                el.setAttribute('id', dirpath[len(rootdir) + 1:])
                xmlPaths[parentCategory].appendChild(el)
                xmlPaths[dirpath[len(rootdir) + 1:]] = el

		for filename in filenames:
			if not filename.endswith('.svg'):
				continue
			fullpath = os.path.join(dirpath, filename)
			relpath = fullpath[len(rootdir) + 1:]
			try:
				xml = file(fullpath).read()
				m = getMetadata(xml)
			except: # If the metadata was not parsable, skip the image
				if verbose:
					print "couldn't parse metadata for %s, skipping image" % fullpath
				continue
			contentsHash = md5.new(xml).hexdigest()
			c = (relpath, contentsHash, m.get('title', None), m.get('artist', None), tuple(m.get('keywords', None)))
			pathIndex[relpath] = c
                        category = os.path.dirname(relpath)
                        if not categoryIndex.has_key(category):
                            categoryIndex[category] = set([c])
                        else:
                            categoryIndex[category].add(c)
			for word in m.get('keywords', []):
				if kwIndex.has_key(word):
					kwIndex[word.lower()].update([c])
				else:
					kwIndex[word.lower()] = set([c])
			if verbose:
				print 'indexed', fullpath
	persist = shelve.open(indexFile)
	persist['keywords'] = kwIndex
	persist['paths'] = pathIndex
        persist['categories'] = categoryIndex
        persist['catsXML'] = xmlDoc.toprettyxml()
	if verbose:
		print '\nIndexed %i images' % len(pathIndex)

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

def updateConfig(filename, repodir, indexfile):
	"Update a clipartbrowser config file using the info being used currently for indexing"
	if verbose:
	    print 'Updating config file at %s ...' % filename
	section = 'localocal'
	c = ConfigParser.ConfigParser()
	if not c.read(filename):
	    sys.exit('Error: unable to parse configuration file at %s' % filename)
	if not c.has_section(section):
	    c.add_section(section)
	c.set(section, 'repodir', repodir)
	c.set(section, 'indexfile', indexfile)
	c.write(file(filename, 'w'))
	if verbose:
	    print 'Config file updated successfully'



helpmsg = '''indexClipart.py
USAGE: python indexClipart.py [OPTIONS] [DIR]

DIR is the root directory of the clip art dump.  Defaults to "."

Options:
	-v		Verbose output
	-f=filename	path to index file to be generated
	-h		Print this help message
	-c=configfile	Update browser config file using current indexing settings

DESCRIPTION

Create an index for a clip art repository in the format that the localocal module for the Clip Art Browser needs.
'''

if __name__ == '__main__':
	import sys
	import getopt
	opts, args = getopt.getopt(sys.argv[1:], 'chvf:')
	indexFile = 'index.dat'
	configFile = None
	for opt, value in opts:
		if opt == '-v':
			verbose = True
		elif opt == '-f':
			indexFile = value
		elif opt == '-h':
			print helpmsg
			sys.exit()
		elif opt == '-c':
		    if value:
		    	configFile = value
		    else:
			configFile = os.path.expanduser('~/.inkscape/clipartbrowser.conf')
		    

	if len(args) > 0:
		rootdir = args[0]
	else:
		rootdir = '.'

#	Make paths absolute
	indexFile = os.path.abspath(indexFile) 
	rootdir = os.path.abspath(rootdir)
	if not os.path.isdir(rootdir):
	    sys.exit('Error: repository path %s is not a directory' % rootdir)
	if configFile and not os.path.isfile(configFile):
	    sys.exit('Error: configuration file %s does not exist' % configFile)

	makeIndex(rootdir, indexFile)
	if configFile:
	    updateConfig(configFile, rootdir, indexFile)
