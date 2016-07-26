#!/bin/bash
# Mothur 18S Pipeline
# Joe Wan
# Based on Mariam's 16S Mothur pipeline for Nephele

# v. 2: Added fallback to entire reference if primers can't be found. Added 
# processors option to chimera.uchime command.
# September 14, 2015

####################
# Helper Functions #
####################

# Helper function that runs mothur given a string containing commands formatted
# like a bash file. This makes the commands more readable.
run_mothur_command () {
    # Take command, remove blank lines and comments, add ';' at end of lines,
    # and then combine all the lines to produce mothur command.
    # The # at beginning tells mothur we are running a command, not a script.
    $MOTHUR "#$(echo "$COMMAND" | egrep -v '^(#|$)' | sed 's/$/;/' | tr '\n' ' ')"
}

#PROCESSORS=`cat /proc/cpuinfo  | grep processor | wc -l`
# read parameters from config file
#cat $1 | sed -e 's/,/=/g' >config.tmp
echo "Pipeline parameters"
echo
while read -r line
do
    echo "$line"
    eval "$line"
done < $1
echo

# download silva files

#########################
# Step 1: Preprocessing #
#########################

# Make the pcr.oligos file using primer inputs. Primers should use valid IUPAC
# ambiguity codes.
#
# User-defined parameters:
#     FORWARD_PRIMER - forward primer used for amplifying the 18S gene
#     REVERSE_PRIMER - reverse primer used for amplifying the 18S gene
#
echo forward$'\t'$FORWARD_PRIMER$'\n'reverse$'\t'$REVERSE_PRIMER > pcr.oligos

# Trim the reference to the desired region of the 18S gene. Use pcr.oligos
# (generated from the user-defined primers) to trim.
#
# DIFFERENCE: Use the new silva.seed_v119.align fsince it contains archaea
# DIFFERENCE: keepprimer=true since sequences have primers
#
# Use seed_119 since it's much smaller (~10x) than nr_119. Later we will trim
# both datasets.
#
# Output File Names:
#     silva.seed_v119.pcr.align
#     silva.seed_v119.bad.accnos
#     silva.seed_v119.scrap.pcr.align
#
$MOTHUR "#pcr.seqs(fasta=silva.seed_v119.align, oligos=pcr.oligos, processors=$PROCESSORS, keepprimer=true)"

# Trim the entire alignment to the primer-bracketed region
#
# Output File Names:
#     silva.trimmed.align
#     silva.seed.trimmed.align
#
# Find primer locations
python find_primers.py --trimmed silva.seed_v119.pcr.align --output primer.positions
START=$(cut -f 1 primer.positions)
END=$(cut -f 2 primer.positions)
# Check if found and trim if needed
if [ "$START" = "?" ]; then
    # Primers not found. Use entire reference (will be slower and less accurate)
    # Fake it: just symlink to the un-trimmed references
    ln -s silva.nr_v119.align silva.trimmed.align
    ln -s silva.seed_v119.align silva.seed.trimmed.align
else
    START=$(expr $START - 1) # I think mothur trims an extra base, so use start - 1
    $MOTHUR "#pcr.seqs(fasta=silva.nr_v119.align, start=$START, end=$END, keepdots=false,  processors=$PROCESSORS)"
    mv silva.nr_v119.pcr.align silva.trimmed.align
    $MOTHUR "#pcr.seqs(fasta=silva.seed_v119.align, start=$START, end=$END, keepdots=false,  processors=$PROCESSORS)"
    mv silva.seed_v119.pcr.align silva.seed.trimmed.align
fi

# Process reads
# -------------

# Combine all samples into files with custom python script.
#
# Output File Names:
#     R1.fasta
#     R1.qual
#     R2.fasta
#     R2.qual
#     concat.fasta
#     rawfile.groups
#
python join_files.py --input rawfile.files --reverse_r2 --quality_offset 33\
    --r1 R1.fasta --r1_q R1.qual --r2 R2.fasta --r2_q R2.qual \
    --concat concat.fasta --group rawfile.groups
cp R1.fasta rawfile.trim.contigs.fasta
cp rawfile.groups rawfile.contigs.groups

# Joins the forward and reverse reads. User provides 'rawfile.files', a file
# with each line in the format (tab-delimited):
# [SAMPLE NAME]    [FORWARD FILE]    [REVERSE FILE]
#
# Output File Names:
#     rawfile.trim.contigs.fasta
#     rawfile.contigs.report
#     rawfile.scrap.contigs.fasta
#     rawfile.contigs.groups
#
$MOTHUR "#make.contigs(file=rawfile.files, processors=$PROCESSORS)"

# Print information about the contigs.
#
# Output File Names:
#     rawfile.trim.contigs.summary
#
$MOTHUR "#summary.seqs(fasta=rawfile.trim.contigs.fasta)"

# Remove bad reads.
#
# User-defined parameters:
#     SCREEN_MAXAMBIG - The maximum number of ambiguous bases ('N') to allow.
#                       Default is 0 (all reads w/ ambig. bases are thrown out).
#
# DIFFERENCE: I removed the maxlength argument, since 18S has diff. variable
# region lengths.
#
# Output File Names:
#     rawfile.trim.contigs.good.fasta
#     rawfile.trim.contigs.bad.accnos
#     rawfile.contigs.good.groups
#
$MOTHUR "#screen.seqs(fasta=rawfile.trim.contigs.fasta, group=rawfile.contigs.groups, maxambig=$SCREEN_MAXAMBIG)"

# Get unique sequences
#
# Output File Names:
#     rawfile.trim.contigs.good.names
#     rawfile.trim.contigs.good.unique.fasta
#
$MOTHUR "#unique.seqs(fasta=rawfile.trim.contigs.good.fasta)"

# Make file with counts of each unique sequence
#
# Output File Names:
#     rawfile.trim.contigs.good.count_table
#
$MOTHUR "#count.seqs(name=rawfile.trim.contigs.good.names, group=rawfile.contigs.good.groups)"



#####################################
# Step 2: Align and clean sequences #
#####################################

# Align our data to the trimmed reference. Trimming the reference speeds up the
# alignment process and results in more accurate alignment.
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.align
#     rawfile.trim.contigs.good.unique.align.report
#     rawfile.trim.contigs.good.unique.flip.accnos
#
$MOTHUR "#align.seqs(fasta=rawfile.trim.contigs.good.unique.fasta, reference=silva.trimmed.align, processors=$PROCESSORS, flip=F)"

# Output information about the sequences.
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.summary
#
$MOTHUR "#summary.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table)"

# Make sure sequences start and end at appropriate points
#
# User-defined parameters:
#     OPTIMIZE_CRITERIA - The percentage of sequences to keep when choosing
#                         start, end, and minlength. Default 90.
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.good.summary
#     rawfile.trim.contigs.good.unique.good.align
#     rawfile.trim.contigs.good.unique.bad.accnos
#     rawfile.trim.contigs.good.good.count_table
#
$MOTHUR "#screen.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table, summary=rawfile.trim.contigs.good.unique.summary, optimize=$OPTIMIZE, criteria=$OPTIMIZE_CRITERIA)"

# Make sure all sequences start and end at the same point in the alignment
#
# Output File Names:
#     rawfile.filter
#     rawfile.trim.contigs.good.unique.good.filter.fasta
#
$MOTHUR "#filter.seqs(fasta=rawfile.trim.contigs.good.unique.good.align, vertical=T, trump=.)"

# Remove duplicate sequences
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.good.filter.count_table
#     rawfile.trim.contigs.good.unique.good.filter.unique.fasta
#
$MOTHUR "#unique.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.fasta, count=rawfile.trim.contigs.good.good.count_table)"

# 'Single-linkage precluster' removes some erroneous sequences and speeds up
# calculations.
#
# User-defined parameters:
#     PRECLUSTER_DIFFS - Cutoff (number of differences) for pre.cluster
#                        According to mothur protocol, should allow 1 difference
#                        for each 100 bp of sequence (so our ~200 bp seqs get 2)
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.count_table
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.*.map
#
$MOTHUR "#pre.cluster(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.fasta, count=rawfile.trim.contigs.good.unique.good.filter.count_table, diffs=$PRECLUSTER_DIFFS)"

# Chimera detection with UCHIME. Default options work well for long amplicons, but
# may be necessary to fine-tune for short amplicons.
#
# TODO: Provide more options here?
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.chimeras
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.accnos
#
$MOTHUR "#chimera.uchime(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta, count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.count_table, dereplicate=t, processors=$PROCESSORS)"

# Check if accnos file has non-0 length
if [ -s rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.accnos ]; then
    # Remove chimeras from our file.
    #
    # Output File Names:
    #     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta
    #
    $MOTHUR "#remove.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta, accnos=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.accnos)"
else
    # Sometimes uchime detects no chimeras. We need to link the files to 'fake' the remove.seqs step.
    ln -s rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta
fi

# Use our trimmed SILVA to classify. Trimming the reference has been shown to
# improve the accuracy of classification (recommended in mothur's SILVA readme)
#
# DIFFERENCE: Here we use SILVA instead of greengenes (like Mariam does) because
# only SILVA contains archaeal and eukaryotic sequences.
#
# Output File Names:
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.nr_v119.wang.taxonomy
#     rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.nr_v119.wang.tax.summary
#
$MOTHUR "#classify.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta, count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table, reference=silva.trimmed.align, taxonomy=silva.nr_v119.tax, cutoff=80, processors=$PROCESSORS)"

# Remove undesirable sequences: for instance, we don't want chloroplasts since
# they are transients derived from food. Users should be able to check which
# groups they want to exclude.
#
# User-defined parameters:
#     REMOVE_LIST - A dash ('-') delimited list of taxon names to remove. User
#                   should be able to check the ones they want (options:
#                   Chloroplast, Mitochondria, unknown, Archaea, Eukaryota) and
#                   include custom names.
#
# Output File Names:
#    rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.nr_v119.wang.pick.taxonomy
#    rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta
#    rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.count_table
#
$MOTHUR "#remove.lineage(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta, count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table, taxonomy=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.nr_v119.wang.taxonomy, taxon=$REMOVE_LIST)"

run_mothur_command "$COMMAND"

# Move files to friendlier locations
ln -sf rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta rawfile.final.fasta
ln -sf rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.count_table rawfile.final.count_table
ln -sf rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.nr_v119.wang.pick.taxonomy rawfile.final.nr_v119.taxonomy

######################
# Step 3: Clustering #
######################

if [ "$REMOVE_SINGLETONS" = true ]; then
    # Remove singletons if necessary to speed up clustering.
    #     Output File Names:
    #     rawfile.final.rare.count_table
    #     rawfile.final.abund.count_table
    #     rare.accnos
    #     abund.accnos
    #     rawfile.final.rare.fasta
    #     rawfile.final.abund.fasta
    $MOTHUR "#split.abund(fasta=rawfile.final.fasta, count=rawfile.final.count_table, cutoff=1, accnos=true)"

    $MOTHUR "#remove.seqs(accnos=rare.accnos, taxonomy=rawfile.final.nr_v119.taxonomy)"

    # Overwrite old links with the new files, which have singletons removed
    ln -sf rawfile.final.abund.count_table rawfile.final.count_table
    ln -sf rawfile.final.abund.fasta rawfile.final.fasta
    ln -sf rawfile.final.nr_v119.pick.taxonomy rawfile.final.nr_v119.taxonomy
fi

# Calculate distances and cluster
# CHANGED: 0.20 -> 0.10 since we're making 0.03 OTUs
COMMAND="
dist.seqs(fasta=rawfile.final.fasta, cutoff=0.10, processors=$PROCESSORS)
cluster(column=rawfile.final.dist, count=rawfile.final.count_table)
"

run_mothur_command "$COMMAND"



# ANALYSIS
# From here, the pipeline is identical to Mariam's pipeline.

#####################################
# Step 4a: Alpha and beta diversity #
#####################################

# Run standard mothur alpha- and beta-diversity analyses.
#
# TODO: Visualize the data
# TODO: Add option to subsample the data using Andrew's script
#
COMMAND="
# Shared table is basis of subsequent analyses
make.shared(list=rawfile.final.an.unique_list.list, count=rawfile.final.count_table, label=0.03)

# Move shared table to friendlier location
system(cp rawfile.final.an.unique_list.shared rawfile.final.otu.shared)

# Get consensus OTU classifications using existing classifications
classify.otu(list=rawfile.final.an.unique_list.list, count=rawfile.final.count_table, taxonomy=rawfile.final.nr_v119.taxonomy, label=0.03, reftaxonomy=silva.nr_v119.tax)

# Make trees indicating community similarity
tree.shared(shared=rawfile.final.otu.shared, calc=thetayc-jclass)

# Distance table for communities, used for AMOVA
dist.shared(shared=rawfile.final.otu.shared, calc=thetayc)

# AMOVA (analysis of molecular variance) detects significant difference between
# treatment groups
amova(phylip=rawfile.final.otu.thetayc.0.03.lt.dist, design=rawfile.design)

# Generate collector's curves showing how richness, diversity, etc. change with
# sampling effort
collect.single(shared=rawfile.final.otu.shared)

# Get single-sample summary statistics
summary.single(shared=rawfile.final.otu.shared, calc=nseqs-coverage-sobs-invsimpson-chao)

# Rarefaction curve (richness vs. sampling effort) with confidence intervals
rarefaction.single(shared=rawfile.final.otu.shared)
"

run_mothur_command "$COMMAND"

if [ "$DO_OTU_ENRICHMENT" = true ]; then
    # Metastats: detect differentially-abundant OTUs
    $MOTHUR "#metastats(shared=rawfile.final.otu.shared, design=rawfile.design)"
fi



#############################################
# Step 4b: Output for LEfSe and Qiime plots #
#############################################

# Make data files used by LEfSe and Qiime
#
# User-provided files:
#     rawfile.design - A design file (same format as the one for Mariam's
#                      Illumina 16S pipeline). Should include the optional field
#                      "Treatment".
#
# User-provided parameters:
#     QIIME_SUBSAMPLE_FRAC - Minimum sample size to include in QIIME's Core
#                            Diversity Analysis, specified as fraction of the
#                            largest sample in the dataset. Data will be
#                            subsampled to the smallest sample's size. Default
#                            is 0.1 (i.e. 10%).
#

if [ "$DO_OTU_ENRICHMENT" = true ]; then
    # Run LEfSe, incorporating information from provided design file
    $MOTHUR "#make.lefse(shared=rawfile.final.otu.shared, design=rawfile.design, constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy, label=0.03)"
fi

# Make the BIOM file, with OTU abundance and taxonomy information
$MOTHUR "#make.biom(shared=rawfile.final.otu.shared, constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy)"

# Using the BIOM package (bundled in QIIME), output human-readable description
# of the BIOM file.
biom summarize-table -i rawfile.final.otu.0.03.biom -o otu_table.biom.summary.txt

if [ "$DO_CORE_DIVERSITY" = true ]; then
    # Sort the samples in the OTU table by treatment
    sort_otu_table.py -i rawfile.final.otu.0.03.biom -o rawfile.final.otu.0.03.sorted.biom -m rawfile.mapping -s TreatmentGroup

    # Use Andrew's script to calculate best subsample size
    sub=$(perl calculate_subsample.pl -f $QIIME_SUBSAMPLE_FRAC otu_table.biom.summary.txt 2> subsampling_summary.txt)

    # Do the standard diversity analyses and plots in the QIIME workflow
    core_diversity_analyses.py -o $PWD/core_diversity -i $PWD/rawfile.final.otu.0.03.sorted.biom -m $PWD/rawfile.mapping -e $sub --parallel --jobs_to_start $PROCESSORS --nonphylogenetic_diversity -c "TreatmentGroup"
fi

if [ "$DO_INTERACTIVE_HEATMAP" = true ]; then
    # Make QIIME's interactive HTML-based heatap
    make_otu_heatmap_html.py -i rawfile.final.otu.0.03.sorted.biom -o OTU_Heatmap/
fi



##################################################
# Step 5: Phylogenetic approach (UniFrac + pcoA) #
##################################################

# Run phylogenetic diversity analysis: instead of using OTUs, use entire trees
# to calculate sample similarity. May be slow for large datasets!
#
# TODO: Visualize the outputs, make trees, calculate phylogenetic diversity
#
COMMAND="
# Make a distance table for sequences for clustering
dist.seqs(fasta=rawfile.final.fasta, output=phylip, processors=$PROCESSORS)

# Use clearcut to construct the phylogenetic tree
clearcut(phylip=rawfile.final.phylip.dist)

# Use unweighted UniFrac to get phylogenetic distances between samples.
# Unweighted UniFrac does not consider abundances in distance calculation.
unifrac.unweighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table, distance=lt, processors=$PROCESSORS, random=F)

# Use weighted UniFrac to get phylogenetic distances between samples.
# Weighted UniFrac weights OTUs by abundance in distance calculation.
unifrac.weighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table, distance=lt, processors=$PROCESSORS, random=F)

# Principal coordinate analysis of the UniFrac distance matrices
pcoa(phylip=rawfile.final.phylip.tre1.unweighted.phylip.dist)
pcoa(phylip=rawfile.final.phylip.tre1.weighted.phylip.dist)
"
run_mothur_command "$COMMAND"



##############################
# Step 6: Phylotype analysis #
##############################

# Run a phylotype analysis: bin the sequences based on the classification at a
# given level (e.g. genus), then use these phylotypes for downstream analysis.
#
# TODO: Give the user option to select the level at which to phylotype
# TODO: alpha diversity, summary stats, PCOA, rarefaction
#
COMMAND="
# Bin sequences into phylotypes so they can be used as OTUs.
phylotype(taxonomy=rawfile.final.nr_v119.taxonomy)

# Make a shared file. The command label=1 means the most specific level
# available in the taxonomy (e.g. species)
make.shared(list=rawfile.final.nr_v119.tx.list, count=rawfile.final.count_table, label=1)

system(cp rawfile.final.nr_v119.tx.shared rawfile.final.phylotype.shared)

# Label the phylotypes with their consensus taxonomy
classify.otu(list=rawfile.final.nr_v119.tx.list, count=rawfile.final.count_table, taxonomy=rawfile.final.nr_v119.taxonomy, label=$PHYLOTYPE_LEVEL)

# Make a tree of sample similarities using phylotype abundance
tree.shared(shared=rawfile.final.phylotype.shared, calc=thetayc-jclass)
"

run_mothur_command "$COMMAND"

