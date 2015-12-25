#!/usr/bin/perl

use Getopt::Std;
use FileTools;

use strict;
# require ConfigMgr;

my $dir = shift;

print("Scanning $dir\n");
my $begin = time();
my $list = FileTools::getFileList($dir);
my $size = $#{ $list };
my $duration = time()-$begin;
print("List of files\n");
foreach my $file (@{$list}) {
  print "$file\n";
}
print("Done, total computing time: $duration s\n");
print("Nbr of files: $size\n");

#------------------------------------------------------------
