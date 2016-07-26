#!/usr/bin/env python

# trim_entire_alignment.py
# ------------------------
# Joe Wan
# v. 3: Fixed bug when checking for empty file.
#
# Helper script for Nephele pipelines. Given a primer-trimmed (pcr.seqs) input 
# and the untrimmed original, trim the entire original alignment to the primer-
# bracketed region. This way, sequences with primer mismatches aren't thrown out
# (which may be desirable, since primers can amplify even when there are 
# mismatches).

import argparse
from collections import defaultdict

parser = argparse.ArgumentParser(description=
    "Given a primer-trimmed (pcr.seqs) input , find the primer-bracketed "
    "region.")
parser.add_argument("--trimmed", type=argparse.FileType('r'), required=True, 
    help="Trimmed alignment (output of mothur's pcr.seqs)")
parser.add_argument("--output", type=argparse.FileType('w'), required=True, 
    help="Output file with alignment positions")
parser.add_argument("--silent", action='store_true',
    help="If specified, don't print anything to stdout.")

args = parser.parse_args()

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

# Helper function: get alignment start and end positions
def get_positions(s):
    # # This iterative approach is slower than the l/rstrip method
    # pos = 1 # 1-indexed!
    # while pos <= len(s) and s[pos - 1] == '.':
    #     pos += 1
    # # Pos is at the first non-'.' character
    # start = pos
    # while pos <= len(s) and s[pos - 1] != '.':
    #     pos += 1
    # # Now, pos is at the (1-indexed) first '.' after the aligned portion
    # end = pos - 1
    # return (start, end)
    
    # Using the faster l/rstrip functions saves a lot of time!
    orig_len = len(s)
    lstrip_len = len(s.lstrip('.'))
    rstrip_len = len(s.rstrip('.'))
    start = orig_len - lstrip_len + 1
    end = rstrip_len
    return (start, end)

def print_verbose(s):
    if not args.silent:
        print s

# Determine best start and end positions
start_positions = defaultdict(lambda: 0)
end_positions = defaultdict(lambda: 0)
num_seqs = 0

print_verbose("Tabulating start and end...")

length = None
warned = False
for name, sequence in fasta_iter(args.trimmed):
    if length is None:
        length = len(sequence)
    if len(sequence) != length:
        if not warned:
            print 'Warning: length of aligned sequences is not the same.'
            warned = True
        length = max(len(sequence), length)
    start, end = get_positions(sequence)
    start_positions[start] += 1
    end_positions[end] += 1
    num_seqs += 1
    if num_seqs % 10000 == 0: print_verbose(num_seqs)
if num_seqs % 10000 != 0: print_verbose(num_seqs)

if num_seqs >= 1:
    print_verbose("\nFinding best positions...")

    indices = range(1, length + 1)
    # Get the starting position with the most matches. Prefer the earliest result
    best_start = max(indices, key=lambda x: start_positions[x])
    if start_positions[best_start] == 0:
        best_start = 1
        print_verbose('Forward primer not found. Using 1 (beginning) as start position.')

    # Get the ending position with the most matches. Prefer the last result
    best_end = max(reversed(indices), key=lambda x: end_positions[x])
    if end_positions[best_end] == 0:
        best_end = length + 1
        print_verbose('Forward primer not found. Using %d (end) as end position.' % best_end)

    print_verbose("\nFound alignment positions.")
    print_verbose("  Start: %d (%d/%d seqs)" % (best_start, 
        start_positions[best_start], num_seqs))
    print_verbose("  End: %d (%d/%d seqs)" % (best_end, 
        end_positions[best_end], num_seqs))

    if best_start > best_end:
        print_verbose('Start (%d) greater than end (%d). Using entire alignment (%d to %d).'
            % (best_start, best_end, 1, length + 1))
        best_start, best_end = 1, length + 1

    args.output.write('%s\t%s\n' % (best_start, best_end))
else:
    print_verbose("Not enough sequences. Using entire alignment.")
    args.output.write('?\t?\n' % (best_start, best_end))