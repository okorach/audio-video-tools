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
$me [-a] [-v] [-h] [-g <level>]
   Returns teh available encoding formats (or profiles) available
   -a: Show only audio formats
   -v: Show only video formats
   -g: Trace level

   $me -h                                       (Displays this help and exits)
";
}

my %options;
getopts('avhg:', \%options);
Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $href_formats = VideoTools::getProfiles();
my @keys = keys %$href_formats;

foreach my $k (sort @keys) {
  printf("%-10s => %s\n", $k, $href_formats->{$k}[2]);
}

#------------------------------------------------------------
