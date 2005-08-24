#!/usr/bin/python
"""localocal.py- A module for local clip art repositories for the Clip Art Navigator
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

class API:
	title = 'localocal'
	def __init__(self, config):
		self.repodir = config.get('localocal', 'repodir')
		indexFile = os.path.join(self.repodir, 'index.dat')
		index = shelve.open(indexFile, writeback=False)
		self.kwIndex = index['keywords']
		self.pathIndex = index['paths']

	def query(self, q):
		keywords = [word.lower().replace(' ', '') for word in shlex.split(q)]
		if len(keywords) is 0:
			return []
		results = self.kwIndex.get(keywords[0], set())
		for word in keywords:
			# searching for "cat dog" means "cat AND dog"... i.e. intersection
			results = results.intersection(self.kwIndex.get(word, set()))
		return [(img[0], img[1]) for img in results]

	def getImage(self, ID):
		# The second element should be a metadata dict, but we'll skip that for now
		img = self.pathIndex[ID]
		m = {'title':img[2], 'artist':img[3], 'keywords':img[4]}
		return (file(os.path.join(self.repodir, ID)).read(), m)
