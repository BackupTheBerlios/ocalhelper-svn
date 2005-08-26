#!/usr/bin/python

import gtk
import gtk.glade
from xml.parsers import expat

class RepoTree(gtk.TreeStore):
    "A gtk tree model for storing the category hierarchies of loaded repositories"
    def __init__(self):

#       Columns are id, label (often the same as id), repository (the repository object itself)
        gtk.TreeStore.__init__(self, str, str, object)


        self.repositories = []
        self.searchResultsRow = self.append(None, ['searchResults', 'Search Results', None])

    def __startElementHandler(self, name, attrs):
        if name == 'category':
            if attrs.has_key('id'):
                ID = attrs['id']
            else:
                ID = attrs['name']
            iter = self.append(self.path[-1], [ID, attrs['name'], self.__currentRepo])
            self.path.append(iter)
    def __endElementHandler(self, name):
        if name == 'category':
            self.path.pop()

#   repo is a repository module api object
    def addRepo(self, repo): 
        "Load a repository module"
        self.repositories.append(repo)

#       All repositories get a row in the browse pane, even if they have no subcategories
#       This inserts the new repository just before the search results item, so they're still in insertion order
        topRow = ['/', repo.title, repo]
        iter = self.insert(None, len(self) - 1, row=topRow)
        self.path = [iter]

        xml = repo.categoriesXML
        if xml: # If they have browsable categories (defined in xml), add those to the treestore
            self.parser = expat.ParserCreate()
            self.parser.StartElementHandler = self.__startElementHandler
            self.parser.EndElementHandler = self.__endElementHandler

            self.__currentRepo = repo
            self.parser.Parse(xml)
            del self.__currentRepo

class Repo:
    categoriesXML = file('cats.xml').read()
    title = 'Local clipart'

class Interface:

        def __init__(self):
            self.xml = gtk.glade.XML('newglade.glade')
            self.xml.signal_autoconnect(self)

#           Left-hand category browsing tree
            self.repotree = RepoTree()
            self.browsepane = self.xml.get_widget('browsepane')
            cellRenderer = gtk.CellRendererText()
            categoryColumn = gtk.TreeViewColumn('Categories', cellRenderer)
            categoryColumn.add_attribute(cellRenderer, 'text', 1)
            self.browsepane.append_column(categoryColumn)
            self.browsepane.set_model(self.repotree)
            self.repotree.addRepo(Repo())

#           Right-hand results window
            self.iconview = self.xml.get_widget('iconview')

#           Statusbar
            self.statusbar = self.xml.get_widget('statusbar')

        def __loadRepoHierarchy(self, xml):
            if not xml:
                return
            parser = expat.ParserCreate()

        def on_mainwindow_delete_event(self, widget, event):
            return False
        def on_mainwindow_destroy(self, widget):
            gtk.main_quit()

interface = Interface()
gtk.main()
