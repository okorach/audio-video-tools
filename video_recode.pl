#!/usr/bin/perl

use Getopt::Std;
use VideoTools;
use File::Basename;
use Trace;
use strict;
# require ConfigMgr;

my $me = basename($0);

my $overwrite = "";

sub usage
{
	print "
$me [-s <source>] [-t <target>] [-p <profile>] [-b <begintimestamp>] [-d <duration>] [-h] \n\
	-s: Source. Can be a file or a disk drive. In case of a disk drive, this assumes the drives contains a DVD
	-t: Target file
	-p: Output profile: Default value is dvd: video XVID 1200 kbps audio MP3 128 kbps
	-a: list of audio tracks to encode
	-b: Timestamp of the start of encoding
	-d: Duration to encode
	-T/-B/-L/-R: Top/Bottom/Left/Right cropping
	    If only top is specified then bottom is assumed to be cropped the same way
		If only left is specified then right is assumed to be cropped the same way
	-S: Size of the output video (eg -S 640x480)
	-P: Nbr of passes (-P 1 or -P 2). 2 passes by default
	-o: Options: croptop, cropbottom, cropleft, cropright ...
	-f: Specific ffmpeg options
	-k: Keep intermediate files at end
	-g: Trace level
Example:
  $me -s ironmap.avi -t ironman.mp4 -p 720p 
	"
}

my %options;
getopts('s:t:p:b:ko:a:d:T:B:L:R:S:P:f:hg:', \%options);
Trace::setTraceLevel($options{'g'} || 1);

if ($options{'h'}) { usage; exit; }
my $src_file = $options{'s'};
Trace::trace(3, "Source file = $src_file\n");
my $tgt_file = $options{'t'};
if (! defined($tgt_file) ) {
  $tgt_file = FileTools::stripExtension($src_file);
  #$tgt_file = $src_file;
  $tgt_file .= "_recoded.mp4";
}
Trace::trace(3, "Target file = $tgt_file\n");
my $profile = $options{'p'} || 'dvd';
my $nbpass = 2;
$nbpass = 1 if ($options{'P'} eq "1");

my %h_opts = split(/\s+/, $options{'o'});
$h_opts{'audio_tracks'} = $options{'a'} if (defined($options{'a'}));


# The -d option is mostly used to encode a (small) piece of a video to check the result before launching the complete (long) encoding
if (defined($options{'d'})) {
	$h_opts{'duration'} = $options{'d'};
	# If a short duration is selected, this is probably a sample so start in the middle of the video to check encoding
	if ($options{'d'} < 600) {
		$h_opts{'start'} = 1600;
		$nbpass = 1 if (!defined($options{'P'}));
	}
}
$h_opts{'start'} = $options{'b'} if (defined($options{'b'}));
#$h_opts{'start'} = 1600;
#$h_opts{'duration'} = 60;
#$h_opts{'audio_tracks'} = 1;
# Video cropping options
$h_opts{'croptop'} = $h_opts{'cropbottom'} = $options{'T'} if (defined($options{'T'}));
$h_opts{'cropbottom'} = $options{'B'} if (defined($options{'B'}));
$h_opts{'cropleft'} = $h_opts{'cropright'} = $options{'L'} if (defined($options{'L'}));
$h_opts{'cropright'} = $options{'R'} if (defined($options{'R'}));
$h_opts{'size'} = $options{'S'} if (defined($options{'S'}));


# If the source is a disk drive, then it is assumed to contain a DVD. Dump the DVD into a local file first
my $drive_letter = '';
my $vobfile = $tgt_file;
$vobfile =~ s/\.[a-zA-Z0-9]+/.vob/;

if ($src_file =~ m/^[a-zA-Z]:$/) {
	$drive_letter = $src_file;
	print "Dumping $drive_letter into $vobfile\n";
	if ( -f "$vobfile" ) {
		print "$vobfile exists, skipping DVD dump\n";
	}  else {
 		VideoTools::dumpDVD($drive_letter, $vobfile );
	}
	$src_file = $vobfile;
}

my $ffmpeg_opts = $options{'f'};

foreach my $k (keys %h_opts) { print "$k => ", $h_opts{$k}, "\n"; }

my $passOneFile;
if ($nbpass == 1) {
	Trace::trace (1,"Single pass encoding of $src_file into $tgt_file\n");
	VideoTools::encode($src_file, $tgt_file, $profile, \%h_opts, $ffmpeg_opts);
} else {
	Trace::trace (1, "2 pass encoding of $src_file into $tgt_file\n");
	if ( -f "$tgt_file.log-0.log" ) {
		Trace::trace (1, "Pass 1 log file $tgt_file.log exists, skipping pass 1\n");
	} else {
	  $passOneFile = FileTools::stripExtension($tgt_file).".pass1.mp4";
	  #$passOneFile = $tgt_file.".pass1.mp4";
		VideoTools::encode($src_file, $passOneFile, $profile, \%h_opts, $ffmpeg_opts." -pass 1 -passlogfile \"$tgt_file.log\"");
	}
	VideoTools::encode($src_file, $tgt_file, $profile, \%h_opts, $ffmpeg_opts." -pass 2 -passlogfile \"$tgt_file.log\"");
}

if (! defined($options{'k'})) {
	Trace::trace (1, "Deleting temp files \"$passOneFile\" \"$tgt_file.log-0.log\" \"$tgt_file.log-0.log.mbtree\"\n");
	unlink($passOneFile);
	unlink("$tgt_file.log-0.log");
	unlink("$tgt_file.log-0.log.mbtree");
	my $logfile = $tgt_file;
	$logfile =~s/\.[^.]+$/_ffmpeg.log/;
  unlink($logfile);
	$logfile = $passOneFile;
	$logfile =~s/\.[^.]+$/_ffmpeg.log/;
	unlink($logfile);
	if ($drive_letter ne '')
	{
		Trace::trace (1,"Deleting temp files $vobfile\n");
		unlink($vobfile);
	}
}
# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
