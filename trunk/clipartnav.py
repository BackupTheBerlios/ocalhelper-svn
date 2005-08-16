#!/usr/bin/python

import gtk
import pygtk
import gtk.glade
import tempfile
import libxml2 # The code needs to be moved to pyxml at some point
import ConfigParser
import subprocess
import os
import cStringIO
import sys
import getopt

class Searcher:
	"Abstracts away the process of searching different repositories and aggregating their results"

#	Takes an already loaded ConfigParser instance
	def __init__(self, config):
		try:
			moduleNames = [word.strip() for word in config.get('main', 'modules').split(';') if word.strip()]
			rawNames = [word.strip() for word in config.get('main', 'modules').split(';') if word.strip()]
			modules = []
			for name in rawNames:
#				Detect whether this repo serves as a cache for subsequent repos
				if name.endswith(' iscache'):
					modules.append((name[:-8], True))
				else:
					modules.append((name, False))

			if config.has_option('main', 'maxresults'):
				self.maxResults = int(config.get('main', 'maxresults').strip())
				assert self.maxResults >= 0
			else:
				self.maxResults = None
		except Exception, e:
			raise
			raise BadConfigError


		self.repos = [] # A list of (module, iscache) duples... 
		self.errorModules = []
		for name, cache in modules:
#			Get configuration info for each module
			modConfig = {}
			if config.has_section(name):
				for key, value in config.items(name):
					modConfig[key] = value
			try:
				package = __import__('modules.%s'  % name)
				mod = getattr(package, name)
#				Load a repo api instance, giving it its config info as a dict
				self.repos.append((mod.API(modConfig), cache))
				if getattr(self.repos[-1][0], 'initMessages', None):
					for msg in self.repos[-1][0].initMessages:
						d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK, format=msg)
						d.show()
						d.run()

			except:
				self.errorModules.append(name)

		if len(self.repos) is 0:
			raise NoRepositoriesError
	
	def __call__(self, q, statusCallback=None):
		"Given a query, search all repositories and return the net list of (xml, metadata) duples"
#		We uniquely identify images by the md5 hash of their xml contents, which
#		repositories are required to return (we could calculate it ourselves, but
#		that's a waste of time).  Duplicate images are filtered out of search results this way.
		allHashes = [] 
		allImages = []
		try:
			for repo, cache in self.repos:
#				Let the gui know what repo we're currently searching via a callback
				if callable(statusCallback):
					name = getattr(repo, 'title', '')
					statusCallback('Searching %s...' % name)
					results = repo.query(q) # A list of id, hash duples
					for ID, hash in results:
						if hash not in allHashes or hash is None:
							allHashes.append(hash)
							xml, metadata = repo.getImage(ID)
							if metadata is None:
								metadata = getMetadata(xml)
							allImages.append(xml, metadata) # an xml, metadata duple
							if self.maxResults and len(allHashes) == self.maxResults:
								raise MaxResults
		except MaxResults:
			pass
		return allImages # a list of xml, metadata duples

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

class Renderer:
	"Given svg data and a size, returns a gdk pixbuf rendering of it"

	def __init__(self, config):
		
		if config.has_option('main', 'inkscapecmd'):
			self.inkscapeCmd = config.get('main', 'inkscapecmd').strip()
		else:
			self.inkscapeCmd = 'inkscape' # reasonable default

		if config.has_option('main', 'renderinkscape'): # allowed values: always, backup, never
			self.renderInkscape = config.get('main', 'renderinkscape').strip().lower()
		else:
			self.renderInkscape = 'backup' # reasonable default

		self.svgTempName = tempfile.mkstemp(suffix='.svg')[1]
		self.pngTempName = tempfile.mkstemp(suffix='.png')[1]

#	Cleanup the tempfiles when this program exits
	def __del__(self):
		try:
			os.remove(self.svgTempName)
			os.remove(self.pngTempName)
		except:
			pass

	def __call__(self, xml, size):
		"Return a gdk pixbuf, rendering according to config file settings"
		f = file(self.svgTempName, 'w')
		f.write(xml)
		f.close()

		try:
			if self.renderInkscape == 'backup':
				try:
					pixbuf = self.__gdkRender(size)
					return self.__gdkRender(size)
				except:
					return self.__inkscapeRender(size)
			elif self.renderInkscape == 'always':
				return self.__inkscapeRender(size)
			else: # renderInkscape == 'never'
				return self.__gdkRender(size)
		except Exception, e:
			raise UnrenderableError

	def __gdkRender(self, size):
		"Render using librsvg"
#		The sys stuff is in here to keep gdk's potential error messages from being read by Inkscape
		sys.stdout = cStringIO.StringIO()
		try:
			pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.svgTempName, size, size)
			sys.stdout = sys.__stdout__
			return pixbuf
		except:
			sys.stdout = sys.__stdout__
			raise

	
	def __inkscapeRender(self, size):
		"Use inkscape to convert image to png, then render"
		cmd = '%s %s --export-png=%s -w%i -h%i' % (self.inkscapeCmd, self.svgTempName, self.pngTempName, size, size)
		p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		retcode = p.wait()
		if retcode is not 0:
			raise Exception

		return gtk.gdk.pixbuf_new_from_file(self.pngTempName)

class Interface(object):
	"Represents the Clip Art Navigator gui (and only the gui)"

	smallsize = 80 	# Dimensions of browse icons
	largesize = 240	# Dimensions of preview images 

	def __init__(self, config, searcher, renderer, outFile=None):
		"Modules is a list of repository module api objects used for querying"

		self.config = config
		self.outFile = outFile

		assert callable(searcher)
		self.search = searcher

		assert callable(renderer)
		self.makePixbuf = renderer

		self.xml = gtk.glade.XML('clipartnav.glade')
		self.xml.signal_autoconnect(self)

#		Columns are xml, icon pixbuf, preview pixbuf, marked-up title, raw title, artist, keywords
#		self.store itself is accessed as a property
		self.__storeIndex = 0
		self.__storeList = [gtk.ListStore(str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, str, str, str, str)]
		self.__firstSearch = True
		self.__queriesList = ['']

		self.window = self.xml.get_widget('mainwindow')
		self.statusbar = self.xml.get_widget('statusbar')
		self.statuscontext = self.statusbar.get_context_id('searching')

#		The main icon browsing box
		self.iconview = self.xml.get_widget('iconview')
		self.iconview.set_model(self.store)
		self.iconview.set_pixbuf_column(1)
		self.iconview.set_markup_column(3) # markup is required to make text small enough

		self.searchbox = self.xml.get_widget('searchbox')
		self.previewImg = self.xml.get_widget('previewImg')
		self.previewLabel = self.xml.get_widget('previewlabel')

		self.popupmenu = self.xml.get_widget('popupmenu')
		if self.config.has_option('main', 'inkviewcmd') and self.config.get('main', 'inkviewcmd'):
			self.inkviewcmd = self.config.get('main', 'inkviewcmd')
			ivItem = gtk.MenuItem('Preview with Inkview')
			ivItem.connect('activate', self.inkview)
			self.popupmenu.append(ivItem)
			ivItem.show()
			self.inkviewtmp = tempfile.mkstemp(suffix='.svg')[1]

		self.changeSelected(None)

#		gtk-style targets for ipc, i.e. dnd and clipboard-copy
		self.ipcTargets = [('image/svg+xml', 0, 0)]

		self.iconview.drag_source_set(gtk.gdk.BUTTON1_MASK, self.ipcTargets, gtk.gdk.ACTION_COPY)
		self.iconview.connect('drag_data_get', self.drag_data_get)

		self.clipboard = gtk.Clipboard()
	
	def __del__(self):
		"Cleanup the inkview temp file"
		try:
			os.delete(self.inkviewtmp)
		except:
			pass
	
	def __getStore(self):
		return self.__storeList[self.__storeIndex]
	def __getQuery(self):
		return self.__queriesList[self.__storeIndex]
	
	store = property(__getStore) # The actual gtk.ListStore being displayed currently
	query = property(__getQuery)

	def on_copy_activate(self, widget):
		"Copy the currently selected image to the clipboard"
		selected = self.iconview.get_selected_items()
		if len(selected) is 0:
			contents = ''
		else:
			contents = self.store[selected[0][0]][0]
		self.clipboard.set_with_data(self.ipcTargets, self.clipboard_get, lambda a, b: None, '')
		self.clipboard.set_text(contents)

#	This function never worked correctly, and probably serves no purpose anymore...
	def clipboard_get(self, clipboard, selection_data, info, contents):
		selection_data.set(selection_data.target, 8, contents)

	def drag_data_get(self, widget, context, selection_data, info, timestamp):
		"Provide data to be copied in a drag-drop"
		selected = self.iconview.get_selected_items()
		if len(selected) is 0:
			contents = ''
		else:
			contents = self.store[selected[0][0]][0]
		selection_data.set(selection_data.target, 8, contents)

	def makeStoreItem(self, xml, metadata):
		"Given svg xml and metadata, return a 7-tuple suitable for use in a ListStore"

		item = []
		item.append(xml) 					# index 0, the xml
		item.append(self.makePixbuf(xml, self.smallsize))	# index 1, icon pixbuf
		item.append(self.makePixbuf(xml, self.largesize))	# index 2, preview pixbuf
		title = metadata.get('title', '')
		if title:
			item.append('<small>%s</small>' % title)	# index 3, marked-up title
			item.append(title)				# index 4, raw title
		else:
			item.append('<small><i>No title</i></small>')
			item.append('')
		item.append(metadata.get('artist'))			# index 5, artist
		item.append(';;'.join(metadata.get('keywords', []))) 	# index 6, keywords

		return item

	def on_mainwindow_delete_event(self, widget, event):
		return False
	
	def on_mainwindow_destroy(self, widget):
		gtk.main_quit()

	def on_iconview_button_press_event(self, widget, event):
		"When the mouse is clicked in the browse window"
		if event.button is 3:
			x, y = event.get_coords()
			path = widget.get_path_at_pos(x, y)
			if not path:
				return
			else:
				widget.select_path(path)
				self.popupmenu.popup(None, None, None, event.button, event.time)
	
	def inkview(self, widget):
		"Preview the currently selected image with inkview"
		paths = self.iconview.get_selected_items()
		if len(paths) > 0:
			xml = self.store[paths[0][0]][0]
			file(self.inkviewtmp, 'w').write(xml)
		subprocess.call('%s %s' % (self.inkviewcmd, self.inkviewtmp), shell=True)

	def on_backbutton_clicked(self, widget):
		if self.__storeIndex is not 0:
			self.__storeIndex -= 1
			self.iconview.set_model(self.store)
			self.searchbox.set_text(self.query)
			self.changeSelected(None)

	def on_forwardbutton_clicked(self, widget):
		if self.__storeIndex != len(self.__storeList) - 1:
			self.__storeIndex += 1
			self.iconview.set_model(self.store)
			self.searchbox.set_text(self.query)
			self.changeSelected(None)

	def on_searchbox_activate(self, widget):
		"Perform a search"
		query = widget.get_text().strip()

		if not self.__firstSearch:
			del self.__storeList[self.__storeIndex + 1:]
			del self.__queriesList[self.__storeIndex + 1:]
			self.__storeList.append(gtk.ListStore(str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, str, str, str, str))
			self.__queriesList.append(query)
			self.__storeIndex = len(self.__storeList) - 1 
			self.iconview.set_model(self.store)
		else:
			self.__queriesList[0] = query
		self.changeSelected(None)

#		Update the UI so that users don't panic
#		These things don't always actually display... needs some tuning
		results = self.search(query, self.searchUpdate)
		self.statusbar.push(self.statuscontext, '%i images found... rendering images' % len(results))
		for i in range(3):
			gtk.main_iteration(False)

		for xml, metadata in results:
			try:
				self.store.append(self.makeStoreItem(xml, metadata))
			except Exception, e:
				print "EXCEPTION:", e
				pass # If an image couldn't be rendered, skip it
		self.__firstSearch = False
		self.statusbar.push(self.statuscontext, '%i images' % len(self.store))
	
	def searchUpdate(self, msg):
		"Update the statusbar with the name of the repository currently being searched"
		self.statusbar.pop(self.statuscontext)
		self.statusbar.push(self.statuscontext, msg)
		gtk.main_iteration()

#	This function, clearly, needs humungous work
	def on_iconview_item_activated(self, widget, path):
		#origxml = minidom.parseString(sys.stdin.read())
		imgXML = self.store[path[0]][0]
		if self.outFile is None:
			print imgXML
		else:
			file(self.outFile, 'w').write(imgXML)
		gtk.main_quit()

	def on_iconview_selection_changed(self, widget, event=None):
		"When the currently selected image changes"
		selected = self.iconview.get_selected_items()
		if selected:
			selected = selected[0][0]
		else:
			selected = None
		if selected != self.selected:
			self.changeSelected(selected)
	
#	Change the preview image and labels
	def changeSelected(self, path):
		"Sync the preview pane with the currently selected item"
		if path is not None:
			self.previewImg.set_from_pixbuf(self.store[path][2])
			label = '<b>Title</b>: %s\n<b>Artist</b>: %s\n<b>Keywords</b>: %s' % (self.store[path][4], self.store[path][5], ', '.join(self.store[path][6].split(';;')))
			self.previewLabel.set_markup(label)
		else:
			self.previewImg.set_from_pixbuf(None)
			self.previewLabel.set_markup('')
		self.selected = path
	
class BadConfigError(Exception):
	"The configuration file is missing required values"
	pass

class NoRepositoriesError(Exception):
	"No repository modules were able to be loaded"
	pass

class UnrenderableError(Exception):
	"We were unable to render a particular image"
	pass

class MaxResults(Exception):
	"The maximum allowed number of search results was reached"
	pass

if __name__ == '__main__':
	origDir = os.getcwd() # We switch to another dir to load modules, glade, etc., then switch back
	opts, args = getopt.getopt(sys.argv[1:], 'f:')
	outFile = None # None means standard output, Inkscape style
	for opt, value in opts:
		if opt == '-f':
			outFile = value
	
	config = ConfigParser.SafeConfigParser()
	configPaths = [os.path.expanduser('~/.inkscape/clipartnav.conf'), 'clipartnav.conf']
	if not config.read(configPaths):
		sys.exit('Unable to find configuration file; looking at %s' % configPaths)
	if not config.has_option('main', 'extensionsdir'):
		sys.exit('Invalid configuration file; missing "extensionsdir" variable in the "main" section')
	os.chdir(config.get('main', 'extensionsdir'))
	try:
		searcher = Searcher(config)
	except NoRepositoriesError:
		sys.exit('Error: no repositories were able to be loaded.  Check your config file and repository module dir')
	renderer = Renderer(config)
	interface = Interface(config, searcher, renderer, outFile=outFile)
	os.chdir(origDir) # We switch back to orig dir so that writing output to a file works as expected
	gtk.main()
