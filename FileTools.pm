package FileTools;

use File::Basename;
use File::Spec;
use File::Path;

#-------------------------------------------------------
# Return directory contents
#-------------------------------------------------------
sub getDir
{
	my $some_dir = shift;
	my @files;

	printlog("Scanning $some_dir\n");
	
	opendir(DIR, "$some_dir") || die "can't opendir $some_dir: $!";
	my $i = 0;
	foreach my $f (readdir(DIR)) {
		next if ($f eq '.' || $f eq '..');
		$files[$i++] = $f;
	}
	# @files = grep { /^\./ && -f "$some_dir/$_" } readdir(DIR);
	closedir DIR;
	return @files;
}

#------------------------------------------------------------------------------

use File::Find;
my @FileList;

# Returns the list of files from a root directory
# All files (including directories) are returned
# Files are given with absolute path name

sub getFileList
{
  my $rootdir = shift;
  @FileList = ();
  find(\&pushFile, $rootdir);
  return [ @FileList ];
}

sub pushFile()
{
  my $file = $_;
	my $fulldir = $File::Find::name;
	my $fullpath = $File::Find::name;
	$fullpath =~ s/\//\\/g;
	push(@FileList, $fullpath);
}

#------------------------------------------------------------------------------

sub dirnameOKO
{
	my @arr = split("/\\/", $_[0]);
	pop(@arr);
	return join("\\", @arr);
}

sub stripExtension
{
	my $base = shift;
	my @tabext = @_;
	@tabext = ( "[A-Za-z0-9]+" ) if (! @tabext);
  #	$base =~ s/.*\\//;
	foreach my $ext (@tabext) {
		$base =~ s/\.${ext}$//;
	}
	return $base;
}

sub syncDir
{
	my $dir = shift;
	my $ref = shift;
	# print "Checking $dir and $ref\n";
	
	if (! -d $dir) {
		print "$dir is not a directory\n"; return 0;
	} elsif ( ! -d $ref ) {
		print "$ref is not a directory\n"; return 0;
	}
	
	my @dirlist = FileTools::getDir($dir);
	foreach my $file (@dirlist)
	{
	   $file2 = $file3 = $file4 = $ref."\\".basename($file, ("mp3", "m3a", "aac"));
     $file2 .= ".mp3";
     $file3 .= ".m4a";
    $file4 = ".wav";
    
		if (-f $dir."\\".$file && ! (-f $ref."\\".$file || -f $file2 || -f $file3 || -f $file4)) {
			print "DELETE $dir\\$file ($file2)\n";
			unlink $dir."\\".$file;
		} elsif (-d $dir."\\".$file) {
			if (-d $ref."\\".$file) {
				syncDir($dir."\\".$file, $ref."\\".$file);
			} else {
				rmtree( $dir."\\".$file);
				print "DELETEDIR $dir\\$file\n";
			}
		} else {
			print "KEEP $dir\\$file\n";
		}
	}
	print ("End scan\n");
}

sub patchPath
{
  my @srcTab = split(/\\/, shift);
  my @tgtTab = split(/\\/, shift);
  my $i = 0;
  foreach my $word (@tgtTab) {
    $srcTab[$i] = $word;$i++;
  }
	my $path = join("\\", @srcTab);
	# print "New path = $path\n";
	return $path;
}

return 1;