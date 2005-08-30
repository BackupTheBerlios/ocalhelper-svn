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

INSTALL NOTES

The program should work out of the box; just run 

python clipartbrowser.py

The first time you run it, it will probably ask you if you'd like to
index your local clip art.  This is a very good idea.  Just select the
root directory of your local clip art.  If you don't have any local
clip art, I reccomend downloading the latest package from
http://www.openclipart.org, and extracting it somewhere on your
system.  Then, when the Clip Art Browser asks you where you keep your
local clip art, provide the top directory that was extracted from the
OCAL package.

CONFIG FILE NOTES

I'll try to briefly explain the most important aspects of the
configuration file here.  The configuration file should be kept either
in the same directory as the clipartbrowser.py file (use this location
for system wide configuration), or in a ".clipartbrowser" directory in
a user's home directory.  The config file is broken up into sections,
which are marked off by a line containing the section title enclosed
in square brackets.  For example, the "main" section starts after the
line

[main]

The browser itself uses two sections: "main" and "externalviewers.
The most important setting in the main section is the "modules" list.
This should be a list of the names of repository modules that the
browser should use, with modules separated by a semicolon.  Modules
are actually just python files in the "modules" directory.  So if
there's a "localocal.py" file in the modules directory, you can enable
that module by including "localocal" in your modules list.  It helps
performance to put faster repository modules (such as localocal) at
the beginning of the list, and slower ones (such as ocal_net) at the
end.  There are currently two repository modules included with the
browser: localocal and ocal_net.  localocal lets you access local clip
art, while ocal_net lets you access the Open Clip Art Library servers
at http://openclipart.org .  

Another important setting is "externalrenderercmd".  This lets you
specify a program to help the browser render images that the its
default renderer (GDK) can't handle.  On Windows systems, GDK can't
handle any SVG images at all, so this setting is particularly
important.  You use it to specify a command that can be run to
transform an SVG image into a PNG image.  The command should simply be
a string that can be typed at the command line to do the
transformation.  The string allows placeholders for several dynamic
values (placeholders begin with a dollar sign):

$svgfile    The absolute filename of the svg file to be used as input
$pngfile    The absolute filename of the png file to be used as output
$width      The requested width of the output file, in pixels
$height     The requested height of the output file, in pixels.

Many users will want to use the Inkscape SVG editor as their external
renderer.  To enable it on Linux machines, for example, you would have
the externalrenderercmd line read:

externalrenderercmd = inkscape $svgfile --export-png=$pngfile -w$width

A related setting is "rendermode".  This determines whether the
browser renders images using GDK, your external renderer (described
above), or by trying GDK and then using the external renderer if GDK
fails (most users will want this setting).  The corresponding values
it should be set to are "gdk", "external" and "both".

The "maxresults" setting lets you set a maximum number of results to
retrieve for a given search.  This can be useful when accessing slow
repositories, to prevent unexpectedly large searches from stopping the
program indefinitely.  If this setting is missing, or is set to 0,
there is no limit on the number of results retrieved.

The "externalviewers" section lets you specify external image viewers
or editors that can be launched from within the browser.  Each setting
in this section should specify a label for the viewer as the key, and
the command-line command for the viewer as the value.  For example, to
enable Inkview as an external viewer on Linux systems, you would add
the line

Inkview = inkview

to the [externalviewers] section.  The first viewer specified (if
any), will be given a quick access icon on the browser toolbar.
