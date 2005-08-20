Clip Art Navigator

ABOUT

The Clip Art Navigator is a small program written with Python and GTK
to allow people to search for clip art easily.  It is designed
primarily as an extension for the Inkscape SVG editor, though it can
be used as a standalone program as well.  It searches one or more clip
art repositories, displays the aggregated results, and outputs the
contents of an image the user selects.  Note that the Clip Art
Navigator is currently limited to SVG clipart, though this may change
in the future.

The author would like to thank Google for funding the development of
this tool.

USAGE

To invoke the program directly, run the "clipartnav.py" program from
the command line.  This is a Python script, and should be invoked
however you generally invoke Python programs on your system.  If
invoke without the "-f" option, it will print the contents of the
selected clip
art image to standard output (in the case of svg clip art, these
contents are svg xml).  If invoked with the "-f" flag, it will write
the selected clip art to the given filename.  For example, to have it
write the selected clip art to the file "out.svg", run

python clipartnav.py -f out.svg

The script also takes one optional command line argument; an input
document filename.  If given, the program will insert the selected
clipart into the svg document indicated by the given filename before
outputting the combined image.  This usage is primarily intended for
use by Inkscape, and not expected to be used by users directly.

You may also drag-and-drop images from the navigator into other
appropriate programs.  Copy-paste functionality doesn't quite work
yet, but is being worked on.

INSTALL NOTES

General

The Clip Art Navigator REQUIRES Python 2.4, GTK 2.6, and PyGTK >= 2.6.
In addition, Inkscape 0.42 and  a recent PyXML (from
http://pyxml.sourceforge.net) are strongly reccommended.

To install as a standalone program, simply unpack.  This distribution
comes with two repository modules: localocal (for local system
clipart) and ocal (remote access to the Open Clip Art Library).  You
can choose to use one or both of these modules via the "modules"
option under the "main" section in the configuration file
(clipartnav.conf).  Modules are simply listed by their python name
(i.e. the name of the file they're contained in in the modules
directory, without the trailing ".py"), and are separated by a
semicolon.  For example, to use both the localocal and ocal modules,
have the modules line in your configuration file read:

modules = localocal; ocal

The ocal module works out of the box, but the localocal module
requires a little bit of configuration.  First, download a recent OCAL
release from http://openclipart.org, and extract it somewhere (we
reccommend /usr/share/clipart if you have root access, but anywhere
will do).  Then, index your clipart by running the included
"indexClipart.py" script, passing in the root directory of your
extracted clipart as the first argument.  There's an optional "-v"
flag for verbose output that you'll probably want to use too.  For
example, to index clip art at /usr/share/clipart , run

python indexClipart.py -v /usr/share/clipart

Then, open the configuration file and set the "repodir" option under
the "localocal" section to whatever directory you just used to index
your clipart.  For example:

[localocal]
repodir = /usr/share/clipart

Your localocal repository is now ready to use.  You also may want to
copy your configuration file to the ".inkscape" directory in your home
directory.  The Clip Art Navigator looks there and in the Inkscape
extensions directory for the configuration file (if configuration
files are found in both locations, the user file will be used when
settings between the two conflict).


After installation, it is highly reccommended that you download a
recent release of the Open Clip Art Library from
http://openclipart.org.  Extract the release contents somewhere on
your computer, and then run the modules/indexClipart.py script,
passing the path to the directory where you extracted the clipart as
the first argument.  You'll probably want to use the -v flag for
verbose output.  For example:

python indexClipart.py -v /usr/share/clipart

(if your root clip art directory is /usr/share/clipart).  This script
creates an index of your local clipart that the Clip Art Navigator can
use for searching.

Inkscape

To install the Clip Art Navigator as an Inkscape extension, simply extract the
contents of the package to Inkscape's extensions directory (on Linux, this is
typically /usr/local/share/inkscape/extensions).  Inkscape usage requires the
following files to be present in that directory:

clipartnav.py
clipartnav.glade
clipartnav.inx
modules/__init__.py

and whatever repository module files you want must be present in the modules
directory.  
