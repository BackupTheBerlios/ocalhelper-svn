#!/usr/bin/python

from pysqlite2 import dbapi2 as sqlite
import os
import libxml2
import md5

class API:
	"An api object for a local ocal repository"

	title = 'localocal'

	def __init__(self, config=None):
		"Initialize a new api object, with a config dict"

		self.dbfile = config['dbfile']
		self.repoDir = config['repodir']

		self.initMessages = [] # Messages about initialization
		

#		Check that an index db already exists and is a proper schema 
		try:	
			assert os.access(self.dbfile, os.R_OK)
			self.con = sqlite.connect(self.dbfile)
			cur = self.con.cursor()
			cur.execute('SELECT id, path, title, artist, hash FROM images LIMIT 1')
#			Is it ok to have no images in your local repository? Hmmm....
#			assert cur.fetchone[0] > 0

			cur.execute('SELECT image_id, word FROM keywords LIMIT 1')
		except:
			raise

#		Should we check whether the index matches the repo state?
		verify = config['verifyindex'].lower()
		if (verify == 'true' or verify == '1' or verify == 'on' or verify == 'yes'):
			if not self.__checkIndex():
				self.initMessages.append('''The index for the local clipart repository stored at %s is out of date- its contents do not match the repository contents.  To reindex the repository, find your Clip Art Navigator modules directory, and run "python localocal reindex %s %s" from the command line.  Note that this command must be run by a user with write access to %s .''' % (self.repoDir, self.dbfile, self.repoDir, self.dbfile))

	def __checkIndex(self):
		"Check whether the index db is synced with the repo contents; returns True or False"
		files = []
		for dirpath, subdirs, filenames in os.walk(self.repoDir):
			for name in filenames:
				if name.endswith('.svg'):
					files.append(name)
		newHash = ';'.join(files).__hash__()

		cur = self.con.cursor()
		cur.execute("SELECT value FROM settings WHERE key='statehash'")
		oldHash = cur.fetchone()[0]

		return oldHash == newHash

		pass
	
	def query(self, q):
		"Perform a query on the repository (using some to-be-standardized query string syntax) and return a list of (id, hash) duples as the result"

		cur = self.con.cursor()
		keywords = [word.lower() for word in q.split()]
		query = 'SELECT id, hash FROM images WHERE id IN (SELECT image_id FROM keywords WHERE %s )'
		parts = ' OR '.join([' word = ? '] * len(keywords))
		query = query % parts
		cur.execute(query, keywords)
		return cur.fetchall()
	
	def getImage(self, ID):
		"Fetch an image and its metadata by its repository id"

		cur = self.con.cursor()
		cur.execute('SELECT path, title, artist FROM images WHERE id=?', [ID])
		results = cur.fetchall()
		if len(results) is 0:
			return None
		path, title, artist = results[0][0], results[0][1], results[0][2]
		cur.execute('SELECT word FROM keywords WHERE image_id = ?', [ID])
		keywords = [row[0] for row in cur.fetchall()]
		xml = file(os.path.join(self.repoDir, path)).read()
		metadata={'title':title, 'artist':artist, 'keywords':keywords}
		return (xml, metadata)

# The following functions are used for manual administration of the local ocal repository; 
# they don't interact with the clip art navigator

def getMetadata(xml):
	"Given an xml document, get the rdf dc title value"

	metadata = {}

	doc = libxml2.parseDoc(xml)
	xp = doc.xpathNewContext()
	xp.xpathRegisterNs('svg', 'http://www.w3.org/2000/svg')
	xp.xpathRegisterNs('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
	xp.xpathRegisterNs('cc', 'http://web.resource.org/cc/')
	xp.xpathRegisterNs('dc', 'http://purl.org/dc/elements/1.1/')
	
	results = xp.xpathEval('//svg:metadata/rdf:RDF/cc:Work/dc:title')
	if len(results) == 1:
		metadata['title'] = results[0].getContent()

	results = xp.xpathEval('//svg:metadata/rdf:RDF/cc:Work/dc:creator/cc:Agent/dc:title')
	if len(results) == 1:
		metadata['artist'] = results[0].getContent()

	results = xp.xpathEval('//svg:metadata/rdf:RDF/cc:Work/dc:description')
	if len(results) == 1:
		metadata['description'] = results[0].getContent()

	results = xp.xpathEval('//svg:metadata/rdf:RDF/cc:Work/dc:subject/rdf:Bag/rdf:li')
	if len(results) > 0:
		metadata['keywords'] = tuple([elem.getContent() for elem in results])

	return metadata

def grabLatest(dir, url, verbose=False):
	"Download the latest OCAL dump and extract it to a given directory"

#	NOTE: This, obviously, uses bz2-zipped tarfile packages... thats the format it needs
#	And you might as well get the svg-only package, we don't need the other stuff

# 	No need to import this stuff when this module is just being used by the navigator
	import urllib 
	import bz2
	import tarfile
	import tempfile

	if verbose:
		print "Downloading latest OCAL release"

	filename, headers = urllib.urlretrieve(url)
	bz2contents = file(filename).read()
	if verbose:
		print "Downloaded %s (size %i kb)" % (url, len(bz2contents)/1024)
	tempname = tempfile.mkstemp(suffix='.tar')[1]
	print "Decompressing (may take a while)"
	file(tempname, 'w').write(bz2.decompress(bz2contents))
	if verbose:
		print "Decompressed successfully"
	tar = tarfile.open(tempname)
	if verbose:
		print "Parsed TARred contents"
	for member in tar.getmembers():
		tar.extract(member, dir)
		if verbose:
			print "Extracted", member.name
	try:
		os.remove(tempname)
	except:
		pass

def reindex(dbfile, repoDir):
	"Make the index database match the current state of the filesystem repository"
	try:
		os.remove(dbfile)
	except:
		pass

	repoDir=os.path.normpath(repoDir)
	
	con = sqlite.connect(dbfile)
	cur = con.cursor()

	cur.execute('CREATE table images (id INTEGER PRIMARY KEY, path, hash, title, artist)')
	cur.execute('CREATE table keywords (image_id INTEGER, word)')
	cur.execute('CREATE table settings (key UNIQUE, value)')
	con.commit()

	if verbose:
		print "\nInitialized index schema successfully"

	q1 = 'INSERT INTO images (path, hash, title, artist) VALUES (?, ?, ?, ?)'
	q2 = 'SELECT id FROM images WHERE hash = ?'
	q3 = 'INSERT INTO keywords (image_id, word) VALUES (?, ?)'
	files = [] # used to verify the state of the db in the future
	for dirpath, subdirs, filenames in os.walk(repoDir):
		for filename in filenames:
			if filename.endswith('.svg'):
				files.append(filename)
				try:
					path = os.path.join(dirpath, filename)
					contents = file(path).read()
					hash = md5.new(contents).hexdigest()
					m = getMetadata(contents)
					title = m.get('title', '')
					artist = m.get('artist', '')
					cur.execute(q1, [path[len(repoDir) + 1:], hash, title, artist])
					cur.execute(q2, [hash])
					new_id = cur.fetchone()[0]
					for word in m.get('keywords', []):
						cur.execute(q3, [new_id, word])
					if verbose:
						print "Indexed", path
				except:
					print 'oops!', path
	filehash = ';'.join(files).__hash__()
	cur.execute("INSERT INTO settings (key, value) VALUES ('statehash', ?)", [filehash])
	con.commit()

helptxt = '''NAME
\tlocalocal - Install a local clipart repository

SYNOPSIS
\tlocalocal.py [options] mode

\tOptions:
\t[-r REPODIR] [-i INDEX]

DESCRIPTION
localocal is both a python module providing the Clip Art Navigator program with access to local clip art repositories, and a command-line program for creating and maintaining such repositories.  The command-line form has two modes: downloading and installing a new repository, and indexing an existing repository.  In install mode, clip art content is downloaded from the Open Clip Art Library at http://www.openclipart.org .  If you modify the repository's contents after installation, or you would like to create an accessible repository of your own for the Clip Art Navigator, you can use the index mode to provide easy searching functionality.  In either mode, you can specify two options: the root directory of the repository, and the path to the index file.

A local clip art repository is just a directory containing svg images (which can be organized into nested subdirectories).  The index file is just an SQLite database that records basic metadata about each svg images, such as the title, artist, and keywords, along with the path at which the various images are actually located.  Separating the index from the actual content in this manner improves performance, but allows the index and the content to get out of sync(if images are added or removed from the repository).  This program's index mode allows the two to be synchronized again (the index is made to match the content, of course).  

Note that to run python scripts such as this, you either have to configure them to be executable in a platform dependent way (i.e. setting the executable permission in Linux), or invoke the Python interpreter directly.  See the examples below.

MODE
Either "install" or "index".  In install mode, the latest release of the Open Clip Art Library will be downloaded from http://www.openclipart.org, and its contents will be extracted and indexed.  In index mode, an index is created (possibly replacing an old index) from the contents of an existing directory.

OPTIONS
\t-r=REPODIR
\t\tSpecify the root directory of the repository.  All files with .svg extensions within this directory will be indexed.  On Unix, defaults to /usr/share/clipart .  On Windows, defaults to C:\Common\Clipart .
\t-v
\t\tVerbose output

\t-i=INDEX
\t\tSpecify the location of the index file.  Default to the file "index.dat" within the root directory of the repository.

EXAMPLES

python localocal.py install
python localocal.py -r ~/ocalindex.dat index



'''

if __name__ == '__main__':

	import sys
	import getopt
	import platform

	opts, args = getopt.getopt(sys.argv[1:], 'vr:i:')
	print opts, args
	if len(args) != 1 or args[0] not in ('index', 'install'):
		print helptxt
		sys.exit(1)
	mode = args[0]

	if platform.system() == 'Windows':
		repodir = 'C:\Common\Clipart'
	else:
		repodir = '/usr/share/clipart'
	
	verbose = False

	for opt, value in opts:
		if opt == '-r':
			repodir = value
		if opt == '-v':
			verbose = True
	
	indexpath = os.path.join(repodir, 'index.dat')
	for opt, value in opts:
		if opt == '-i':
			indexpath = value


#	Obviously, this needs to be made dynamic somehow
#	Ok option: a seperate func asks the server what the latest filename is
# 	(this is nice if people want to be able to check periodically if they have the latest version)
#	Better option: its always available under a consistent filename (i.e. openclipart-latest.tar.bz2)
#	(there can still be checking functionality, as long as the each package internally indicates its 
#	version #)... and the filename can just redirect to the latest real file
#	url = 'http://www.openclipart.org/downloads/0.16/openclipart-0.16-svgonly.tar.bz2'
	url = 'http://localhost:8080/static/openclipart-0.15.tar.bz2'

	if mode == 'install':
		grabLatest(repodir, url, verbose)
	reindex(indexpath, repodir)
