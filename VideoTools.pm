#!/usr/bin/perl

package VideoTools;

use Trace qw(Trace::trace);
use FileTools;
use File::Path qw(make_path);
use File::Copy;
use File::Basename;
use MP3::Info;
use MP3::Tag;
MP3::Tag->config(write_v24 => 1);

# my $FFMPEG = "D:\\Tools\\ffmpeg\\ffmpeg.exe";
my $FFMPEG = "E:\\Tools\\ffmpeg-20150926-win64\\bin\\ffmpeg.exe";
# my $FFMPEG = "D:\\Tools\\FFmpeg-22508\\ffmpeg.exe";
my $LAME = "E:\\Tools\\lame-3.98.2\\lame.exe";
my $VLC    = 'C:\Program Files\VideoLAN\VLC\vlc.exe';
my $VIRTUALDUB = 'E:\tools\virtualdub-1.8.3\virtualDub.exe';

# Signification of options
# -b : Video bitrate
# -r : Video Framerate
# -a : Video bandwidth
# -vcodec: Video codec
# -s : Video size (can be word like qcif, cif, 4cif, qvga, vga, svga, xga, sxga, wxga, hd480, hd720, hd1080 or WxH)
# -ar: Audio sampling frequency (8k, 16k, 22k, 44k etc...)
# -ab: Audio bitrate
# -acodec: Audio codec
# -bt: Video bitrate tolerance
my $gp3 = "-f 3gp -ac 1 -ar 8000 -ab 12.2k -ps 128 -i_qfactor 3";

my $h263p = "-f 3gp -vcodec h263p";
my $h263 = "-f 3gp -vcodec h263";
my $amr = '-ac 1 -ar 8000 -ab 12.2k -ps 128 -i_qfactor 3';
my $amr2 = '-ac 1 -ar 8000 -ab 12.2k';
my $qcif_fps = "-r 8 -g 40"; # 8 fps, 1 I-Frame every 5 sec
my $cif_fps = "-r 15 -g 75"; # 15 fps, 1 I-Frame every 6 sec
my $qcif = "-r 8 -g 40 -b 43k -maxrate 80k -bufsize 24k -s qcif";
my $cif = " -b 384k -s cif -r 15 -g 75";
my $cif4 = "-r 15 -g 75 -b 1024k -s 704x576";

my $avimp3 = "-f avi -acodec libmp3lame -ab 128k -ac 2 -alang fre -async 25 -vcodec libxvid -r 25";
my $avimp3_64k = "-f avi -acodec libmp3lame -ab 64k -ac 2 -alang fre -async 25 -vcodec libxvid -r 25";
my $iphone = "-f mp4 -ab 64k -async 25 -s 320x208 -vcodec mpeg4 -r 25";
my $avilowmp3 = "-acodec libmp3lame -ab 64k -ac 1 -async 25 -vcodec libxvid -r 25";
my $mp3 = "-f mp3 -acodec libmp3lame -ac 2";

# my $avi_shq_opts = "-flags +ilme+ildct -flags +alt -mbd rd -flags +trell -cmp 2 -subcmp 2 -g 100";
my $avi_shq_opts = "-flags +ilme+ildct -flags +alt -mbd rd -subcmp 2 -g 100";

my %h_profiles = (
	'aac128'        => ['aac', '.m4a', "-c:a libvo_aacenc -vn -b:a 128k"],
	'aac192'        => ['aac', '.m4a', "-c:a libvo_aacenc -vn -b:a 192k"],
	'mp3_128k'       => ['mp3', '.mp3', "-c:a libmp3lame -vn -b:a 128k"],
	'mp3_64k'       => ['mp3', '.mp3', "-c:a libmp3lame -vn -b:a 64k"],
  # 'aacvbr128'       => ['aac', '.m4a', "-c:a libvo_aacenc -vbr 4"],
  # 'aacvbr192'       => ['aac', '.m4a', "-c:a libvo_aacenc -vbr 5"],
	'lame_128k'     => ['mp3', '.mp3', "-q 2 -b 128 --priority 2"],
	'lame_64k'      => ['mp3', '.mp3', "-q 2 -b 64 --priority 2"],
	'lame_32k'      => ['mp3', '.mp3', "-q 5 -b 32 --priority 2"],
	'mp3_96k'        => ['mp3', '.mp3', "$mp3 -ab 96k"],
	'mp3_64k'        => ['mp3', '.mp3', "$mp3 -ab 64k"],
	'mp3_32k'        => ['mp3', '.mp3', "$mp3 -ab 32k"],
	'avi'           => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b 1024k -r 25"],
	'voiture'       => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec mpeg4 -vtag xvid -b 512k -r 25"],
	'avi_d'         => ['avi', '.avi', "-deinterlace -f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b 1024k -r 25"],,
	'video'         => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b 1024k -r 25 -s 640x360"],,
	'audio32'       => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 1 -ab 32k -vcodec copy"],
	'audio64'       => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec copy"],
	'audio96'       => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 96k -vcodec copy"],
	'audio128'      => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec copy"],
	'audio192'      => ['avi', '.avi', "-f avi -acodec libmp3lame -ac 2 -ab 192k -vcodec copy"],

	'avihd'         => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b 4096k -r 50"],	
	#  			'avihd'        => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b 4096k -r 50"],

	'720p'          => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 2048k -r 25 -aspect 16:9  -s 1280x720"],
	'720p_mkv'      => ['mp4', '.mkv',"-acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 2048k -r 25 -aspect 16:9  -s 1280x720"],
	'720p_tv'       => ['mp4', '.mp4',"-f mp4 -deinterlace -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 2048k -r 25 -aspect 16:9  -s 1280x720"],
	'720p_theater'  => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 2048k -r 25 -aspect 221:100  -s 1280x720"],
	'720p3m_theater'  => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 3072k -r 25 -aspect 221:100  -s 1280x720"],
	'720p3m'        => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 3072k -r 25 -aspect 16:9  -s 1280x720"],
	'720p4m'        => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 4096k -r 25 -aspect 16:9  -s 1280x720"],
	'1080p'         => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 192k -vcodec libx264 -b:v 6144k -r 25 -aspect 16:9 -s 1920x1080"],
	'1080p4m'       => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 192k -vcodec libx264 -b:v 4096k -r 25 -aspect 16:9 -s 1920x1080"],
	'1080p8m'       => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 192k -vcodec libx264 -b:v 8192k -r 25 -aspect 16:9 -s 1920x1080"],
	'mp4_1000_96'   => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 96k -vcodec libx264 -b:v 1024k"],
	'mp4_1000'   => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 128k -vcodec libx264 -b:v 1024k"],

	'ipod'          => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 2 -ab 64k -vcodec libx264 -b:v 1536k -r 25 "],
	'apn_canon'     => ['mp4', '.mp4',"-f mp4 -acodec libvo_aacenc -ac 1 -ab 64k -vcodec libx264 -b:v 1024k -r 25 "],

	'720p_avi'      => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libx264 -b:v 4096k -r 25 -s 1280x720"],
	'tv_mp4'        => ['mp4', '.mp4',"-f mp4 -acodec libmp3lame -ac 2 -ab 128k -vcodec libx264 -b:v 1536k -r 25 -s 720x400"],
	'tv_mp4_2M'     => ['mp4', '.mp4',"-f mp4 -acodec libmp3lame -ac 2 -ab 128k -vcodec libx264 -b:v 2048k -r 25 -s 720x400"],
	'tv_mp4_3M'     => ['mp4', '.mp4',"-f mp4 -acodec libmp3lame -ac 2 -ab 128k -vcodec libx264 -b:v 3072k -r 25 -s 720x400"],
	'720p_xvid'     => ['avi', '.avi',"-f avi -deinterlace -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b:v 4096k -r 25 -s 1280x720"],
	'720p_x264'     => ['avi', '.avi',"-f avi -deinterlace -acodec libmp3lame -ac 2 -ab 128k -vcodec libx264 -b:v 4096k -r 25 -s 1280x720"],
	'720p_low'      => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 128k -vcodec libxvid -b:v 2048k -r 25 -s 1280x720"],
	'vob'           => ['vob', '.vob',"-f dvd -acodec ac3 -ac 2 -ab 128k -vcodec mpeg2video -b:v 4096k -r 25 -s 720x576"],
	'iphone'        => ['mp4', '.mp4',"$iphone -b:v 200k"],
	'cartoon'       => ['avi', '.avi','-f avi -acodec libmp3lame -ar 48000 -ac 2 -ab 64k -vcodec libxvid -b:v 800k'],
	'dvd2'          => ['avi', '.avi','-f avi -acodec libmp3lame -ac 2 -ab 96k -vcodec libxvid -b:v 1024k'],
	'cartoonmp4'    => ['avi', '.avi','-f avi -acodec libmp3lame -ar 48000 -ab 64k -b:v 800k'],
	'avi_wmv'       => ['avi', '.avi','-f avi -acodec libmp3lame -vcodec wmv2'],
	'olddvd'        => ['avi', '.avi',"-deinterlace $avimp3 -b:v 1200k $avi_shq_opts"],
	'avi_800_64'    => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec libxvid -b:v 768k"],
	'avi_900_64'    => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec libxvid -b:v 900k"],
	'avi_900_64_d'  => ['avi', '.avi',"-deinterlace -f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec libxvid -b:v 900k"],
	'avi_500_64'    => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 64k -vcodec libxvid -b:v 500k"],
	'dvd800'        => ['avi', '.avi',"-deinterlace $avilowmp3 -b:v 800k $avi_shq_opts"],
	'dvd1500'       => ['avi', '.avi',"$avimp3 -b:v 1536k $avi_shq_opts"],
	'canon'         => ['avi', '.avi',"-acodec libmp3lame -ab 11k -ac 1 -vcodec libxvid -r 25 -b:v 800k -s 640x480"],
	'canon2'        => ['avi', '.avi',"-f avi -b:v 800k -vcodec libxvid -s 640x480"],
	'studio'        => ['avi', '.avi',"-deinterlace $avimp3 -b:v 1200k -s 640x480 $avi_shq_opts -aspect 4:3"],
	'studio_low'    => ['avi', '.avi',"-deinterlace $avilowmp3 -b:v 300k -s 320x240 $avi_shq_opts -aspect 4:3"],
	'dvdlow'        => ['avi', '.avi',"$avilowmp3 -b:v 1024k $avi_shq_opts  -aspect 16:9"],
	'dvdlow_di'     => ['avi', '.avi',"-deinterlace $avilowmp3 -b:v 1024k $avi_shq_opts -aspect 16:9"],
	'mpeg1'         => ['avi', '.avi','-f mpeg1video -sameq -acodec mp3 -b:v 512k'],
	'mpeg1hq'       => ['avi', '.avi','-acodec copy -f mpeg1video -sameq'],
	'mpeg2'         => ['avi', '.avi','-f mpeg2video -sameq -acodec mp3 -b:v 512k'],
	'mpeg4'         => ['avi', '.avi','-f mp4 -aspect 16:9 -b:v 4096k'],
	'mpeg2hq'       => ['avi', '.avi','-acodec copy -f mpeg2video -sameq -b:v 1200k'],
	'mpeg2'         => ['avi', '.avi','-target dvd-pal'],
	'copy'          => ['avi', '.avi','-vcodec copy -acodec copy'],
	'wav'           => ['wav', '.wav','-f wav'],
	'resync'        => ['avi', '.avi',"-f avi -acodec libmp3lame -ac 2 -ab 64k -async 24000 -vcodec copy"],
	
	# Profiles for file format conversion only (no video/audio transcoding)
	'mp4'           => ['mp4', '.mp4', '-c copy'],
	'mkv'           => ['mkv', '.mkv', '-c copy'],
	'avi'           => ['avi', '.avi', '-c copy'],
	# 'wmv'           => ['wmv', '.wmv', '-c copy'],

	# Profiles for file truncation or concatenation only (no video/audio transcoding)
	'direct'        => ['undef', '.undef',"-c copy"],
	'concat'        => ['undef', '.undef','-c copy']

);


sub setFFmpegPath
{
	$FFMPEG = shift;
}

sub getFileProperties
{
	my $videofile = shift;
	my %h_opts;
	#$h_opts{'logfile'} = "C:\\temp\\ffmpeg$$.log";
	#$output = "C:\temp\foo$$.avi";
	
	#Encode the file for 1 second
	$h_opts{'duration'} = '00:00:00.1';
	$h_opts{'logfile'} = "ffmpeg$$.log";
	$output = "foo$$.avi";
	VideoTools::encode($videofile, $output, 'dvd' , \%h_opts, '');
	open (FIN, "<".$h_opts{'logfile'}) || die "Cannot open $h_opts{'logfile'}";
	my $endloop = 0;
	while (<FIN>)
	{
		# print;
		if ( m/Output \#0/ ) { $endloop = 1; }
		next if ($endloop);
		chomp;
		if ( m/\s*Input #0, (\w+),/ ) {
			$prop{'format'} = $1;
			$prop{'text'} .= $_."\n";
			next;
		}

		if ( m/\s*Duration: ([^,]+), start: ([^,]+), bitrate: ([^,]+)\s*$/ ) {
			$prop{'duration'} = $1;
			$prop{'start'} = $2;
			$prop{'bitrate'} = $3;
			$prop{'text'} .= $_."\n";
			next;
		}
		#if ( m/\s*Stream #0.\d: Video: ([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+).*$/ ) {
		if ( m/\s*Stream #0.\d: Video: ([^,]+),\s*(.*)$/ ) {
			$prop{'vcodec'} = $1;
			$prop{'text'} .= $_."\n";
			$rest = $2;
			if ($rest =~ m/,\s*([^,]*yuv[^,]*)/) { $prop{'yuv'} = $1; }
			if ($rest =~ m/,\s*([^,]*\d\dx\d\d[^,]*)/) {
				my $res = $1;
				if ($res =~ m/(\d+x\d+) \[PAR (\d+:\d+) DAR (\d+:\d+)\]/) {
					$prop{'resolution'} = $1; 
					$prop{'par'} = $2;
					$prop{'dar'} = $3;
				} else {
					$prop{'resolution'} = $res;
				}
			}
			if ($rest =~ m/,\s*([^,]*(fps|tbn|tbc)[^,]*)/) { $prop{'fps'} = $1; }
			if ($rest =~ m/,\s*([^,]*kb\/s[^,]*)/) { $prop{'vbitrate'} = $1; }
			if ($rest =~ m/,\s*([^,]*q=\d[^,]*)/) { $prop{'qfactor'} = $1; }
			next;
		}
		if ( m/\s*Stream #0.\d: Audio: ([^,]+),\s*([^,]+),\s*(.+)\s*$/ ) {
			$prop{'acodec'} = $1;
			$prop{'sampling'} = $2;
			my $audio = $3;
			if ($audio =~ m/(mono|stereo|DTS|5.1), (s\d+), (\d+ kb\/s)/i) {
				$prop{'audio_mode'} = $1;
				$prop{'audio_samplingbits'} = $2;
				$prop{'audio_bitrate'} = $3;
			} 
			$prop{'audio'} = $audio;
			$prop{'text'} .= $_."\n";
			next;
		}
		#Duration: 01:32:09.5, start: 0.000000, bitrate: N/A
		#Stream #0.0: Video: h264, yuv420p, 1280x544, 24.39 fps(r)
		#Stream #0.1: Audio: liba52, 48000 Hz, 5:1
	}
	close FIN;
	unlink($output);
	#unlink($h_opts{'logfile'});
	return %prop ;
}




sub encode
{
	my ($srcFile, $tgtFile, $profile, $h_opts, $ffmpeg_opts) = @_;

	die "FATAL ERROR: Undefined encoding profile \"$profile\" \n" if (!defined($h_profiles{$profile}));
	Trace::trace(1,"Encoding $srcFile into $tgtFile in profile $profile: Start\n");

	my $cropping = "";
	foreach my $c ('croptop', 'cropbottom', 'cropleft', 'cropright')
	{
		if ( defined($h_opts->{$c}) && $h_opts->{$c} > 0 ) { $cropping .= " -$c ".$h_opts->{$c}; }
	}

	$ffmpeg_opts .= ' -deinterlace ' if ( defined($h_opts->{'deinterlace'}));
	$ffmpeg_opts .= ' -s '.$h_opts->{'size'} if ( defined($h_opts->{'size'}));
	my $time_window = '';
	$time_window .= " -ss ".$h_opts->{'start'} if defined($h_opts->{'start'});
	$time_window .= " -t ".$h_opts->{'duration'} if defined($h_opts->{'duration'});
	$time_window .= " -to ".$h_opts->{'stop'} if defined($h_opts->{'stop'});

	$overwrite = ($overw eq 'nooverwrite' ? '' : '-y');
	$format =~ tr/A-Z/a-z/;
  my $ext = $tgtFile; $ext =~ s/.*\.//;
	#---------------------------------------------------------------------------
	# Audio tracks management
	#---------------------------------------------------------------------------
	
	my $audio_opts = '';
	# If multiple audio tracks are specified, encode each of them in requested order
	# If not specified, encode only the first audio track found in the source file
	if (defined($h_opts->{'audio_tracks'}))
	{
		my @audio_tracks = split(/[,|: ;]+/, (defined($h_opts->{'audio_tracks'}) ? $h_opts->{'audio_tracks'} : '1,2,3,4,5'));
		my $primary_track = shift(@audio_tracks);
		$audio_opts = " -map 0:0 -map 0:$primary_track"; # Map video track and primary audio track
		# Map additional audio tracks
		foreach my $track (@audio_tracks) { $audio_opts .= " -map 0:$track"; }
		$audio_opts .= " -c:s copy" if ($#audio_tracks >= 0);
#		foreach my $track (@audio_tracks) { $audio_opts .= " $mp3 -alang eng -newaudio -map 0:$track"; }
	}
	
	$tgtDir = FileTools::dirname($tgtFile);
	make_path $tgtDir;

	my $time_opts = '';

	my $src_date = 1;
	my $tgt_date = 0;
	$overw = 'nooverwrite';
	if ( -f $tgtFile && ! -z $tgtFile )
	{
		if ($overw eq 'nooverwrite') {
			Trace::trace("WARNING: File $tgtFile exists, skipping encoding\n");
			return;
		} elsif ($overw eq "modifdate") {
			$src_date = (stat($srcFile))[9];
			$tgt_date = (stat($tgtFile))[9];
		}
	}
	my $aspect;
	if (defined($h_opts->{'aspect'}))
	{
		$aspect = " -aspect ".$h_opts->{'aspect'}; # Map video track and primary audio track
		# Map additional audio tracks
	}
	if ($tgt_date >= $src_date) {
		Trace::trace("WARNING: File $tgtFile is more recent than $srcFile, skipping encoding\n");
	} else {
		my $fmt = $h_profiles{$profile}->[0];
	  my $ext = $h_profiles{$profile}->[1];
  	my $opts = $h_profiles{$profile}->[2];

		my $logfile = $h_opts->{'logfile'};
		if (! defined($logfile) || "$logfile" eq "") {
			$logfile = $tgtFile;
			$logfile =~s/\.[^.]+$/_ffmpeg.log/;
		}
		#$cmd = "$FFMPEG -y -i \"$srcFile\" $cropping $time_window $opts $aspect $ffmpeg_opts \"$tgtFile\""." $audio_opts >> \"$logfile\" 2>>&1";
		$cmd = "$FFMPEG -y -i \"$srcFile\" $ffmpeg_opts $cropping $time_window $opts $aspect $audio_opts \"$tgtFile\""." >> \"$logfile\" 2>>&1";
		Trace::trace(2, "*** Running: $cmd\n");
	#die("Just before encode\n") if ($srcFile =~ m/merge/);
		$out = qx($cmd);
		#system($cmd);
		fixCbrAudio($tgtFile) if ($ext eq "avi" && (! defined($h_opts{'audiofix'}) || $h_opts{'audiofix'} == 1));
	}
	Trace::trace(1, "Encoding of $srcFile into $tgtFile in profile $profile: End\n");
}

# This function just rewrites the AVI header generated by ffmpeg to mark CBR instead of VBR (pb from ffmpeg)

sub fixCbrAudio($file)
{
	Trace::trace(1, "Fixing $file CBR audio: Start\n");
	my $file = shift;
	my $newfile = "$file.cbr.avi";
	$cmd = "$VIRTUALDUB /s \"D:\\tools\\virtualdub165\\cbr_settings.vcf\" /p \"$file\" \"$newfile\" /r /x";
	$out = qx($cmd);
	unlink $file;
	rename($newfile, $file);
	Trace::trace(1, "Fixing $file CBR audio: End\n");
}

sub getProfiles()
{
  return { %h_profiles };
}

sub encodeDir
{
	my ($dirname, $profile, $h_opts, $ffmpeg_opts) = @_;
	Trace::trace(1,"Encode directory $dirname with profile $profile\n");
	my @filelist = FileTools::getDir($dirname);
	my $oldfile;
	my $newfile;
	foreach $oldfile (@filelist)
	{
		next if (! ($oldfile =~ m/\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts)$/i));
		$newfile = "$dirname\\$oldfile";
		$newfile =~s/\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts)$/_recoded.mp4/i;
		$oldfile = "$dirname\\$oldfile";
		#rename($newfile, $oldfile);
		Trace::trace(1,"Encode $oldfile into $newfile profile $profile\n");
		encode($oldfile, $newfile, $profile, $h_opts, $ffmpeg_opts);
	}
}

sub encodeVideoDir
{
  ($src_dir, $tgt_dir, $profile) = @_;
	die "Profile $profile does not exist\n" if (!defined ($h_profiles{$profile}));
  my $begin = time();
  my $filelist = FileTools::getFileList($src_dir);
  my $nbfiles = $#{ $filelist } + 1;
  my $i = 0;
  my $totalduration = time()-$begin;
	my $ext = $video_profiles{$profile}->[1];
	my $fmt = $video_profiles{$profile}->[0];

  Trace::trace(1, "$nbfiles files to encode\n");
  foreach my $srcfile (@{$filelist}) {
	  $i++;
    Trace::trace(1, sprintf("%6d\/%6d - %2d%% ", $i, $nbfiles, $i*100 / $nbfiles));
    my $full_tgt_file = FileTools::patchPath($srcfile, $tgt_dir);	
    $full_tgt_file =~ s/\.(avi|wmv|mp4|3gp|mpg|mpeg|mkv|ts|mts)$/${ext}/;
	  encode($srcfile, $full_tgt_file, $profile, { 'logfile' => "$profile.log", 'overwrite' => 'modifdate' });
  }
}

sub encodeAudioDir
{
  ($src_dir, $tgt_dir, $profile) = @_;
	die "Profile $profile does not exist\n" if (!defined ($h_profiles{$profile}));
  my $begin = time();
  my $filelist = FileTools::getFileList($src_dir);
  my $nbfiles = $#{ $filelist } + 1;
  my $i = 0;
  my $totalduration = time()-$begin;
	my $ext = $h_profiles{$profile}->[1];
	my $fmt = $h_profiles{$profile}->[0];

  Trace::trace(1, "$nbfiles files to encode\n");
  my $fmt = (($nbfiles < 100) ? "%2d\/%2d" :
            ($nbfiles < 1000) ? "%3d\/%3d" :
            ($nbfiles < 10000) ? "%4d\/%4d" :
            ($nbfiles < 100000) ? "%5d\/%5d" :
            "%6d\/%6d" );
  foreach my $srcfile (@{$filelist}) {
	  $i++;
    Trace::trace(1, sprintf("$fmt - %2d%% ", $i, $nbfiles, $i*100 / $nbfiles));
    my $full_tgt_file = FileTools::patchPath($srcfile, $tgt_dir);	
    $full_tgt_file =~ s/\.(mp3|aac|m4a|ac3)$/${ext}/;
	  encodeAudioFile($srcfile, $full_tgt_file, $profile, { 'logfile' => "$profile.log", 'overwrite' => 'modifdate' });
  }
}

sub encodeAudioFile
{
	my ($srcFile, $tgtFile, $profile, $h_opts) = @_;

	my $shortname = $srcFile;
	$shortname =~ s/(.*)(.................................................................)/...$2/;
	Trace::trace(1, sprintf("%-70s", "$shortname: "));
  if (! (-f $srcFile)) {
    Trace::trace (1, "Not a file, skipping\n");
    return;
  }

	my $fmt = $h_profiles{$profile}->[0];
	my $ext = $h_profiles{$profile}->[1];
	my $cmdopts = $h_profiles{$profile}->[2];
  $tgtFile =~ s/\.(mp3|aac|m4a|ac3|avi)$/${ext}/;
	
	Trace::trace(3, "Profile: Format = $fmt, Extension = $ext, Options = $cmdopts\n");
  Trace::trace(3, "Overwrite = ".$h_opts->{'overwrite'}, "\n");
	my $begin = time();
	my $overw = $h_opts->{'overwrite'} || 'nooverwrite';
	$format =~ tr/A-Z/a-z/;

	make_path(FileTools::dirname($tgtFile));
  if (! ($srcFile =~ m/\.(mp3|ac3|aac|m4a|avi)$/i)) {
    Trace::trace (1, "Not an audio file, simple copy\n");
    copy($srcFile, $tgtFile);
    return 1;
  }

	my $src_date = 1;
	my $tgt_date = 0;
	if (-f $tgtFile && ! -z $tgtFile )
	{
		if ($overw eq 'nooverwrite') {
			Trace::trace(1, "Skipped, target file exists");
			Trace::trace(2, " - target file is $tgtFile");
      Trace::trace(1, "\n");
			return 0;
		} elsif ($overw eq 'modifdate') {
			$src_date = (stat($srcFile))[9];
			$tgt_date = (stat($tgtFile))[9];
			Trace::trace(3, "Source file date = ".localtime($src_date)." - Target file date = ".localtime($tgt_date)."\n");
		}
	}
	if ($overw ne 'overwrite' && $tgt_date >= $src_date) {
		Trace::trace(1, "Skipped, target file up to date");
		Trace::trace(2, " - target file is $tgtFile");
    Trace::trace(1, "\n");
		return 2;
	} else {
		my $logfile = $h_opts->{'logfile'};
		if (! defined($logfile)) {
			$logfile = $tgtFile;
			$logfile =~s/\.[^.]+$/_${profile}.log/;
		}
  	$shortname = $tgtFile;
  	$shortname =~ s/(.*)(.................................................................)/...$2/;
  	Trace::trace(1, "--> $shortname:");
		if ($profile =~ m/lame/i) {
		  die "$LAME executable missing\n" unless (-x $LAME);
		  $cmd = "$LAME --mp3input -h \"$srcFile\" \"$tgtFile\" $cmdopts >> \"$logfile\" 2>>&1";
   } else {
      die "$FFMPEG executable missing\n" unless (-x $FFMPEG);
		  $cmd = "$FFMPEG -y -i \"$srcFile\" $cmdopts \"$tgtFile\" >> \"$logfile\" 2>>&1";
    }
    Trace::trace(2, $cmd);
		$out = qx($cmd);
   	copyMp3Tags($srcFile, $tgtFile) if ($fmt eq 'mp3');
		#system($cmd);
	
		my $duration = time()-$begin;
		Trace::trace(1, "Done ($duration s)\n");
		return 1;
	}
}

# This function allows to shift the audio track forward ar backward to resync audio and video
# If $wavDecode = false, then the audio track is shifted without reencoding. This is much faster but does not
#    always work fine. Try this first; if audio is still out for sync, try again with wavDecode = true
# If $wavDecode = true, then the audio tarck is entirely extracted in WAV and reencoded with the video track
#   This is much longer, requires significant disk space to generate the wav file, but works more consistently

sub delay_audio
{
	my ($ifile, $delay, $ofile, $recode) = @_;
	$mapping = "-map 0:0 -map 1:1";
	if ($recode == 1)
	{
		my $wavFile = "$ifile.wav";
		encode($ifile, $wavFile, 'wav', {'audiofix' => 0}, "");
		encode($ifile, $ofile, 'resync', NULL, "-itsoffset $delay -i $wavFile -map 0:0 -map 1:0");
	} else {
		encode($ifile, $ofile, 'copy', NULL, "-itsoffset $delay -i $ifile $mapping");
	}
}

sub delay_video
{
	my ($ifile, $delay, $ofile, $recode) = @_;
	$mapping = "-map 1:0 -map 0:1";
	if ($recode == 1)
	{
		my $wavFile = "$ifile.wav";
		encode($ifile, $wavFile, 'wav', {'audiofix' => 0}, "");
		encode($ifile, $ofile, 'resync', NULL, "-itsoffset $delay -i $wavFile -map 0:0 -map 1:0");
	} else {
		encode($ifile, $ofile, 'copy', NULL, "-itsoffset $delay -i $ifile $mapping");
	}
}

sub concat_simple
{
  $ofile = pop @_;
  
	$cmd = "$FFMPEG -f concat"; # " -y";
  while (my $f = shift @_) {
    #$cmd .= " \"$f\"";
    $txt .= "file '$f'\n";
  }
  open(FOUT, ">$ofile.concat.txt");
  print FOUT $txt;
  close(FOUT);
  $cmd .= " -i $ofile.concat.txt";
  $cmd .= " -c copy \"$ofile\" >> \"$ofile.concat.log\" 2>>&1";
 	Trace::trace(2, "*** Running: $cmd\n");
  $out = qx($cmd);
}

sub merge
{
	my $fmt = pop;
	my $ofile = pop;
	my @ifiles = @_;
	my @tmpfiles;
	my $cmd = '';
	my $merged_file = '';
	trace(1, "Merging files ".join(' ', @ifiles)." into $ofile format $fmt\n");
	foreach my $file (@ifiles)
	{
		$dir = $file;
		$dir =~ s/\\.*$/\\/;
		if ($dir eq $file) {
			$merged_file = "$ofile.merge.mpg"; 
		} elsif ($merged_file eq '') {
			$merged_file = "$dir\\$ofile.merge.mpg";
		}
		$tmpfile = $file;
		$tmpfile =~ s/\.(avi|wmv|mpg)$//i;
		$tmpfile .= "_enc.mpg";
		encode($file, $tmpfile, 'concat', {'audiofix' => 0});
		if ($cmd eq '') {
			$cmd = "copy /Y \"$tmpfile\" /B";
		} else {
			$cmd .= " + \"$tmpfile\" /B";
		}
	}
	$cmd .= " \"$merged_file\" /B";
	print("\n\n$cmd\n\n");
	system($cmd);

	#delay_audio($merged_file, '00:00:06.00', $merged_file."_delay.mpg");
	#encode($merged_file."_delay.mpg", $ofile, $fmt, 'overwrite');
	encode($merged_file, $ofile, $fmt, {} );

	unlink($merged_file);
}


sub concat
{
	my $ofile = pop;
	my @ifiles = @_;
	my $cmd = '';
	my $curext;
	trace(1, "Concatenating files ".join(' ', @ifiles)." into $ofile\n");
	foreach my $ifile (@ifiles)
	{
		if ($ifile =~ m/\.([A-Z0-9]+)$/i) {$ext = $1;}
		print "WARNING: File $ifile does not seem to have a mergeable format (VOB, MPG, MP3)" if (! $ext =~ m/^(mp3|vob|mpg)$/i);
		if (! defined($curext))
			{ $curext = $ext; }
		else
			{ die "Cannot merge files of different formats ($curext, $ext)" if ($ext ne $curext); }
			
		if ($cmd eq '') {
			$cmd = "copy /Y $ifile /B";
		} else {
			$cmd .= " + $ifile /B";
		}
	}
	$cmd .= " $ofile /B";
	print("\n\n$cmd\n\n");
	system($cmd);

}

sub capture
{
	my ($stream, $file, $fmt, $socks) = @_;

	my $cmd = "$VLC $stream";
	$cmd .= " --socks=$socks" if (defined($socks));

	my %vlc_fmt = (
		'mpeg4' => ':sout=#transcode{vcodec=mp4v,vb=512,scale=1,acodec=mp3,ab=64,channels=1}'
	);
	my %output = (
		'mpeg4' => ':duplicate{dst=std{access=file,mux=mp4,'
	);

	$encodefmt = $vlc{$fmt};
	$outputfmt = $output{$fmt};

	$cmd .= " $encodefmt$output".'dst="'.$file.'"}}';

	print("\n\n$cmd\n\n");
	system($cmd);
}

sub dumpDVD
{
	my ($src_dir, $tgtFile) = @_;
	
	if ( -f $tgtFile )
	{
		Trace::trace("WARNING: $tgtFile already exists, skipping dump...\n");
	} else {
		Trace::trace("INFO: Dumping $src_dir into $tgtFile\n");
		if ($src_dir =~ m/^[A-Z]:$/) { $src_dir .= "\\VIDEO_TS"; }
	
		my @filelist = FileTools::getDir($src_dir);
		my @files;
	
		foreach my $file (@filelist)
		{
			next if (! ($file =~ m/\.(vob)$/i));
			push(@files, $src_dir."\\".$file);		
		}
		push(@files, "$tgtFile");
		concat(@files)
	}
}

sub encodeDVD
{
	my ($srcDir, $tgtFile, $profile, $opts, $ffopts) = @_;
	
	dumpDVD($srcDir, $tgtFile);
	Trace::trace("Encoding $tgtFile.vob\n");
	$profile = 'dvd' if (!defined($profile));
	
	my %hcrop;
	my ($width, $height) = (720, 480); # Equivalent to 720x576 in square pixels
	
	$width = $width - $opts->{'cropleft'} - $opts->{'cropright'};
	$height = $height - $opts->{'croptop'} - $opts->{'cropbottom'};
	$ffopts .= "-s ".$width."x".$height;
	
	#my %pass1_opts;
	#foreach my $k (keys %{$opts}) { $pass1_opts{$k} = $opts->{$k} if ($k != 'audio_tracks'); }
	#---------------------------------------------------------------------------
	# Video encoding
	#---------------------------------------------------------------------------
	# Encode first pass to generate log file
	encode("$tgtFile.vob", $tgtFile."_pass1.avi", $profile, $opts, $ffopts." -pass 1/2 -passlogfile \"$tgtFile.log\"")  if ( -z  $tgtFile."_pass1.avi" || ! -f $tgtFile."_pass1.avi" );

	# Encode 2nd pass with optimal quality based on log file
	encode("$tgtFile.vob", $tgtFile."_pass2.avi", $profile, $opts, $ffopts.." -pass 2/2 -passlogfile \"$tgtFile.log\"")  if ( ! -f $tgtFile."_pass2.avi" );

	# Test encode multiple subtitle tracks
	if (0) {
		my $sub_opts = '';
		if (defined($opts->{'subtitle_tracks'})) {
			my @sub_tracks = split(/[,|: ;]+/, $opts->{'subtitle_tracks'});
			foreach my $track (@sub_tracks) { $sub_opts .= " -slang fre -newsubtitle -map 0:$track"; }
		}

		encode("$tgtFile.vob", $tgtFile."_pass2.avi", $vfmt, $audio_opts.$sub_opts, \%hcrop, $ffopts." -pass 2/2 -passlogfile \"$tgtFile.log\" ") if ( -z $tgtFile."_pass2.avi" || ! -f $tgtFile."_pass2.avi" );
	}
}


use constant SEARCH_ALL   => 'all';

my %freedb_searches = (
   artist  => { keywords => [], abbrev => 'I', tagequiv => 'TPE1' },
   title   => { keywords => [], abbrev => 'T', tagequiv => 'TALB' },
   track   => { keywords => [], abbrev => 'K', tagequiv => 'TIT2' },
   rest    => { keywords => [], abbrev => 'R', tagequiv => 'COMM' },
      );

# maps ID3 v2 tag info to WebService::FreeDB info
my %info2freedb = (
   TALB  => 'cdname',
   TPE1  => 'artist',
      );

my %supported_frames = (
   TIT1 => 1,
   TIT2 => 1,
   TRCK => 1,
   TALB => 1,
   TPE1 => 1,
   COMM => 1,
   WXXX => 1,
   TYER => 1,
      );

my @supported_frames = keys %supported_frames;

# my $term = new Term::ReadLine 'Input> '; # global input


sub get_tag
{
 my $file    = shift @_;
 my $upgrade = shift @_;
 my $mp3 = MP3::Tag->new($file);

 return undef unless defined $mp3;

 $mp3->get_tags();

 my $tag = {};

 if (exists $mp3->{ID3v2})
 {
  my $id3v2 = $mp3->{ID3v2};
  my $frames = $id3v2->supported_frames();
  while (my ($fname, $longname) = each %$frames)
  {
   # only grab the frames we know
   next unless exists $supported_frames{$fname};

   $tag->{$fname} = $id3v2->get_frame($fname);
   delete $tag->{$fname} unless defined $tag->{$fname};
   $tag->{$fname} = $tag->{$fname}->{Text} if $fname eq 'COMM';
   $tag->{$fname} = $tag->{$fname}->{URL} if $fname eq 'WXXX';
   $tag->{$fname} = '' unless defined $tag->{$fname};
  }
 }
 elsif (exists $mp3->{ID3v1})
 {
  warn "No ID3 v2 TAG info in $file, using the v1 tag";
  my $id3v1 = $mp3->{ID3v1};
  $tag->{COMM} = $id3v1->comment();
  $tag->{TIT2} = $id3v1->song();
  $tag->{TPE1} = $id3v1->artist();
  $tag->{TALB} = $id3v1->album();
  $tag->{TYER} = $id3v1->year();
  $tag->{TRCK} = $id3v1->track();
  $tag->{TIT1} = $id3v1->genre();

  if ($upgrade && read_yes_no("Upgrade ID3v1 tag to ID3v2 for $file?", 1))
  {
   set_tag($file, $tag);
  }
 }
 else
 {
  warn "No ID3 TAG info in $file, creating it";
  $tag = {
      TIT2 => '',
      TPE1 => '',
      TALB => '',
      TYER => 9999,
      COMM => '',
      };
 }
# print "Got tag ", Dumper $tag
 # if $config->DEBUG();
 return $tag;
}
# }}}
# {{{ set_tag: set a ID3 V2 tag on a file
sub set_tag
{
	my $file = shift @_;
	my $tag  = shift @_;
	my $mp3 = MP3::Tag->new($file);
	#print Dumper $tag;
	my $tags =  $mp3->get_tags();
	my $id3v2;
	my $id3v1;
	
	if (ref $tags eq 'HASH' && exists $tags->{'ID3v2'}) {
		$id3v2 = $tags->{'ID3v2'};
	} else {
		$id3v2 = $mp3->new_tag('ID3v2');
	}

	my %old_frames = %{$id3v2->get_frame_ids()};

	foreach my $fname (keys %$tag)
	{
	 Trace::trace(3, "Copying ID3 Frame = $fname\n");
		$id3v2->remove_frame($fname) if exists $old_frames{$fname};

		if ($fname eq 'WXXX') {
			$id3v2->add_frame('WXXX', 'ENG', 'FreeDB URL', $tag->{WXXX}) ;
		} elsif ($fname eq 'COMM') {
			$id3v2->add_frame('COMM', 'ENG', 'Comment', $tag->{COMM}) ;
		} else {
			$id3v2->add_frame($fname, $tag->{$fname});
		}
	}
	$id3v2->write_tag();

	# Write ID3 Tags V1
	if (ref $tags eq 'HASH' && exists $tags->{'ID3v1'}) {
		$id3v1 = $tags->{'ID3v1'};
	} else {
		$id3v1 = $mp3->new_tag('ID3v1');
	}
	$id3v1->comment($tag->{'COMM'});
	$id3v1->song($tag->{'TIT2'});
	$id3v1->artist($tag->{'TPE1'});
	$id3v1->album($tag->{'TALB'});
	$id3v1->year($tag->{'TYER'});
	$id3v1->track($tag->{'TRCK'});
	$id3v1->genre($tag->{'TIT1'});
	$id3v1->write_tag();
	
	return 0;
}


# {{{ print_tag_info: print the tag info

sub print_tag_info
{
 my $filename = shift @_;
 my $tag      = shift @_;
 my $extra    = shift @_ || 'Track info';

 # argument checking
 return unless ref $tag eq 'HASH';

 print "$extra for '$filename':\n";

 foreach (keys %$tag)
 {
  printf "%10s : %s\n", $_, $tag->{$_};
 }
}

# }}}

# {{{ guess_track_number: guess track number from ID3 tag and file name
sub guess_track_number
{
 my $filename = shift @_;
 my $tag      = shift @_ || return undef;

 $filename = basename($filename);   # directories can contain confusing data

 # first try to guess the track number from the old tag
 if (exists $tag->{TRCK} && contains_word_char($tag->{TRCK}))
 {
  my $n = $tag->{TRCK} + 0;    # fix tracks like 1/10
  return $n;
 }
 elsif ($filename =~ m/([012]?\d).*\.[^.]+$/)
                     # now look for numbers in the filename (0 through 29)
 {
  print "Guessed track number $1 from filename '$filename'\n"
   if $config->DEBUG();
  return $1;
 }

 return undef; # if all else fails, return undef
}
# }}}

# {{{ guess_artist_and_track: guess artist and track from file name
sub guess_artist_and_track
{
 my $filename = shift @_;
 my $artist;
 my $track;

 $filename = basename($filename);   # directories can contain confusing data

 if ($filename =~ m/([^-_]{3,})\s*-\s*(.{3,})\s*\.[^.]+$/)
 {
  print "Guessed artist $1 from filename '$filename'\n"
   if $config->DEBUG();
  $artist = $1;
  $track = $2;
 }

 return ($artist, $track);
}
# }}}
# {{{ make_tag_from_freedb: make the ID3 tag info from a FreeDB entry
sub make_tag_from_freedb
{
 my $disc  = shift @_;
 my $track = shift @_;

 # argument checking
 return undef unless $track =~ m/^\d+$/;

 # note that the user inputs track "1" but WebService::FreeDB gives us that
 # track at position 0, so we decrement $track
 $track--;

 return undef unless exists $disc->{trackinfo};

 return undef unless exists $disc->{trackinfo}->[$track];

 my $track_data = $disc->{trackinfo}->[$track];

 return {
      TIT1 => $disc->{genre},
      TIT2 => $track_data->[0],
      TRCK => $track+1,
      TPE1 => $disc->{artist},
      TALB => $disc->{cdname},
      TYER => $disc->{year},
      WXXX => $disc->{url},
      COMM => $disc->{rest}||'',
   };

}
# }}}

# {{{ contains_word_char: return 1 if the text contains a word character
sub contains_word_char
{
 my $text = shift @_;
 return $text && length $text && $text =~ m/\w/;
}
# }}}

sub copyMp3Tags
{
	my ($ifile, $ofile) = @_;
	Trace::trace(3, " Tagging: $ifile --> $ofile:");

	set_tag($ofile, get_tag($ifile));
	
	Trace::trace(3, " Done\n");
}