#!/usr/bin/perl

use Getopt::Std;
use VideoTools;
use File::Basename;
use Trace;
use strict;
# require ConfigMgr;

my %h_opts;

my $me = basename($0);

sub usage
{
	print "
$me -i <inputfile> -f <format> [-o <outputfile>] [-h]	
   -i: Input file. Mandatory. Can be a file or a disk drive. In case of a disk drive, this assumes the drives contains a DVD
   -o: Output file. Optional. Automatically guessed if not specified (eg -i myvideo.avi -f mp4 will automatically create -o myvideo.mp4)
   -p: Output file format. Mandatory. Can be \"avi\", \"mp4\", \"mkv\"
   -g: Trace level. Optional. 1 by default. Use 0 for no trace output at all. Values higher than 1 display more traces

Examples:
   $me -i -myvideo.avi -f mp4 -o mynewvideo.mp4 (generates mynewvideo.mp4)
   $me -i -myvideo.avi -f mkv                   (generates myvideo.mkv)
   $me -i -myvideo.mkv -f avi -g 0              (generates myvideo.avi silently)
   $me -h                                       (Displays this help and exits)
";
}

my %options;
getopts('i:o:g:h', \%options);
Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $ifile = $options{'i'}; 
my $profile = "mp4"; # $options{'f'};
my $ofile = $options{'o'};
$ofile = FileTools::stripExtension($ifile).".".$profile if (! defined($ofile) );
Trace::trace(3, "Input file = $ifile\n");
Trace::trace(3, "Output format = $profile\n");
Trace::trace(3, "Output file = $ofile\n");
die "Input file (-i) is mandatory, type $me -h for help\n" if (!defined($ifile));
die "Output format (-f) is mandatory, type $me -h for help\n" if (!defined($profile));
die "Input file  \"$ifile\" does not exist, type $me -h for help\n" if (! (-f $ifile));


my %h_opts;

Trace::trace(1,"Changing file format for input file $ifile into output file $ofile\n");
VideoTools::encode($ifile, $ofile, $profile, \%h_opts, "");
#------------------------------------------------------------
