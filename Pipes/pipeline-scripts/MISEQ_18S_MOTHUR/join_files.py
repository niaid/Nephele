#!/usr/bin/env python

import argparse
from itertools import izip
import os.path

parser = argparse.ArgumentParser(description=
    "Given a .files file, make combined R1, R2, and concatenated .fasta files"
    "with associated .groups and .names.")

parser.add_argument('--input', type=argparse.FileType('r'), required=True, help=
    "Input .files file (tab-delimited, with paired Illumina FASTQ paths.")
parser.add_argument('--prefix', default='', help=
    "Prefix for the paths in the .files input (if the files are not in working "
    "directory).")

parser.add_argument('--num_ambig', type=int, default=8, help=
    "The concatenated output has a string of Ns as padding between reads. This "
    "allows it to work with kmer-based classifiers (e.g. RDP). You must ensure "
    "that the number of Ns is at least the kmer size.")
parser.add_argument('--reverse_r2', action='store_true', help=
    "If specified, give the reverse complement of the R2 in the -2 output.")
parser.add_argument('--quality_offset', type=int, default=33, help=
    "A quality offset for quality scores. Default 33 for Phred+33.") 

parser.add_argument('--r1', type=argparse.FileType('w'), default=None, help=
    "Combined FASTA output for the forward read.")
parser.add_argument('--r1_q', type=argparse.FileType('w'), default=None, help=
    "Combined QUAL output for the forward read.")
parser.add_argument('--r2', type=argparse.FileType('w'), default=None, help=
    "Combined FASTA output for the reverse read.")
parser.add_argument('--r2_q', type=argparse.FileType('w'), default=None, help=
    "Combined QUAL output for the reverse read.")
parser.add_argument('--concat', type=argparse.FileType('w'), default=None, help=
    "Combined FASTA output for the concatenated read pairs.")
parser.add_argument('--group', type=argparse.FileType('w'), required=True, help=
    "Group file for the combined inputs.")

args = parser.parse_args()

# Reformat ID so mothur is happy
def format_id(i):
    return i.split(' ')[0].replace(':', '_')

# Iterate through FASTQ
def fastq_iter(f):
    for record in izip(*[f] * 4): # Read 4 at a time
        read_id = record[0][1:].rstrip()
        seq = record[1].strip()
        qual = record[3].strip()
        assert record[2].strip() == '+'
        yield (read_id, seq, qual)

# Complement IUPAC ambiguity codes
iupac_table = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'M': 'K', 'R': 'Y', 
    'W': 'W', 'S': 'S', 'Y': 'R', 'K': 'M', 'V': 'B', 'H': 'D', 'D': 'H', 
    'B': 'V', 'N': 'N'}
def base_complement(b):
    return iupac_table[b.upper()]

# Reverse-complement a read
def rc(seq):
    return ''.join(base_complement(b) for b in reversed(seq))

# Write to fasta if the file has been specified
def fasta_write(f, name, seq):
    if f is not None:
        f.write('>%s\n%s\n' % (name, seq))

# Translate ASCII-encoded quality scores to the 
def qual_translate(s):
    return ' '.join([str(ord(x) - args.quality_offset) for x in s])

# # Remove extension from file if in the specified list
# def remove_extension(path, extensions):
#     for ext in sorted(extensions, key=len, reverse=True): # Start with largest
#         if path.endswith('.' + ext):
#             return path[0:-(len(ext) + 1)]
#     return path

# Read the .files input
for line in args.input:
    group, r1_path, r2_path = line.strip().split('\t')
    r1_path = os.path.join(args.prefix, r1_path)
    r2_path = os.path.join(args.prefix, r2_path)

    # Iterate through records in pairs of files
    with open(r1_path, 'r') as r1, open(r2_path, 'r') as r2:
        for (r1_id, r1_seq, r1_qual), (r2_id, r2_seq, r2_qual) \
                in izip(fastq_iter(r1), fastq_iter(r2)):
            assert format_id(r1_id) == format_id(r2_id)
            new_id = format_id(r1_id)
            concat = r1_seq + 'N' * args.num_ambig + rc(r2_seq)
            # Write FASTA
            fasta_write(args.r1, new_id, r1_seq)
            fasta_write(args.r2, new_id, 
                rc(r2_seq) if args.reverse_r2 else r2_seq)
            fasta_write(args.concat, new_id, concat)
            # Write QUAL
            fasta_write(args.r1_q, new_id, qual_translate(r1_qual))
            fasta_write(args.r2_q, new_id, qual_translate(r2_qual[::-1])
                if args.reverse_r2 else qual_translate(r2_qual))
            # Write group
            args.group.write('\t'.join([new_id, group]) + '\n')