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
$me -i <inputfile> [-o <outputfile>] [-r <range>] [-h] [-g <level>] \n\
	-i: Input file. Mandatory
	-o: Output file. Optional. <_inputfile>_recombined.mp4 by default
	-r: Ranges to cut (eg 00:00-17:25,41:25-1:36:19). Optional. Whole file by default
	-g: Trace level
	Example: $me -i myvideo.mp4 -o mymiddlechunk.mp4 -s 00:27:10 -e 00:34:43 
	";
}

my %options;
getopts('i:o:r:g:hc', \%options);

Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $ifile = $options{'i'};
my $ofile;

my $ranges = $options{'r'};
if (! defined($ranges) ) {
	print ("Range(s) ? ");
	$ranges = <STDIN>;
	chomp($ranges);
}

die("Input file (option -i) is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'i'}));
#die("One of option -s or -e is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'s'}) && ! defined($options{'e'}));
die("Input file \"$ifile\" not found, aborting. Type $me -h for help\n") if (! (-f $ifile));
Trace::trace(3, "Input file = $ifile\n");
Trace::trace(3, "Output file = $ofile\n");
Trace::trace(3, "Ranges = $ranges\n");

my @ranges = VideoTools::getTimeRanges($options{'r'});

my $profile = 'direct';
my $ext = FileTools::getFileExtension($ifile);

my @filelist;

$ofile = $options{'o'};
for (my $i=0; $i <= $#ranges; $i++) {
	$h_opts{'start'} = $ranges[$i]->{'start'};
	$h_opts{'stop'} = $ranges[$i]->{'stop'};
	my $j = $i+1;
	if ($#ranges > 0) {
		$ofile = FileTools::replaceExtension($ifile, "cut_$j.$ext");
	} else {
		$ofile = $options{'o'} || FileTools::replaceExtension($ifile, "cut.$ext");
	}
	push(@filelist, $ofile);
	die("Output file \"$ofile\" exists, aborting. Type $me -h for help\n") if (-f $ofile);
	Trace::trace (1,"Cutting video file \"$ifile\" between \"".$h_opts{'start'}."\" and \"".$h_opts{'stop'}."\", output into \"$ofile\"\n");
	VideoTools::encode($ifile, $ofile, $profile, \%h_opts, "");
	Trace::trace (1,"Video cut \"$ofile\" complete\n");
}

if (defined($options{'c'}) && ($#ranges > 0)) {
	# Reconcatenate all cuts
	$ofile = $options{'o'} || FileTools::replaceExtension($ifile, "recombined.$ext");
	Trace::trace(1,"Concatenating ".join(" + ", @filelist)." => \"$ofile\"\n");
	push(@filelist, $ofile);
	VideoTools::concat_simple(@filelist);
	Trace::trace(1,"Concatenation of \"$ofile\" complete\n");
}

# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
