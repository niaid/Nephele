#!/usr/bin/perl
# Author: Martin Dahlo / modified Jacques Dainat
#
# Usage:  perl scriptname.pl <infile> [-a -t <max seconds to search>]
# ex.
# perl scriptname.pl reads.fq
# perl scriptname.pl reads.fq -a
# perl scriptname.pl reads.fq -a -t 90

use warnings;
use strict;
use Getopt::Std;


my $usage = <<EOF;
Usage:  perl scriptname.pl <infile> [-a -t <max seconds to search>]

-a		Advanced mode. Can be used to find exactly which scoring system it is.
-t		Set the max search time in seconds to be used when using -a. Default is 60.
EOF

my $fq = shift or die $usage;

# get flags, if any
getopts('at:');
our($opt_a, $opt_t);
my $adv = $opt_a;
my $time = $opt_t || 999999999;

# open the files
open FQ, "<", $fq or die $!;

if(!$adv){
    # initiate
    my @line;
    my $l;
    my $number;
    
    
    # go thorugh the file
    while(<FQ>){

	# if it is the line before the quality line
	if($_ =~ /^\+/){

	    $l = <FQ>; # get the quality line
	    chomp($l); # remove newline and whitespaces
	    @line = split(//,$l); # divide in chars

	    for(my $i = 0; $i <= $#line; $i++){ # for each char

		$number = ord($line[$i]); # get the number represented by the ascii char

		# check if it is sanger or illumina/solexa, based on the ASCII image at http://en.wikipedia.org/wiki/FASTQ_format#Encoding
		if($number > 74){ # if solexa/illumina
		    print "64"; # 1.5
		    exit;
		}elsif($number < 59){ # if sanger
		    print "33";	      # 1.8
		    exit;
		}
	    }
	}
    }

    die "0";			# 0 implies we can't tell
}


# if the user wants the advanced mode
if($adv){

    # initiate
    my @line;
    my $l;
    my $number;
    my $max = -100;
    my $min = 99999999;
    my $start = time();
    
    # scoring system definitions, according to http://en.wikipedia.org/wiki/FASTQ_format#Encoding 
    # Feel free to add more on your own, following the system of the ones already in here.
    my %systems = (	'Sanger', [33,126], 
			'Solexa', [59,126], 
			'Illumina 1.3+', [64,126], 
			'Illumina 1.5+', [66,126], 
			'Illumina 1.8+', [35,126]);

    my %infoDisplay = ( 'Sanger' => 'Phred+33',
			'Solexa' => 'Phred+64',
			'Illumina 1.3+' => 'Phred+64',
			'Illumina 1.5+'=> 'Phred+64 ',
			'Illumina 1.8+' => 'Phred+33',
			'last' => 'Phred+33');

    my $nb_line =	`awk 'END {print NR}' $fq`;
    my $nb_read = $nb_line/4;
    my $startP=time;
    my $nb_read_checked=0;	

    # go thorugh the file
    while(<FQ>){

	#Display progression
	if ((30 - (time - $startP)) < 0) {
	    my $done = ($nb_read_checked*100)/$nb_read;
	    $done = sprintf ('%.0f', $done);
	    $startP= time;

	}

	# if it is the line before the quality line
	if($_ =~ /^\+/){
	    $nb_read_checked++;
	    $l = <FQ>; # get the quality line
	    chomp($l); # remove newline and whitespaces
	    @line = split(//,$l); # divide in chars

	    for(my $i = 0; $i <= $#line; $i++){ # for each char

		$number = ord($line[$i]); # get the number represented by the ascii char

		# check if the new number is larger or smaller than the previous records  
		if($number < $min){

		    # update min and check how many systems are matching
		    $min = $number;
		    check($min, $max, \%systems, \%infoDisplay);
		}
		if($number > $max){

		    # update max and check how many systems are matching
		    $max = $number;
		    check($min, $max, \%systems, \%infoDisplay);
		}

		# terminate if time is up
		if((time() - $start) >= $time){

		    # print message to screen
		    die "Possible matches:\n".join("\n", check($min, $max, \%systems, \%infoDisplay))."\n";
		}
	    }
	}
    }

    # reached the end of the file without finding a definite answer, without running out of time
    die "Possible matches:".join("\n", check($min, $max, \%systems, \%infoDisplay))."\n";

}




###subroutines

# check how many scoring systems are matching the current max min values
sub check{

    # get arguments
    my ($min, $max, $systems, $infoDisplay) = @_;

    # init
    my @matching;

    # check available systems
    foreach my $key (keys %{$systems}){

	# is it a match?
	if( ($min >= $systems->{$key}[0]) && ($max <= $systems->{$key}[1]) ){

	    # save matching systems
	    my $messageToDisplay = $infoDisplay->{$key};
	    push(@matching, $messageToDisplay);

	}

    }


    # check if only one system matched
    if($#matching == 0){

	# print message to screen
	die "Only one possible match, observed qualities in range [$min,$max]:\n$matching[0]\n";

    }

    # If still not dtermined
    if($#matching >= 1){
	@matching=();
	

	if($min >= $systems->{'Illumina 1.5+'}[0]){
	    my $messageToDisplay = $infoDisplay->{'Illumina 1.5+'};
	    push(@matching, $messageToDisplay);
	}
	elsif($min >= $systems->{'Illumina 1.3+'}[0]){ 
	    my $messageToDisplay = $infoDisplay->{'Illumina 1.3+'};
	    push(@matching, $messageToDisplay);
	}
	elsif($min >= $systems->{'Solexa'}[0]){ 
	    my $messageToDisplay = $infoDisplay->{'Solexa'};
	    push(@matching, $messageToDisplay);
	}
	else{ #could be Illumina 1.8+ or Sanger
	    if($max == $systems->{'Sanger'}[1]){
		my $messageToDisplay = $infoDisplay->{'Sanger'};
		push(@matching, $messageToDisplay);
	    }
	    elsif($max == $systems->{'Illumina 1.8+'}[1]){
		my $messageToDisplay = $infoDisplay->{'Illumina 1.8+'};
		push(@matching, $messageToDisplay);
	    }
	    else{
		my $messageToDisplay = $infoDisplay->{'last'};
		push(@matching, $messageToDisplay);
	    }
	}
	
    }

    # return all matching systems
    return @matching;
}
