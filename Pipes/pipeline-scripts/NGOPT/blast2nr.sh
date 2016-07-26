#!/bin/bash
BLASTX=/opt/blast-2.2.29+/bin/blastx
NR=/opt/BLAST_NR/nr
PREF=$1
CORES=$2

# running blastx
echo "running blastx"
TZ='America/New_York' date
$BLASTX -db $NR\
        -out $PREF.final.scaffolds.blastn_t4x.txt\
        -query $PREF.final.scaffolds.fasta\
        -num_threads $CORES -outfmt 6

echo "blast step done"
TZ='America/New_York' date
