package FileTools;

use strict;
use File::Basename;
use File::Spec;
use File::Path;
use Trace qw(trace);

my $DIR_SEPARATOR = "/";
my $EXT_SEPARATOR = "\.";

#-------------------------------------------------------------------------------
# Return list of files and directories of a given directory
# list is returned in an array
#-------------------------------------------------------------------------------
sub getDir
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $some_dir = shift;

   Trace::trace(2, "Scanning $some_dir\n");
   
   opendir(DIR, "$some_dir") || die "can't opendir $some_dir: $!";

   my @files;
   foreach my $f (readdir(DIR)) {
		push(@files, $f) unless ($f eq '.' || $f eq '..');
   }
   # @files = grep { /^\./ && -f "$some_dir/$_" } readdir(DIR);
   closedir DIR;
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") returns ".join(',',@files)."\n");
   return @files;
}

#------------------------------------------------------------------------------

use File::Find;
my @FileList;

# Returns the list of files from a root directory
# All files (including directories) are returned
# Files are given with absolute path name

#-------------------------------------------------------------------------------
#   getFileList($rootDir)
#-------------------------------------------------------------------------------
sub getFileList
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $rootdir = shift;
   @FileList = ();
   find(\&pushFile, $rootdir);
   return [ @FileList ];
}

#-------------------------------------------------------------------------------
#   pushFile
#-------------------------------------------------------------------------------
sub pushFile()
{
   my $file = $_;
   my $fullpath = $File::Find::name;
   $fullpath =~ s/\//\\/g;
   push(@FileList, $fullpath);
}

#------------------------------------------------------------------------------

sub syncDir
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
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
		my ($file2, $file3, $file4);
      $file2 = $file3 = $file4 = $ref.$DIR_SEPARATOR.basename($file, ("mp3", "m3a", "aac"));
     $file2 .= ".mp3";
     $file3 .= ".m4a";
    $file4 = ".wav";
    
      if (-f $dir.$DIR_SEPARATOR.$file && ! (-f $ref.$DIR_SEPARATOR.$file || -f $file2 || -f $file3 || -f $file4)) {
         print "DELETE $dir\\$file ($file2)\n";
         unlink $dir.$DIR_SEPARATOR.$file;
      } elsif (-d $dir.$DIR_SEPARATOR.$file) {
         if (-d $ref.$DIR_SEPARATOR.$file) {
            syncDir($dir.$DIR_SEPARATOR.$file, $ref.$DIR_SEPARATOR.$file);
         } else {
            rmtree( $dir.$DIR_SEPARATOR.$file);
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
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
  my @srcTab = split(/${DIR_SEPARATOR}/, shift);
  my @tgtTab = split(/${DIR_SEPARATOR}/, shift);
  my $i = 0;
  foreach my $word (@tgtTab) {
    $srcTab[$i] = $word;$i++;
  }
   my $path = join($DIR_SEPARATOR, @srcTab);
   # print "New path = $path\n";
   return $path;
}

sub basename
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $fullpath = shift;
   $fullpath =~ s/\/+$//;
   my @arr = split( /(\\|\/)/, $fullpath);
	my $ret = pop(@arr);
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") returns $ret\n");
   return $ret;
}

sub dirname
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $fullpath = shift;
   $fullpath =~ s/\/+$//;
   my @arr = split( /$DIR_SEPARATOR/, $fullpath);
   pop(@arr);
   my $ret = join($DIR_SEPARATOR, @arr);
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") returns $ret\n");
   return $ret;
}

sub getFileExtension {
   Trace::trace(5, "Calling ".(caller(0))[3]."(".join(',',@_).")\n");
   my $filename = basename(shift);
   my @arr = split( /${EXT_SEPARATOR}/, $filename);
	my $ret = ($#arr == 0 ? undef : pop(@arr));
   Trace::trace(5, "Return ".(caller(0))[3]." => ".$ret."\n");
   return $ret;
}

#-------------------------------------------------------------------------------
#   stripExtension($filename)
#   Returns a filename with the extension suppressed
#-------------------------------------------------------------------------------
sub stripExtension
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $filename = shift;

   my $dirname = dirname($filename);
   my $basename = basename($filename);
   my @arr = split( /\./, $basename);
   Trace::trace(5, "Array = ", join(", ", @arr), "\n");
	my $ret;
   if ($#arr == 0) {
      $ret = $filename;
   } else {
      pop(@arr);
		$ret = $dirname.$DIR_SEPARATOR.join('.', @arr);
   } 
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") returns $ret\n");
   return $ret;
}

#-------------------------------------------------------------------------------
#   changeExtension($filename, $newExtension)
#   Returns a filename with its previous extension replaced by a new one
#-------------------------------------------------------------------------------
sub changeExtension
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $filename = shift;
   my $newExtension = shift;
	$newExtension =~ s/^${EXT_SEPARATOR}//;  # Remove heading . if any

   my $basename = basename($filename);
   my $dirname = dirname($filename);
   my @arr = split( /${EXT_SEPARATOR}/, $filename);
   if ($#arr != 0) {
      pop(@arr);
      unshift (@arr, $dirname);
      $filename = join($DIR_SEPARATOR, @arr);
   } 
   return $filename.$EXT_SEPARATOR.$newExtension;
}

#-------------------------------------------------------------------------------
#   stripExtensionFromList($filename [, @listOfExtensions ])
#   Returns a filename with the extension suppressed
#-------------------------------------------------------------------------------
sub stripExtensionFromList
{
   Trace::trace(5, (caller(0))[3]."(".join(',',@_).") called\n");
   my $base = shift;
   my @tabext = @_;
   @tabext = ( "[A-Za-z0-9]+" ) if (! @tabext);
   foreach my $ext (@tabext) {
      $base =~ s/${EXT_SEPARATOR}${ext}$//;
   }
   return $base;
}

return 1;
