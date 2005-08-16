Clip Art Navigator

INSTALL NOTES

Dependencies: this code currently requires Python 2.4, GTK 2.6, PyGTK,
pysqlite 2, and the python bindings for libxml2.  XML handling will be
switched to PyXML eventually, but this has not been done yet.  This
libxml2 dependency prevents it from being used on windows currently
(at least, without installing libxml2 and its python bindings).  Once
the PyXML switch is done (and some path issues are worked through), it
should be very cross-platform.

The code consists of a main script (clipartnav.py) a ui directory
containing the libglade resource file (ui/clipartnav.glade), a modules
directory (modules) containing python modules for various repositories
(currently only one is provided, localocal), an Inkscape extension inx
file (clipartnav.inx), and a configuration file (clipartnav.conf).  

To install, copy clipartnav.conf to the .inkscape directory in your
home directory (or change the value of the configPath variable near
the top of clipartnav.py appropriately).  Copy the rest of the package
contents (clipartnav.py, clipartnav.inx, ui and modules) to your
Inkscape extensions directory.  Then, open clipartnav.conf and verify
that the "extensionsdir" setting points to your Inkscape extensions
directory (the main script uses the directory indicated by this value
as its working directory, and looks for its glade file and modules
package relative to the directory indicated by this value).

Next, setup the localocal repository (the only repository module
currently provided).  An automated downloader is included, but doesn't
really work well, so manual setup is reccommended (and is easy).
First, either locate a directory that you use to store SVG clipart
(/usr/share/clipart will be reccomended in the future), or download
and extract a recent OCAL release from http://www.openclipart.org .
Then, from the command-line, go to the directory that you modules
directory that you copied into your Inkscape extensions directory, and
execute "python localocal.py -v -r PATH index", where PATH is the
directory you're using to store clipart.  This will create a PySQLite
database indexing the contents of your clipart directory in a file
called "index.dat" in your clipart directory.  Now, open the
clipartnav.conf file again, and verify that the repodir setting points
to your clipart directory, and that your dbfile setting points to your
new index database file.  This should complete installation.


USAGE

The Clip Art Navigator can be used either from within Inkscape (via
the Extensions menu) or as a standalone program (via the clipartnav.py
script).  By default, it writes the clipart that is selected to
standard out, but can write to a file instead if the -f command-line
option is used, as in "python clipartnav.py -f out.svg".  For a
description of how the navigator uses repositories for its searching,
see the DESIGN.txt file.

MOST COLOSSAL BUGS

The navigator does not yet insert selected clipart into existing
documents; it just returns the clipart itself, replacing the previous
document.

Ironically, drag-and-drop from the Navigator to Inkscape works when
the Navigator is invoked as a standalone program, but not from within
Inkscape.  

Connectivity to OCAL is not yet implemented (this shouldn't be hard at
all... on the order of 30 lines of code... I just need to continue
working through my SOAP issues).

Copy-paste doesn't work; this one in particular is confusing me.  You
can copy-and-paste fine into gedit, but not into Inkscape.  I believe
that the clipboard target value is set correctly as "image/svg+xml"
(its the same ones I'm using for drag-and-drop, which does work).
Inkscape claims that there's nothing on the clipboard though.  I dug
through interface.cpp a bit to work through this, will dig some more
soon.

Very, very little detection of common errors is being done.


