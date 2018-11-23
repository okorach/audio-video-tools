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
$me -i <inputfile> [-o <outputfile>] [-s <starttime>] [-e <endtime>] [-h] [-g] [-c]\n\
	-i: Input file. Mandatory
	-o: Output file. Optional. <_inputfile>_recombined.mp4 by default
	-s: Start times to cut (eg 00:00,41:25,1:36:19). Optional. 00:00:00 by default
	-e: End times to cut (eg 38:35,1:33:25,). Optional. End of file by default
	-c: Reconcatenate all after cutting segments
	-g: Trace level
	Example: $me -i myvideo.mp4 -o mymiddlechunk.mp4 -s 00:27:10 -e 00:34:43 
	";
}

my %options;
getopts('i:o:s:e:cg:h', \%options);

Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $ifile = $options{'i'};
my $ofile;
my $starttime = $options{'s'};
my $stoptime = $options{'e'};

die("Input file (option -i) is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'i'}));
#die("One of option -s or -e is mandatory, aborting. Type $me -h for help\n") if (! defined($options{'s'}) && ! defined($options{'e'}));
die("Input file \"$ifile\" not found, aborting. Type $me -h for help\n") if (! (-f $ifile));

Trace::trace(3, "Input file = $ifile\n");
Trace::trace(3, "Output file = $ofile\n");

if (! defined($starttime) && !defined($stoptime) ) {
	print ("Start Time(s) ? ");
	$starttime = <STDIN>;
	chomp($starttime);
	print ("End Time(s) ? ");
	$stoptime = <STDIN>;
	chomp($stoptime);
}


Trace::trace(3, "Start Time = $starttime\n");
Trace::trace(3, "Stop Time = $stoptime\n");


my @starttab;
if ($starttime ne '') {
	@starttab = split(/\s*,\s*/, $starttime, -1);
} else {
	push(@starttab, '');
}
my @endtab;
if ($stoptime ne '') {
	@endtab = split(/\s*,\s*/, $stoptime, -1);
} else {
	push(@endtab, '');
}
die("Nbr of starttimes and endtimes must be the same (Start: $#starttab vs End: $#endtab), aborting. Type $me -h for help\n") if ($#starttab != $#endtab);

my $profile = 'direct';
my @filelist;

for (my $i=0; $i <= $#starttab; $i++) {
	$h_opts{'start'} = $starttab[$i] if (defined($starttab[$i]) && ($starttab[$i] ne ""));
	$h_opts{'stop'} = $endtab[$i] if (defined($endtab[$i]) && ($endtab[$i] ne ""));
	if (defined($options{'o'}) && ($#starttab == 0)) {
		$ofile = $options{'o'};
	} else {
		$ofile = FileTools::stripExtension($ifile);
		$ofile .= "_cut_$i.mp4";
	}
	push(@filelist, $ofile);
	die("Output file \"$ofile\" exists, aborting. Type $me -h for help\n") if (-f $ofile);
	Trace::trace (1,"Cutting video file $ifile  between \"$starttab[$i]\" and \"$endtab[$i]\", output into \"$ofile\"\n");
	VideoTools::encode($ifile, $ofile, $profile, \%h_opts, "");
}

if (defined($options{'c'}) && ($#starttab > 0)) {
	# Reconcatenate all cuts
	$ofile = $options{'o'};
	if (! defined($ofile) ) {
		$ofile = FileTools::stripExtension($ifile);
		$ofile .= "_concat.mp4";
	}
	Trace::trace(1,"Concatenating ".join(" + ", @filelist)." => \"$ofile\"\n");
	push(@filelist, $ofile);
	VideoTools::concat_simple(@filelist);
}

# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
