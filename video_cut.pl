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
$me -i <inputfile> [-o <outputfile>] [-s <starttime>] [-e <endtime>] [-h] [-g] \n\
	-i: Input file. Mandatory
	-o: Output file. Optional. <_inputfile>_cut.mp4 by default
	-s: Start time to cut. Optional. 00:00:00 by default
	-e: End time to cut. Optional. End of file by default
      One of -s or -e is mandatory otherwise no cut would be done.
	-g: Trace level
	Example: $me -i myvideo.mp4 -o mymiddlechunk.mp4 -s 00:27:10 -e 00:34:43 
	";
}

my %options;
getopts('i:o:s:e:g:h', \%options);

Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $ifile = $options{'i'};
my $ofile = $options{'o'};
my $starttime = $options{'s'};
my $stoptime = $options{'e'};
if (! defined($ofile) ) {
  $ofile = FileTools::stripExtension($ifile);
  $ofile .= "_cut.mp4";
}

die("Input file (option -i) is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'i'}));
die("One of option -s or -e is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'s'}) && ! defined($options{'e'}));
die("Input file \"$ifile\" not found, aborting. Type $me -h for help\n") if (! (-f $ifile));
die("Output file \"$ofile\" exists, aborting. Type $me -h for help\n") if (-f $ofile);
die("Output file \"$ofile\" exists, aborting. Type $me -h for help\n") if (-f $ofile);
Trace::trace(3, "Input file = $ifile\n");
Trace::trace(3, "Output file = $ofile\n");
Trace::trace(3, "Start Time = $starttime\n");
Trace::trace(3, "Stop Time = $stoptime\n");

$h_opts{'start'} = $options{'b'} if (defined($options{'b'}));

# Video cropping options

$h_opts{'start'} = $starttime if (defined($starttime));
$h_opts{'stop'} = $stoptime if (defined($stoptime));

my $profile = 'direct';

Trace::trace (1,"Cutting video file $ifile  between \"$starttime\" and \"$stoptime\", output into \"$ofile\"\n");
VideoTools::encode($ifile, $ofile, $profile, \%h_opts, "");

# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
