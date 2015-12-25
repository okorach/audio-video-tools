#!/usr/bin/perl

use Getopt::Std;
use VideoTools;
use File::Basename;
use Trace qw(trace);

use strict;

my $me = basename($0);

sub usage
{
	print "
$me [-s <source>] [-t <target>] [-p <profile>] [-g <trace_level>] [-h] \n\
	-s: Source directory. Mandatory parameter. Must exist
	-t: Target directory. Optional parameter \"<source> recoded\" by default. Directory created if it does not already exist
	-p: Output profile. Default value is mp3_128k coded with ffmpeg LAME library
	-g: Set trace level
	-h: Prints this help and exits
	"
}

my %options;
getopts('s:t:p:hg:', \%options);

if ($options{'h'}) { usage; exit; }
# my $root = $options{'r'};
my $src_dir = $options{'s'};
my $tgt_dir = $options{'t'} || "$src_dir recoded";
my $profile = $options{'p'} || 'mp3_128k';
my $lvl = $options{'g'} || 1;
  
use File::Spec;
$src_dir = File::Spec->rel2abs( $src_dir ) ;
$tgt_dir = File::Spec->rel2abs( $tgt_dir ) ;

die 'ERROR: Source directory undefined, aborting' if (! defined($src_dir));
die "ERROR: Source directory \"$src_dir\" does not exist, aborting" if (! (-d $src_dir));
# die 'ERROR: Target directory undefined, aborting' if (! defined($tgt_dir));

Trace::setTraceLevel($lvl);
my $begin = time();
Trace::trace(1, "Re-encoding directory \"$src_dir\" in directory \"$tgt_dir\" in  with profile \"$profile\"\n"); 
VideoTools::encodeAudioDir($src_dir, $tgt_dir, $profile);

my ($s, $m, $h, $day, $foo, $foo) = localtime(time()-$begin);
$h = ($h - 1) + ($day-1) * 24; 
Trace::trace(1, sprintf("Done, total computing time: %02d:%02d:%02d\n", $h, $m, $s));

exit 0;
#------------------------------------------------------------
