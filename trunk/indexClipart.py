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

def makeIndex(rootdir, indexFile='index.dat', verbose=False):
	rootdir = os.path.normpath(rootdir) # Remove the trailing slash, if any
	kwIndex = {}
	pathIndex = {}
	for dirpath, subdirs, filenames in os.walk(rootdir):
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
			for word in m.get('keywords', []):
				if kwIndex.has_key(word):
					kwIndex[word].update([c])
				else:
					kwIndex[word] = set([c])
			if verbose:
				print 'indexed', fullpath
	persist = shelve.open(indexFile)
	persist['keywords'] = kwIndex
	persist['paths'] = pathIndex
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

helpmsg = '''indexClipart.py
USAGE: python indexClipart.py [OPTIONS] [DIR]

DIR is the root directory of the clip art dump.  Defaults to "."

Options:
	-v		Verbose output
	-f=filename	path to index file to be generated

DESCRIPTION

Create an index for a clip art repository in the format that the localocal module for the Clip Art Browser needs.
'''

if __name__ == '__main__':
	import sys
	import getopt
	opts, args = getopt.getopt(sys.argv[1:], 'hvf:')
	verbose = False
	indexFile = 'index.dat'
	for opt, value in opts:
		if opt == '-v':
			verbose = True
		if opt == '-f':
			indexFile = value
		if opt == '-h':
			print helpmsg
			sys.exit()

	if len(args) > 0:
		rootdir = args[0]
	else:
		rootdir = '.'
	makeIndex(rootdir, indexFile, verbose)
