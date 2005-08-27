#!/usr/bin/python
"""
clipartbrowser.py - An extension to Inkscape for searching for clip art
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

import gtk
import pygtk
import gtk.glade
import tempfile
import ConfigParser
import subprocess
import os
import sys
import getopt
from cStringIO import StringIO
import md5
from xml.dom import minidom
from xml.parsers import expat


class RepoTree(gtk.TreeStore):
    "A gtk tree model for storing the category hierarchies of loaded repositories"

    def __init__(self, config):

        try:
            repoNames =  [word.strip() for word in config.get('main', 'modules').split(';') if word.strip()]

            if config.has_option('main', 'maxresults'):
                self.maxResults = int(config.get('main', 'maxresults').strip())
                assert self.maxResults >= 0
            else:
                self.maxResults = None
        except Exception, e:
            raise BadConfigError

        self.repositories = [] # A list of (module, iscache) duples... 
        self.errorModules = []
        for name in repoNames: # for each repo name, try to load a module with that name and create an api object
            try:
                package = __import__('modules.%s'  % name) # we look for modules in the "modules" package
                mod = getattr(package, name)
#                Load a repo api instance, giving it its config info as a dict
                self.repositories.append(mod.API(config))
            except:
                self.errorModules.append(name)

        if len(self.repositories) is 0:
            raise NoRepositoriesError
 
#       Columns are:
#           the query string used to produce this view
#           the on-screen label for this view
#           the list of repositories searched to produce this view
#           old search results (you can store them here to avoid having to do the search again)
        gtk.TreeStore.__init__(self, str, str, object, object)

        for repo in self.repositories:
            self.__addRepo(repo)
#       After all repos are added, add the "Search Results" group, which searches through ALL repositories
        self.searchResultsRow = self.append(None, ['', 'Recent searches', self.repositories, None])

    @staticmethod
    def query(q, repos, maxResults=None, statusCallback=None):
        q = q.strip()

        if not q: # If repos are implemented correctly, this would happen anyway, but this is faster
            return []

#       We uniquely identify images by the md5 hash of their xml contents, which
#       repositories are required to return (we could calculate it ourselves, but
#       that's a waste of time).  Duplicate images are filtered out of search results this way.
        allHashes = [] 
        allImages = []
        try:
            for repo in repos:
#               Let the gui know what repo we're currently searching via a callback
                if callable(statusCallback):
                    name = getattr(repo, 'title', '')
                    statusCallback('Searching %s...' % name)
                results = repo.query(q) # A list of id, hash duples
                for ID, hash in results: # If the repo doesn't provide hashes, calculate it dynamically
                    if hash is None:
                        hash = md5.new(xml).hexdigest()
                    if hash not in allHashes:
                        allHashes.append(hash)
                        xml, metadata = repo.getImage(ID)
                        if metadata is None:
                            metadata = getMetadata(xml)
                        metadata['MD5 hash'] = hash
                        allImages.append((xml, metadata)) # an xml, metadata duple
                        if maxResults and len(allHashes) == maxResults:
                            raise MaxResults
        except MaxResults: # we're using exceptions as goto statements.... the horror!
            pass
        return allImages # a list of xml, metadata duples

    def __startElementHandler(self, name, attrs):
        if name == 'category':
            if attrs.has_key('id'):
                ID = attrs['id']
            else:
                ID = attrs['name']
            newRow = ['category:"%s"' % ID, attrs['name'].capitalize(), (self.__currentRepo,), None]
            iter = self.append(self.path[-1], newRow) #self.path[-1] is the parent category of this category
            self.path.append(iter) # record that we've descended one step into the hierarchy
    def __endElementHandler(self, name):
        if name == 'category':
            self.path.pop() # record that we've ascended one step in the hierarchy

#   repo is a repository module api object
    def __addRepo(self, repo): 
        "Load a repository module"

#       All repositories get a row in the browse pane, even if they have no subcategories
        topRow = ['category:"/"', repo.title, (repo,), None]
        iter = self.append(None, topRow)
        self.path = [iter]

        xml = repo.catsXML
        if xml: # If they have browsable categories (defined in xml), add those to the treestore
            self.parser = expat.ParserCreate()
            self.parser.StartElementHandler = self.__startElementHandler
            self.parser.EndElementHandler = self.__endElementHandler

            self.__currentRepo = repo
            self.parser.Parse(xml)
            del self.__currentRepo

    def addSearch(self, query):
        "Add a search to the search queries"
        newRow = [query, query[:50], self.repositories, None]
        return self.get_path(self.append(self.searchResultsRow, newRow))

    def clearSearches(self):
        "Clear the search list"
        child = self.iter_children(self.searchResultsRow)
        while child:
            oldchild = child
            child = self.iter_next(child)
            self.remove(oldchild)

    def getSearchRowPath(self):
        return self.get_path(self.searchResultsRow)

# A callable class for rendering svg data into pixbufs
# FIXME: this would be a WONDERFUL place to add caching
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

#    Cleanup the tempfiles when this program exits
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
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self.svgTempName, size, size)
        return pixbuf

    
    def __inkscapeRender(self, size):
        "Use inkscape to convert image to png, then render"
        cmd = '%s %s --export-png=%s -w%i -h%i' % (self.inkscapeCmd, self.svgTempName, self.pngTempName, size, size)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = p.wait()
        if retcode is not 0:
            raise Exception

        return gtk.gdk.pixbuf_new_from_file(self.pngTempName)


class _MetadataParser:

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
    m = _MetadataParser()
    parser.StartElementHandler = m.metadata_startElement
    parser.EndElementHandler = m.metadata_endElement
    parser.CharacterDataHandler = m.metadata_charData
    parser.Parse(svg)
    metadata['title'] = getattr(m, 'title', None)
    metadata['artist'] = getattr(m, 'artist', None)
    metadata['keywords'] = getattr(m, 'keywords', [])
    return metadata


class Interface(object):
    "Represents the Clip Art Navigator gui (and only the gui)"

    smallsize = 80     # Dimensions of browse icons
    largesize = 240    # Dimensions of preview images 

    def __init__(self, config, repotree, renderer, outFile=None, filename=None):
        "Modules is a list of repository module api objects used for querying"

        self.config = config
        self.outFile = outFile

        assert callable(renderer)
        self.makePixbuf = renderer

        self.filename = filename

        self.xml = gtk.glade.XML('clipartbrowser.glade', 'mainwindow')
        self.xml.signal_autoconnect(self)

        self.repoTree = repotree
        self.browsepane = self.xml.get_widget('browsepane')
        cellRenderer = gtk.CellRendererText()
        self.categoryColumn = gtk.TreeViewColumn('Categories', cellRenderer)
        self.categoryColumn.add_attribute(cellRenderer, 'text', 1)
        self.browsepane.append_column(self.categoryColumn)
        self.browsepane.set_model(self.repoTree)

#       Columns are:
#           xml
#           icon pixbuf
#           marked-up title
#           metadata (the original dict)
        self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, object)
        self.iconview = self.xml.get_widget('iconview')
        self.iconview.set_model(self.store)
        self.iconview.set_pixbuf_column(1)
        self.iconview.set_markup_column(2)

        self.window = self.xml.get_widget('mainwindow')
        self.statusbar = self.xml.get_widget('statusbar')
        self.statuscontext = self.statusbar.get_context_id('searching')

        if self.config.has_option('main', 'inkviewcmd') and self.config.get('main', 'inkviewcmd'):
            self.inkviewcmd = self.config.get('main', 'inkviewcmd')
            self.inkviewtmp = tempfile.mkstemp(suffix='.svg')[1]
        else:
            self.inkviewcmd = None

#        gtk-style targets for ipc, i.e. d-n-d and clipboard-copy
        self.ipcTargets = [('image/svg', 0, 0)]

        self.iconview.drag_source_set(gtk.gdk.BUTTON1_MASK, self.ipcTargets, gtk.gdk.ACTION_COPY)
        self.iconview.connect('drag_data_get', self.drag_data_get)

        self.clipboard = gtk.Clipboard(selection='CLIPBOARD')

    
    def __del__(self):
        "Cleanup the inkview temp file"
        try:
            os.delete(self.inkviewtmp)
        except:
            pass

    def on_imageinfo_activate(self, widget):
#       Setup the image info window
        infoXML = gtk.glade.XML('clipartbrowser.glade', 'infowindow')
        infoXML.signal_autoconnect(self)
        self.infowindow = infoXML.get_widget('infowindow') # note that this is initially invisible
        self.infotable = infoXML.get_widget('metadata_table')
        self.infoimage = infoXML.get_widget('infoimage')
        paths = self.iconview.get_selected_items()

        if paths:
#           Show the preview image
            pixbuf = self.makePixbuf(self.store[paths[0][0]][0], 250)
            self.infoimage.set_from_pixbuf(pixbuf)

#           Show the metadata
            metadata = self.store[paths[0][0]][3].items()
            self.infotable.resize(0,0)
            self.infotable.resize(len(metadata), 2)
            for i, data in enumerate(sorted(metadata)):
                key, value = data
                keyLabel = gtk.Label('<b>%s</b>' % key.capitalize())
                keyLabel.set_use_markup(True)
                self.infotable.attach(keyLabel, 0, 1, i, i + 1)

#               value might be a string, a sequence, or something else
                if isinstance(value, basestring):
                    valueLabel = gtk.Label(value)
                elif hasattr(value, '__iter__'): # if its a sequence of some sort, like keywords
                    valueLabel = gtk.Label(', '.join(value))
                else:
                    valueLabel = gtk.Label(str(value))
                valueLabel.set_selectable(True)
                valueLabel.set_width_chars(35)

                keyLabel.wrap = True
                keyLabel.set_alignment(0,0)
                valueLabel.wrap = True
                valueLabel.set_alignment(0,0)
                keyLabel.show()
                valueLabel.show()
                self.infotable.attach(valueLabel, 1, 2, i, i + 1)
                self.infowindow.show()
    def on_infowindow_delete_event(self, widget, event):
        print 'deleting info window'
        self.infowindow.hide()
        return True
    
    def on_browsepane_cursor_changed(self, treeview):
        path, column = self.browsepane.get_cursor()
        selectedRow = self.repoTree.get_iter(path)
        query, repos = self.repoTree.get(selectedRow, 0, 2)
        results = self.repoTree.query(query, repos, statusCallback = self.searchUpdate)
        self.statusbar.push(self.statuscontext, 'Found %i images... rendering images' % len(results))
        for i in range(3): # Give the statusbar message a chance to be shown
            gtk.main_iteration(False)
        print 'found %i results' % len(results)
        self.store.clear()
        for xml, metadata in results:
            self.store.append(self.makeStoreItem(xml, metadata))
            print 'rendered item'

    def on_search_activate(self, widget):
        xml = gtk.glade.XML('clipartbrowser.glade', 'searchbox')
        dialog = xml.get_widget('searchbox')
        inputbar = xml.get_widget('searchbar')
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_OK:
            query = inputbar.get_text()
            path = self.repoTree.addSearch(query)
            self.browsepane.expand_row(self.repoTree.getSearchRowPath(), False)
            self.browsepane.set_cursor(path)

    def on_clearsearches_activate(self, widget):
        self.repoTree.clearSearches()
        self.browsepane.set_cursor(self.repoTree.getSearchRowPath())

    def on_about_activate(self, widget):
        dialog = gtk.glade.XML('clipartbrowser.glade', 'aboutdialog').get_widget('aboutdialog')
        dialog.show()
        
    
    def on_copy_activate(self, widget):
        "Copy the currently selected image to the clipboard"
        selected = self.iconview.get_selected_items()
        if len(selected) is 0:
            contents = ''
        else:
            contents = self.store[selected[0][0]][0] # the image xml
        self.clipboard.clear()
        self.clipboard.set_with_data(self.ipcTargets, self.clipboard_get, self.clipboard_clear, contents)

    def clipboard_get(self, clipboard, selection_data, info, contents):
        selection_data.set(gtk.gdk.SELECTION_CLIPBOARD, 8, contents)

    def clipboard_clear(self, clipboard, data):
        pass

    def drag_data_get(self, widget, context, selection_data, info, timestamp):
        "Provide data to be copied in a drag-drop"
        selected = self.iconview.get_selected_items()
        if len(selected) is 0:
            contents = ''
        else:
            contents = self.store[selected[0][0]][0] # the image xml
        selection_data.set(selection_data.target, 8, contents)

#    FIXME: This needs to behave more intelligently when certain metadata values don't exist
    def makeStoreItem(self, xml, metadata):
        "Given svg xml and metadata, return a 7-tuple suitable for use in a ListStore"

        item = []
        item.append(xml)                     # index 0, the xml
        item.append(self.makePixbuf(xml, self.smallsize))    # index 1, icon pixbuf
        title = metadata.get('title', '')
        if title:
            item.append('<small>%s</small>' % title)    # index 3, marked-up title
        else:
            item.append('<small><i>No title</i></small>')
        item.append(metadata)
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
    
    def on_preview_activate(self, widget):
        "Preview the currently selected image with inkview"

#       FIXME: Code should be added here to try to preview with gdk as a fallback
        if not self.inkviewcmd:
            return

        paths = self.iconview.get_selected_items()
        if len(paths) > 0:
            xml = self.store[paths[0][0]][0]
            file(self.inkviewtmp, 'w').write(xml)
        subprocess.call('%s %s' % (self.inkviewcmd, self.inkviewtmp), shell=True)

    def searchUpdate(self, msg):
        "Update the statusbar with the name of the repository currently being searched"
        self.statusbar.pop(self.statuscontext)
        self.statusbar.push(self.statuscontext, msg)
        gtk.main_iteration()
        gtk.main_iteration()

    
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
#    We switch to the directory this script is in (using an admittedly odd technique) so that we can access 
#    needed files in that directory easily
    origDir = os.getcwd() 
    import modules
    os.chdir(os.path.split(modules.__path__[0])[0])
    opts, args = getopt.getopt(sys.argv[1:], 'f:', ('id='))
    outFile = None # None means standard output, Inkscape style

    for opt, value in opts:
        if opt == '-f':
            outFile = value
    
#    If a filename is provided as an arg, insert clipart into it 
    if len(args) > 0:
        inputFilename = args[0]
    else: # Otherwise, just output the clipart itself
        inputFilename = None

    config = ConfigParser.SafeConfigParser()
    configPaths = [os.path.expanduser('~/.inkscape/clipartbrowser.conf'), 'clipartbrowser.conf']
    if not config.read(configPaths):
        sys.exit('Unable to find configuration file; looking at %s' % configPaths)
    try:
        repobrowser = RepoTree(config)
    except NoRepositoriesError:
        sys.exit('Error: no repositories were able to be loaded.  Check your config file and repository module dir')
    renderer = Renderer(config)
    interface = Interface(config, repobrowser, renderer, outFile=outFile, filename=inputFilename)
    os.chdir(origDir) # We switch back to orig dir so that writing output to a file works as expected
    gtk.main()
