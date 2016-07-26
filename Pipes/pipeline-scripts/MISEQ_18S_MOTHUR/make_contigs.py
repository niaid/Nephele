#!/usr/bin/env python

import argparse
from collections import OrderedDict

parser = argparse.ArgumentParser(description=
    "Given files representing aligned, filtered R1 + R2 sequences, concatenate into"
    "a single (non-continuous) alignment where the non-covered middle region has "
    "been removed. Since sequences have been aligned, assumes R2 is has already been "
    "reverse-complemented.")

parser.add_argument('--silent', action='store_true', help=
    "If specified, do not print to stdout.")

parser.add_argument('--filtered', action='store_true', help=
    "If specified, reads have been filtered in mothur and we should not attempt "
    "to treat them as originating from the same alignment.")

# Input files

parser.add_argument('--r1_fasta', type=argparse.FileType('r'), required=True, help=
    "FASTA file for read 1.")
parser.add_argument('--r1_name', type=argparse.FileType('r'), default=None, help=
    "The .names file representing duplicates for read 1.")
parser.add_argument('--r1_group', type=argparse.FileType('r'), default=None, help=
    "The .groups file for read 1.")
parser.add_argument('--r2_fasta', type=argparse.FileType('r'), required=True, help=
    "FASTA file for read 2.")
parser.add_argument('--r2_name', type=argparse.FileType('r'), default=None, help=
    "The .names file representing duplicates for read 2.")
parser.add_argument('--r2_group', type=argparse.FileType('r'), default=None, help=
    "The .groups file for read 2.")

# Output files

parser.add_argument('--out_fasta', type=argparse.FileType('w'), required=True, help=
    "Output FASTA file.")
parser.add_argument('--out_name', type=argparse.FileType('w'), required=True, help=
    "Output .names file.")
parser.add_argument('--out_group', type=argparse.FileType('w'), required=True, help=
    "Output .groups file.")

args = parser.parse_args()

def verbose_print(s):
    if not args.silent:
        print s

# Helper function: given file f, return an iterator for the FASTA records
def fasta_iter(f):
    name, sequence = None, ''
    while True:
        line = f.readline()
        if line == '' or line[0] == '>':
            if name is not None: # If not first line, yield a record
                yield (name, sequence)
                sequence = ''
            if line == '':
                return
            name = line[1:].rstrip()
        else:
            sequence += line.strip()


# Read the input .name files into ordered dictionaries

verbose_print("\nReading name files...")

r1_names, r2_names = {}, {}

for dictionary, infile in [(r1_names, args.r1_name), (r2_names, args.r2_name)]:
    for line in infile:

        representative, duplicates = line.rstrip('\n').split('\t')
        duplicates = duplicates.split(',')
        for name in duplicates:
            dictionary[name] = representative


# Determine which shared names should appear in the output

verbose_print("Getting shared reads:")

shared_reads = set(r1_names) & set(r2_names)

verbose_print("  Unique to R1: %d / %d" % (len(r1_names) - len(shared_reads), len(r1_names)))
verbose_print("  Unique to R2: %d / %d" % (len(r2_names) - len(shared_reads), len(r2_names)))
verbose_print("  Shared: %d" % len(shared_reads))


# Read through the FASTA to determine boundaries

def f_not_none(f, a, b):
    '''Given a function and two values, return f(a, b) if both a and b are non-None.
    Otherwise return the non-None value if there is one.
    '''
    if a is None:
        return b
    elif b is None:
        return a
    else:
        return f(a, b)

def get_positions(s):
    '''Return positions start, end such that s[start:end-start] = s.lstrip('.').rstrip('.').
    Thus end is the index of the first gap.
    '''
    start = len(s) - len(s.lstrip('.'))
    end = len(s.rstrip('.'))
    return start, end

if not args.filtered:
    r1_positions, r2_positions = [None, None], [None, None]

    verbose_print("\nDetermining portion to keep...")

    for positions, infile in [(r1_positions, args.r1_fasta), (r2_positions, args.r2_fasta)]:
        start, end = None, None
        for name, sequence in fasta_iter(infile):
            if name in shared_reads:
                s, e = get_positions(sequence)
                start = f_not_none(max, start, s)
                end = f_not_none(min, end, e)
        positions[0], positions[1] = start, end
        infile.seek(0) # Rewind file to beginning

    # It's possible our amplicons actually overlap. In that case, adjust the positions: R1 takes
    # precedence.

    if r1_positions[1] > r2_positions[0]:
        r2_positions[0] = r1_positions[1] # Alternatively, we could use the midpoint...

    r1_start, r1_length, r1_end = r1_positions[0], r1_positions[1] - r1_positions[0], \
        r1_positions[1]
    r2_start, r2_length, r2_end = r2_positions[0], r2_positions[1] - r2_positions[0], \
        r2_positions[1]

    verbose_print("  R1: %d to %d" % (r1_start + 1, r1_end)) # Account for 0-indexing
    verbose_print("  R2: %d to %d" % (r2_start + 1, r2_end))


# Determine which contigs need to be made

verbose_print("\nDetermining which contigs need to be made...")

contigs = {} # Maps from (r1_name, r2_name) -> contig_name
new_duplicates = {} # Maps from representative to duplicate list

for name in shared_reads:
    r1_rep = r1_names[name]
    r2_rep = r2_names[name]
    pairing = (r1_rep, r2_rep)
    if pairing not in contigs:
        contigs[pairing] = name
        new_duplicates[name] = [name]
    else:
        contig_rep = contigs[pairing]
        new_duplicates[contig_rep].append(name)

verbose_print("  Unique contigs: %d" % len(contigs))
verbose_print("  Total contigs: %d" % len(shared_reads))

# Write ouput name and group files

verbose_print("\nWriting final name file...")
for representative, duplicates in new_duplicates.iteritems():
    args.out_name.write('%s\t%s\n' % (representative, ','.join(duplicates)))

verbose_print("\nWriting final group file...")
for line in args.r1_group:
    name, group = line.rstrip('\n').split('\t')
    if name in shared_reads:
        args.out_group.write(line)

# Make contigs

# Read R1 into memory; then use it to make contigs

r1_dict = {}
for name, sequence in fasta_iter(args.r1_fasta):
    r1_dict[name] = sequence if args.filtered else sequence[r1_start:r1_length]

# Make dictionary mapping from R2 to the set of contigs containing it

r2_to_contig = {}
for pair, name in contigs.iteritems():
    r2 = pair[1]
    if r2 not in r2_to_contig:
        r2_to_contig[r2] = list()
    r2_to_contig[r2].append((pair[0], name))

# Make contigs

verbose_print('\nWriting contigs...')

for name, sequence in fasta_iter(args.r2_fasta):
    if name in r2_to_contig:
        r2_portion = sequence if args.filtered else sequence[r2_start:r2_length]
        for r1, contig_name in r2_to_contig[name]:
            args.out_fasta.write('>%s\n%s\n' % (contig_name, r1_dict[r1_names[r1]] + r2_portion))

verbose_print('\nDone!')