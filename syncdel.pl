#!/usr/bin/perl -w

use Getopt::Std;

require FileTools;

use strict;
# require ConfigMgr;

sub usage
{
	print "syncdel.pl -d <dir> -r <dir> [-h]\n\
	-d: Mandatory parameter: directory to check (and where files may be deleted)
	-r: Mandatory parameter: reference directory for comparison
	-h: This help
	"
}


my %options;
getopts('d:r:h', \%options);

if ($options{'h'}) { usage; exit; }
my $dir = $options{'d'};
my $ref = $options{'r'};

die "Option -d is mandatory, type syncdel.pl -h for help\n" if (! defined($dir));
die "Option -r is mandatory, type syncdel.pl -h for help\n" if (! defined($ref));
die "$dir is not a directory, type syncdel.pl -h for help\n" if (! -d $dir);
die "$ref is not a directory, type syncdel.pl -h for help\n" if (! -d $ref);

FileTools::syncDir($dir, $ref);

#------------------------------------------------------------
