#!/usr/bin/perl

use FileTools;
use strict;
use Trace;

sub stripExtension_test
{
	my %h = (
		"/opt/var/myfile.txt" => "/opt/var/myfile",
		"./opt/var/myfile.longext" => "./opt/var/myfile",
		"var/tmp/myfile.mp3" => "var/tmp/myfile",
		"var/tmp/myfile.mp3.aac" => "var/tmp/myfile.mp3",
		"/var/tmp.directory/myfile.aac" => "/var/tmp.directory/myfile",
		"var/tmp.directory/myfile" => "var/tmp.directory/myfile"
	);

	my $testNbr = 0;
	foreach my $key (keys %h) {
		$testNbr++;
		Trace::trace(1, "Test stripExtension:$testNbr - Expected stripExtension(".$key.") = ".$h{$key}."\n");
		my $ret = FileTools::stripExtension($key);
		Trace::trace(1, "Test stripExtension:$testNbr - Actual   stripExtension(".$key.") = $ret\n");
		die "Test stripExtension:$testNbr FAILED" unless $ret eq $h{$key};
		Trace::trace(0, "Test stripExtension:$testNbr - PASSED\n");
	}
	return 1;
}

sub basename_test
{
	my %h = (
		"/opt/var/myfile.txt" => "myfile.txt",
		"./opt/var/myfile.longext" => "myfile.longext",
		"var/tmp/myfile.mp3" => "myfile.mp3",
		"var/tmp/myfile.mp3.aac" => "myfile.mp3.aac",
		"/var/tmp.directory/myfile.aac" => "myfile.aac",
		"var/tmp.directory/myfile" => "myfile",
		"var/tmp.directory/myfile/" => "myfile",
		"var/tmp.directory/myfile////" => "myfile"
	);

	my $testNbr = 0;
	foreach my $key (keys %h) {
		$testNbr++;
		Trace::trace(1, "Test basename:$testNbr - Expected basename(".$key.") = ".$h{$key}."\n");
		my $ret = FileTools::basename($key);
		Trace::trace(1, "Test basename:$testNbr - Actual   basename(".$key.") = $ret\n");
		die "Test basename:$testNbr FAILED" unless $ret eq $h{$key};
		Trace::trace(0, "Test basename:$testNbr - PASSED\n");
	}
	return 1;
}

sub dirname_test
{
	my %h = (
		"/opt/var/myfile.txt" => "/opt/var",
		"./opt/var/myfile.longext" => "./opt/var",
		"var/tmp/myfile.mp3" => "var/tmp",
		"var/tmp/myfile.mp3.aac" => "var/tmp",
		"/var/tmp.directory/myfile.aac" => "/var/tmp.directory",
		"var/tmp.directory/myfile" => "var/tmp.directory",
		"var/tmp.directory/myfile/" => "var/tmp.directory",
		"var/tmp/../tmp/opt/../myfile/" => "var/tmp/../tmp/opt/..",
		"var/tmp.directory/myfile////" => "var/tmp.directory"
	);

	my $testNbr = 0;
	foreach my $key (keys %h) {
		$testNbr++;
		Trace::trace(1, "Test dirname:$testNbr - Expected dirname(".$key.") = ".$h{$key}."\n");
		my $ret = FileTools::dirname($key);
		Trace::trace(1, "Test dirname:$testNbr - Actual   dirname(".$key.") = $ret\n");
		die "Test dirname:$testNbr FAILED" unless $ret eq $h{$key};
		Trace::trace(0, "Test dirname:$testNbr - PASSED\n");
	}
	return 1;
}

Trace::setTraceLevel(shift || 0);
stripExtension_test;
basename_test;
dirname_test;

exit 1;
