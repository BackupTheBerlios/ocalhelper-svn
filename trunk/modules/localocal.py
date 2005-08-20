#!/usr/bin/python

import shelve
import os
import shlex

class API:
	title = 'localocal'
	def __init__(self, config):
		self.repodir = config.get('localocal', 'repodir')
		indexFile = os.path.join(self.repodir, 'index.dat')
		index = shelve.open(indexFile)
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
