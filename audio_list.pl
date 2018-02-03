#!/usr/bin/perl

use Getopt::Std;
use FileTools;
use VideoTools;
use strict;
# require ConfigMgr;

my $dir = shift;

my $list = FileTools::getFileList($dir);
my $size = $#{ $list };


print("File;Format;Song;Artist;Album;Year;Track;Genre\n");
foreach my $file (@{$list}) {
	next if (-d $file); # Skip directories
	my $format = FileTools::getFileExtension($file);
	$format =~ tr/A-Z/a-z/;
	my ($song, $artist, $album, $year, $track, $genre) = ('', '', '', '', '', '');
	if ($format eq 'mp3') { # skip tags for non MP3 files
		my $tag = VideoTools::get_tag($file);
		($song, $artist, $album, $year, $track, $genre) = ($tag->{'TIT2'}, $tag->{'TPE1'},  $tag->{'TALB'}, $tag->{'TYER'}, $tag->{'TRCK'}, $tag->{'TIT1'});
	}
	print "$file;$format;$song;$artist;$album;$year;$track;$genre\n";
}

#------------------------------------------------------------
