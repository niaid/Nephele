#!/usr/bin/env perl

# Andrew's calculate_subsample.pl, copied from Nephele's github repository on
# Jul 6, 2015

use strict;
use Getopt::Long;

my $frac = 0.1; 	# Default fraction of max
GetOptions('f=s' => \$frac, 'fraction_of_max=s' => \$frac);

my $usage = "calculate_subsample.pl [-f/--fraction_of_max] <biom summary output>
Prints to STDOUT with no line-end (so the output can be assigned to a variable).
Example: bash\$ f=\$(calculate_subsample.pl otu_table.summary.txt); echo \$f
";

die $usage unless ($ARGV[0]);
my $input_file = $ARGV[0];
my $max_count = 0;
my $min_count_threshold = 0;
my @good_counts;	# array to store all sample counts that pass the min_count_threshold.
my @bad_samples;		# Array to store all sample counts that don't pass the min_count_threshold

open(FH, "<", $input_file) or die "Can't open $input_file: $!";
my $reading_samples = 0;	# Becomes 1 when we're reading samples
LINE: while(<FH>){		# while(<DATA>){		# DATA for testing
	chomp;
	if (m/Max:/){
		my @line = split(/:\s+/);
		$max_count = $line[-1];
		$min_count_threshold = $max_count * $frac; 
	}
	if (m/sample detail/){
		$reading_samples++;
		next LINE;
	}
	if ($reading_samples){
		my @line = split(/:\s+/);
		my $count = $line[-1];
		if ($count >= $min_count_threshold){
			push @good_counts, $count;
		}
		else {
			push @bad_samples, $_;
		}

	}
	
}
my @sorted_counts = sort {$a <=> $b} @good_counts;
my $subsample_count = int($sorted_counts[0]);
print "$subsample_count";
print STDERR "Max: $max_count\nFraction of Max: $frac\nMin threshold: $min_count_threshold\n";
print STDERR "Subsample count: $subsample_count\n";
print STDERR "Samples removed from the analysis:\n";
print STDERR join "\n", @bad_samples;
print STDERR "\n";
close (FH);

__DATA__

Example input file:

Num samples: 12
Num observations: 492
Total count: 31538
Table density (fraction of non-zero values): 0.227
Table md5 (unzipped): 62b8a91d3d6f51cff9365e9971b8c65c

Counts/sample summary:
 Min: 130.0
 Max: 3787.0
 Median: 2911.000
 Mean: 2628.167
 Std. dev.: 1032.839
 Sample Metadata Categories: None provided
 Observation Metadata Categories: taxonomy

Counts/sample detail:
 SRS021065: 130.0
 SRS020819: 1330.0
 SRS021073: 1835.0
 SRS021117: 2326.0
 SRS020592: 2781.0
 SRS020470: 2858.0
 SRS021109: 2964.0
 SRS020478: 2973.0
 SRS020811: 3226.0
 SRS020649: 3648.0
 SRS020584: 3680.0
 SRS020641: 3787.0
