#!/usr/bin/perl

use Getopt::Std;
use VideoTools qw(encode);
use File::Basename;
use Trace qw(trace);
use strict;
use Win32::Console;
Win32::Console::InputCP(1252);
# require ConfigMgr;

my $me = basename($0);


my $overwrite = "";

sub usage
{
	print "
$me [-i <inputfile>] [-o <outputfile>] [-p <profile>] [-r <range>] [-d <duration>] [-x] [-h] \n\
	-i: Input file. Can be a file or a disk drive. In case of a disk drive, this assumes the drives contains a DVD
	-o: Output file. Optional <input>_recoded_<profile> by default
	-p: Output profile: Default value is 2mbps: video MP4 2048k kbps audio AAC 128 kbps
	-a: list of audio tracks to encode
	-r: Range(s) to encode, eg 05:27-1:12:17 the whole file is encoded if nothing specified
	-x: Interactive session to get parameters
	-T/-B/-L/-R: Top/Bottom/Left/Right cropping
	    If only top is specified then bottom is assumed to be cropped the same way
		If only left is specified then right is assumed to be cropped the same way
	-S: Size of the output video (eg -S 640x480)
	-P: Nbr of passes (-P 1 or -P 2). 1 pass by default
	-O: Options: croptop, cropbottom, cropleft, cropright ...
	-f: Specific ffmpeg options
	-k: Keep intermediate files at end
	-g: Trace level
Example:
  $me -s myvideo.avi -t mynewvideo.mp4 -p 720p 
	"
}

my %options;
my $profile;
my %h_opts;
getopts('i:o:p:r:kO:a:xd:T:B:L:R:S:P:f:hg:', \%options);
Trace::setTraceLevel($options{'g'} || 1);
VideoTools::loadProfiles();

if ($options{'h'}) { usage; exit; }

my $ifile = $options{'i'};
trace(3, "Input file = $ifile\n");

if (defined($options{'x'})) {
	print 'Profile ? '; $profile = <STDIN>;
	chomp($profile);
	$profile = 'gen' if ($profile eq '');

	print 'Video bitrate ? '; $h_opts{'video_bitrate'} = <STDIN>;
	chomp($h_opts{'video_bitrate'});
	delete($h_opts{'video_bitrate'}) if ($h_opts{'video_bitrate'} eq '');

	print 'Start ? '; $h_opts{'start'} = <STDIN>;
	chomp($h_opts{'start'});
	delete($h_opts{'start'}) if ($h_opts{'start'} eq '');

	print 'Stop ? '; $h_opts{'stop'} = <STDIN>;
	chomp($h_opts{'stop'});
	delete($h_opts{'stop'}) if ($h_opts{'stop'} eq '');

	print 'Video size WidthXHeight ? '; $h_opts{'size'} = <STDIN>;
	chomp($h_opts{'size'});
	delete($h_opts{'size'}) if ($h_opts{'size'} eq '');

	print 'De-interlace (y) ? '; $h_opts{'deinterlace'} = <STDIN>;
	chomp($h_opts{'deinterlace'});
	delete ($h_opts{'deinterlace'}) if ($h_opts{'deinterlace'} eq 'n');

	print 'Audio bitrate ? '; $h_opts{'audio_bitrate'} = <STDIN>;
	chomp($h_opts{'audio_bitrate'});
	delete($h_opts{'audio_bitrate'}) if ($h_opts{'audio_bitrate'} eq '');
} else {
	$profile = $options{'p'} || '2mbps';
}

my $ofile = VideoTools::getTargetFile($ifile, $profile, $options{'o'});
trace(3, "Output file = $ofile\n");

my $nbpass = ($options{'P'} eq "2" ? 2 : 1);

# my %h_opts = split(/\s+/, $options{'O'});
$h_opts{'audio_tracks'} = $options{'a'} if (defined($options{'a'}));

# Select only a subset of the whole video
my @ranges = VideoTools::getTimeRanges($options{'r'});
if ($#ranges > 0) {
	$h_opts{'start'} = $ranges[0]->{'start'};
	$h_opts{'stop'} = $ranges[0]->{'stop'};
}

# Video options
$h_opts{'croptop'} = $h_opts{'cropbottom'} = $options{'T'} if (defined($options{'T'}));
$h_opts{'cropbottom'} = $options{'B'} if (defined($options{'B'}));
$h_opts{'cropleft'} = $h_opts{'cropright'} = $options{'L'} if (defined($options{'L'}));
$h_opts{'cropright'} = $options{'R'} if (defined($options{'R'}));
$h_opts{'size'} = $options{'S'} if (defined($options{'S'}));


# If the source is a disk drive, then it is assumed to contain a DVD. Dump the DVD into a local file first
my $drive_letter = '';
my $vobfile = $ofile;
$vobfile =~ s/\.[a-zA-Z0-9]+/.vob/;

if ($ifile =~ m/^[a-zA-Z]:$/) {
	$drive_letter = $ifile;
	print "Dumping $drive_letter into \"$vobfile\"\n";
	if ( -f "$vobfile" ) {
		print "$vobfile exists, skipping DVD dump\n";
	}  else {
 		VideoTools::dumpDVD($drive_letter, $vobfile );
	}
	$ifile = $vobfile;
}

my $ffmpeg_opts = $options{'f'};

foreach my $k (keys %h_opts) { print "$k => ", $h_opts{$k}, "\n"; }

my $passOneFile;
if ($nbpass == 1) {
	if (-d $ifile) {
		trace (1,"Single pass encoding of directory \"$ifile\"\n");
		VideoTools::encodeDir($ifile, $profile, \%h_opts, $ffmpeg_opts);
		trace (1,"Single pass encoding of directory \"$ifile\" complete\n");
	} else {
		trace (1,"Single pass encoding of \"$ifile\" into \"$ofile\"\n");
		encode($ifile, $ofile, $profile, \%h_opts, $ffmpeg_opts);
		trace (1,"Single pass encoding of \"$ofile\" complete\n");
	}
} else {
	die "\nERROR: dual pass encoding of directory not supported yet, aborting...\n" if (-d $ifile);

	trace (1, "2 pass encoding of $ifile into $ofile\n");
	if ( -f "$ofile.log-0.log" ) {
		trace (1, "Pass 1 log file $ofile.log exists, skipping pass 1\n");
	} else {
		$passOneFile = FileTools::stripExtension($ofile).".pass1.mp4";
		#$passOneFile = $ofile.".pass1.mp4";
		encode($ifile, $passOneFile, $profile, \%h_opts, $ffmpeg_opts." -pass 1 -passlogfile \"$ofile.log\"");
		trace (1,"First pass encoding of $ofile complete\n");
	}
	encode($ifile, $ofile, $profile, \%h_opts, $ffmpeg_opts." -pass 2 -passlogfile \"$ofile.log\"");
	trace (1,"2nd pass encoding of $ofile complete\n");
}

if (! defined($options{'k'})) {
	trace (1, "Deleting temp files \"$passOneFile\" \"$ofile.log-0.log\" \"$ofile.log-0.log.mbtree\"\n");
	unlink($passOneFile);
	unlink("$ofile.log-0.log");
	unlink("$ofile.log-0.log.mbtree");
	my $logfile = $ofile;
	$logfile =~s/\.[^.]+$/_ffmpeg.log/;
	unlink($logfile);
	$logfile = $passOneFile;
	$logfile =~s/\.[^.]+$/_ffmpeg.log/;
	unlink($logfile);
	if ($drive_letter ne '')
	{
		trace (1,"Deleting temp files $vobfile\n");
		unlink($vobfile);
	}
}
# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
