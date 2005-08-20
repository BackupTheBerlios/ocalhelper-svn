Clip Art Navigator

INSTALL NOTES

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
