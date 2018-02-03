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
$me [-i <inputfile>] [-o <outputfile>] [-p <profile>] [-r <range>] [-d] [-x] [-h] \n\
	-i: Input file. Can be a file or a disk drive. In case of a disk drive, this assumes the drives contains a DVD
	-o: Output file. Optional <input>_recoded_<profile> by default
	-p: Output profile: Default value is 2mbps: video MP4 H.264 2048k kbps audio AAC 128 kbps 720p
	-d: deinterlace
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
my $ranges;
my $keeplogs;
my %h_opts;
getopts('i:o:p:r:dcxkO:a:T:B:L:R:S:P:f:hg:', \%options);
Trace::setTraceLevel($options{'g'} || 3);

trace(3, "Command line options:\n");
foreach my $k (keys %options) { trace(3, "\t$k => $options{$k} \n"); }

VideoTools::loadProfiles();

if ($options{'h'}) { usage; exit; }

my $ifile = $options{'i'};
trace(3, "Input file = $ifile\n");

# Video options
$h_opts{'croptop'} = $h_opts{'cropbottom'} = $options{'T'} if (defined($options{'T'}));
$h_opts{'cropbottom'} = $options{'B'} if (defined($options{'B'}));
$h_opts{'cropleft'} = $h_opts{'cropright'} = $options{'L'} if (defined($options{'L'}));
$h_opts{'cropright'} = $options{'R'} if (defined($options{'R'}));
$h_opts{'size'} = $options{'S'} if (defined($options{'S'}));
$h_opts{'deinterlace'} = 1 if (defined($options{'d'}));
$ranges = $options{'r'} if (defined($options{'r'}));
my $keeplogs = 1 if (defined($options{'k'}));
my $mergechunks = 1 if (defined($options{'c'}));

if (defined($options{'x'})) {
	if (defined($options{'p'})) {
		$profile = $options{'p'};
	} else {
		print 'Profile ? '; $profile = <STDIN>;
		chomp($profile);
		$profile = 'gen' if ($profile eq '');
	}
	
	print 'Video bitrate (2048k) ? '; $h_opts{'video_bitrate'} = <STDIN>;
	chomp($h_opts{'video_bitrate'});
	$h_opts{'video_bitrate'} = '2048k' if ($h_opts{'video_bitrate'} eq '');

	if (!defined($ranges)) {
		print ("Range(s) ? "); $ranges = <STDIN>; chomp($ranges);
	}
	if (!defined($h_opts{'size'})) {
		print 'Video size WidthXHeight (1280x720) ? '; $h_opts{'size'} = <STDIN>; chomp($h_opts{'size'});
		$h_opts{'size'} = '1280x720' if ($h_opts{'size'} eq '');
	}
	
	if (!defined($h_opts{'deinterlace'})) {
		print 'De-interlace (y) ? '; $h_opts{'deinterlace'} = <STDIN>; chomp($h_opts{'deinterlace'});
		delete ($h_opts{'deinterlace'}) if ($h_opts{'deinterlace'} eq 'n');
	}
	
	print 'Audio bitrate (128k) ? '; $h_opts{'audio_bitrate'} = <STDIN>; chomp($h_opts{'audio_bitrate'});
	$h_opts{'audio_bitrate'} = '128k' if ($h_opts{'audio_bitrate'} eq '');
} else {
	$profile = $options{'p'} || '2mbps';
}

my $ofilefinal = VideoTools::getTargetFile($ifile, $profile, $options{'o'});
trace(3, "Output file = $ofilefinal\n");

my $nbpass = ($options{'P'} eq "2" ? 2 : 1);

# my %h_opts = split(/\s+/, $options{'O'});
$h_opts{'audio_tracks'} = $options{'a'} if (defined($options{'a'}));

# If the source is a disk drive, then it is assumed to contain a DVD. Dump the DVD into a local file first
my $drive_letter = '';
my $vobfile = $ofilefinal;
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

# Check if only chunks of the whole video must be encoded
my @ranges = VideoTools::getTimeRanges($ranges);
my @filelist;

for (my $i=0; $i <= $#ranges; $i++)
{
	my $ofile;
	delete($h_opts{'start'});
	delete($h_opts{'stop'});
	$h_opts{'start'} = $ranges[$i]->{'start'} if (defined($ranges[$i]->{'start'}));
	$h_opts{'stop'} = $ranges[$i]->{'stop'} if (defined($ranges[$i]->{'stop'}));
	
	my $j = $i+1;
	if ($#ranges > 0) {
		my $ext = VideoTools::getProfileExtension($profile);
		$ofile = FileTools::replaceExtension($ifile, "chunk_$j.$ext");
		push(@filelist, $ofile);
	} else {
		$ofile = $ofilefinal;
	}
	die("Output file \"$ofile\" exists, aborting. Type $me -h for help\n") if (-f $ofile);

	foreach my $k (keys %h_opts) { trace(3, "$k => ", $h_opts{$k}, "\n"); }

	my $passOneFile = FileTools::stripExtension($ofile).".pass1.mp4";
	if ($nbpass == 1) {
		if (-d $ifile) {
			trace (1,"Single pass encoding of directory \"$ifile\"\n");
			VideoTools::encodeDir($ifile, $profile, \%h_opts, $ffmpeg_opts);
			trace (1,"Single pass encoding of directory \"$ifile\" complete\n");
		} else {
			trace (1,"Single pass encoding of \"$ifile\" into \"$ofile\"\n");
			VideoTools::encode($ifile, $ofile, $profile, \%h_opts, $ffmpeg_opts);
			trace (1,"Single pass encoding of \"$ofile\" complete\n");
		}
		if (! $keeplogs) {
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
	} else {
		die "\nERROR: dual pass encoding of directory not supported yet, aborting...\n" if (-d $ifile);
		trace (1, "2 pass encoding of $ifile into $ofile\n");
		if ( -f "$ofile.log-0.log" ) {
			trace (1, "Pass 1 log file $ofile.log exists, skipping pass 1\n");
		} else {
			
			encode($ifile, $passOneFile, $profile, \%h_opts, $ffmpeg_opts." -pass 1 -passlogfile \"$ofile.log\"");
			trace (1,"First pass encoding of $ofile complete\n");
		}
		encode($ifile, $ofile, $profile, \%h_opts, $ffmpeg_opts." -pass 2 -passlogfile \"$ofile.log\"");
		trace (1,"2nd pass encoding of $ofile complete\n");
	}

}

if ($mergechunks && $#ranges > 0)
{
	# Reconcatenate all cuts
	Trace::trace(1,"Concatenating ".join(" + ", @filelist)." => \"$ofilefinal\"\n");
	push(@filelist, $ofilefinal);
	VideoTools::concat_simple(@filelist);
	Trace::trace(1,"Concatenation of \"$ofilefinal\" complete\n");
}


# print '[Enter] to end '; readline STDIN;

#------------------------------------------------------------
