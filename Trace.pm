#!/usr/bin/perl

package Trace;
use Exporter 'import';
@EXPORT_OK = qw(getTraceLevel trace traceNoDate);

my $TraceLevel = 1;
my $LastCR = 1;

$| = 1;

sub setTraceLevel
{
  $TraceLevel = shift;
}

sub getTraceLevel
{
  return $TraceLevel;
}

sub trace
{
  my $lvl = shift;
  if ($lvl <= $TraceLevel) {
    if ($LastCR) {
      my ($s, $m, $h, $day, $month, $year) = localtime(time());
      printf("%04d-%02d-%02d %02d:%02d:%02d | ", $year+1900, $month+1, $day, $h, $m, $s);
    }
    print @_ ;
    my $lastChunk = pop @_;
    $LastCR = ($lastChunk =~ m/\n$/);
  }
}

sub traceNoDate
{
  my $lvl = shift;
  if ($lvl <= $TraceLevel) {
    print @_ ;
  }
}