#!/usr/bin/perl

use Getopt::Std;
use VideoTools;
use File::Basename;
use Trace;
use strict;
use Win32::Console;
Win32::Console::InputCP(1252);
# require ConfigMgr;

my %h_opts;

my $me = basename($0);

sub usage
{
	print "
$me [-h] [-g <trace_level>] <inputfile1> <inputfile1> [<inputfile3>...] -o <outputfile> 	

Concatenates video files. All input files must be of same format, codec etc...

Arguments:
   <inputfile.x> : List of input files to concatenate. Can be 2 (minimum) or more
   <outputfile>: Concatenated file to generate. Mandatory. <outputfile> MUST be the last argument
   
Examples:
   $me myvideo1.avi othervideo.avi -g 3 concatvideo.avi
   $me myvideo1.mp4 myvideo2.mp4 myvideo3.mp4 myvideo4.mp4 concatvideo.mp4
   $me -h                                       (Displays this help and exits)
";
}

Trace::trace(1, join(" ", @ARGV)."\n");

my $ofile;
my @filelist;
while (my $arg = shift @ARGV)
{
  Trace::trace(1,"Looking at $arg\n");
  if ($arg eq '-h') {
    usage; exit 1;
  } elsif ($arg eq '-g') {
    Trace::setTraceLevel(shift @ARGV);
  } elsif ($arg eq '-o') {
    $ofile = (shift @ARGV);
  } else {
    push(@filelist, $arg);
  }
}

if (!defined($ofile)) {
	$ofile = 
	$ofile = FileTools::stripExtension($filelist[0]);
	$ofile .= "_concat.mp4";
}

die("At least 2 input files must be specified to concat, aborting. Type $me -h for help\n") if ($#filelist <= 1);
die("Output file \"$ofile\" already exist, aborting. Type $me -h for help\n") if (-f $ofile);

Trace::trace(1,"Concatenating ".join(" + ", @filelist)." => \"$ofile\"\n");
push(@filelist, $ofile);
VideoTools::concat_simple(@filelist);
#------------------------------------------------------------
