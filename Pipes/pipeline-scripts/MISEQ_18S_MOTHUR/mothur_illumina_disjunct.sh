#!/bin/bash
# Mothur 18S Pipeline
# Joe Wan
# Based on Mariam's 16S Mothur pipeline for Nephele

# v. 2: Added fallback to entire reference if primers can't be found.
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
#$cat $1 | sed -e 's/,/=/g' >config.tmp
#cat config.csv | sed -e 's/,/=/g' >config.tmp
echo "Pipeline parameters"
while read -r line
do
    echo "$line"
    eval "$line"
done < $1
echo

# download silva files


#symlink silva dbs
ln -s /home/ubuntu/ref_dbs/silva/SILVA_SEED.v123.fasta silva.seed_v123.align
ln -s /home/ubuntu/ref_dbs/silva/silva.seed_v123.tax silva.seed_v123.tax
ln -s /home/ubuntu/ref_dbs/silva/silva.nr_v123.align silva.nr_v123.align
ln -s /home/ubuntu/ref_dbs/silva/silva.nr_v123.tax silva.nr_v123.tax


#########################
# Step 1: Preprocessing #
#########################

# Process the reference file
# --------------------------

# Make the oligos files using primer inputs. Primers should use valid IUPAC
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
# DIFFERENCE: Use the new silva.seed_v123.align fsince it contains archaea
# DIFFERENCE: keepprimer=true since sequences have primers
#
# Use seed_119 since it's much smaller (~10x) than nr_119. Later we will trim
# both datasets.
#
# Output File Names:
#     silva.seed_v123.pcr.align
#     silva.seed_v123.bad.accnos
#     silva.seed_v123.scrap.pcr.align
#
$MOTHUR "#pcr.seqs(fasta=silva.seed_v123.align, oligos=pcr.oligos, processors=$PROCESSORS, keepprimer=true)"

# Trim the entire alignment to the primer-bracketed region
#
# Output File Names:
#     silva.trimmed.align
#     silva.seed.trimmed.align
#
# Find primer locations
python find_primers.py --trimmed silva.seed_v123.pcr.align --output primer.positions
START=$(cut -f 1 primer.positions)
END=$(cut -f 2 primer.positions)
# Check if found and trim if needed
if [ "$START" = "?" ]; then
    # Primers not found. Use entire reference (will be slower and less accurate)
    # Fake it: just symlink to the un-trimmed references
    ln -s silva.nr_v123.align silva.trimmed.align
    ln -s silva.seed_v123.align silva.seed.trimmed.align
else
    START=$(expr $START - 1) # I think mothur trims an extra base, so use start - 1
    $MOTHUR "#pcr.seqs(fasta=silva.nr_v123.align, start=$START, end=$END, keepdots=false,  processors=$PROCESSORS)"
    mv silva.nr_v123.pcr.align silva.trimmed.align
    $MOTHUR "#pcr.seqs(fasta=silva.seed_v123.align, start=$START, end=$END, keepdots=false,  processors=$PROCESSORS)"
    mv silva.seed_v123.pcr.align silva.seed.trimmed.align
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

if [ "$OTU_MODE" = "masked" ] || [ "$FILTER_BOTH_READS" = "true" ]; then
    READ_PROCESSING_LIST="R1 R2"
    echo "Processing both reads."
else
    READ_PROCESSING_LIST=$OTU_MODE
    echo "Only processing $OTU_MODE"
fi

for PREFIX in $READ_PROCESSING_LIST; do
    # Make our own copy of the groups file
    cp rawfile.groups $PREFIX.groups

    # Print information about the contigs.
    #
    # Output File Names:
    #     $PREFIX.summary
    #
    $MOTHUR "#summary.seqs(fasta=$PREFIX.fasta)"

    # Remove low-quality reads.
    #
    # User-defined parameters:
    #     TRIM_MAXAMBIG - The maximum number of ambiguous bases ('N') to allow.
    #                     Default is 0 (all reads w/ ambig. bases are thrown out).
    #     QAVERAGE - The minimum average quality for a sequence to be retained.
    #                Default is 25 (may be too lenient).
    #
    # DIFFERENCE: I removed the maxlength argument, since 18S has diff. variable
    # region lengths.
    #
    # Output File Names:
    #     $PREFIX.trim.fasta
    #     $PREFIX.scrap.fasta
    #
    $MOTHUR "#trim.seqs(fasta=$PREFIX.fasta, qfile=$PREFIX.qual, maxambig=$TRIM_MAXAMBIG, qaverage=$QAVERAGE, processors=$PROCESSORS)"

    # Trim.seqs doesn't take a groups input (since it's supposed to be run on
    # un-multiplexed samples), so we need to re-make our group file.
    #
    # Output File Names:
    #     $PREFIX.pick.groups
    #
    $MOTHUR "#list.seqs(fasta=$PREFIX.trim.fasta); get.seqs(group=$PREFIX.groups, accnos=$PREFIX.trim.accnos)"

    # Move the groups file so its name appropriately matches
    mv $PREFIX.pick.groups $PREFIX.trim.groups

    # Get unique sequences
    #
    # Output File Names:
    #     $PREFIX.trim.names
    #     $PREFIX.trim.unique.fasta
    #
    $MOTHUR "#unique.seqs(fasta=$PREFIX.trim.fasta)"

done

#####################################
# Step 2: Align and clean sequences #
#####################################

# Run on all necessary files
for PREFIX in $READ_PROCESSING_LIST; do
    # Align our data to the trimmed reference. Trimming the reference speeds up the
    # alignment process and results in more accurate alignment.
    #
    # Output File Names:
    #     $PREFIX.trim.contigs.good.unique.align
    #     $PREFIX.trim.contigs.good.unique.align.report
    #     $PREFIX.trim.contigs.good.unique.flip.accnos
    #
    $MOTHUR "#align.seqs(fasta=$PREFIX.trim.unique.fasta, reference=silva.trimmed.align, processors=$PROCESSORS, flip=F)"

    # Output information about the sequences.
    #
    # Output File Names:
    #     $PREFIX.trim.unique.summary
    #
    $MOTHUR "#summary.seqs(fasta=$PREFIX.trim.unique.align, name=$PREFIX.trim.names)"

    # Make sure sequences start and end at appropriate points
    #
    # User-defined parameters:
    #     OPTIMIZE_CRITERIA - The percentage of sequences to keep when choosing
    #                         start, end, and minlength. Default 90.
    #
    # Output File Names:
    #     $PREFIX.trim.unique.good.summary
    #     $PREFIX.trim.unique.good.align
    #     $PREFIX.trim.unique.bad.accnos
    #     $PREFIX.trim.good.names
    #     $PREFIX.trim.good.groups
    #
    $MOTHUR "#screen.seqs(fasta=$PREFIX.trim.unique.align, name=$PREFIX.trim.names, group=$PREFIX.trim.groups, summary=$PREFIX.trim.unique.summary, optimize=$OPTIMIZE, criteria=$OPTIMIZE_CRITERIA)"
    # OLD VERSION
    # $MOTHUR "#screen.seqs(fasta=$PREFIX.trim.unique.align, name=$PREFIX.trim.names, group=$PREFIX.trim.groups, summary=$PREFIX.trim.unique.summary, optimize=start-end-minlength, criteria=$OPTIMIZE_CRITERIA)"

    # Make sure all sequences start and end at the same point in the alignment
    #
    # Output File Names:
    #     $PREFIX.filter
    #     $PREFIX.trim.unique.good.filter.fasta
    #
    $MOTHUR "#filter.seqs(fasta=$PREFIX.trim.unique.good.align, vertical=T, trump=.)"

    # Remove duplicate sequences
    #
    # Output File Names:
    #     $PREFIX.trim.unique.good.filter.names
    #     $PREFIX.trim.unique.good.filter.unique.fasta
    #
    $MOTHUR "#unique.seqs(fasta=$PREFIX.trim.unique.good.filter.fasta, name=$PREFIX.trim.good.names)"

    # 'Single-linkage precluster' removes some erroneous sequences and speeds up
    # calculations.
    #
    # User-defined parameters:
    #     PRECLUSTER_DIFFS - Cutoff (number of differences) for pre.cluster
    #                        According to mothur protocol, should allow 1 difference
    #                        for each 100 bp of sequence (so our ~200 bp seqs get 2)
    #
    # Output File Names:
    #     $PREFIX.trim.unique.good.filter.unique.precluster.fasta
    #     $PREFIX.trim.unique.good.filter.unique.precluster.names
    #     $PREFIX.trim.unique.good.filter.unique.precluster.*.map
    #
    $MOTHUR "#pre.cluster(fasta=$PREFIX.trim.unique.good.filter.unique.fasta, name=$PREFIX.trim.unique.good.filter.names, group=$PREFIX.trim.good.groups, diffs=$PRECLUSTER_DIFFS)"

    # Chimera detection with UCHIME. Default options work well for long amplicons, but
    # may be necessary to fine-tune for short amplicons.
    #
    # TODO: Provide more options here?
    #
    # Output File Names:
    #     $PREFIX.trim.unique.good.filter.unique.precluster.uchime.chimeras
    #     $PREFIX.trim.unique.good.filter.unique.precluster.uchime.accnos
    #
    $MOTHUR "#chimera.uchime(fasta=$PREFIX.trim.unique.good.filter.unique.precluster.fasta, name=$PREFIX.trim.unique.good.filter.unique.precluster.names, group=$PREFIX.trim.good.groups, dereplicate=t, processors=$PROCESSORS)"

    # Check if accnos file has non-0 length
    if [ -s $PREFIX.trim.unique.good.filter.unique.precluster.uchime.accnos ]; then
        # Remove chimeras from our file.
        #
        # Output File Names:
        #     $PREFIX.trim.unique.good.filter.unique.precluster.pick.names
        #     $PREFIX.trim.unique.good.filter.unique.precluster.pick.fasta
        #     $PREFIX.trim.good.pick.groups
        #
        $MOTHUR "#remove.seqs(fasta=$PREFIX.trim.unique.good.filter.unique.precluster.fasta, name=$PREFIX.trim.unique.good.filter.unique.precluster.names, group=$PREFIX.trim.good.groups, accnos=$PREFIX.trim.unique.good.filter.unique.precluster.uchime.accnos)"
    else
        # Sometimes uchime detects no chimeras. We need to link the files to 'fake' the remove.seqs step.
        ln -s $PREFIX.trim.unique.good.filter.unique.precluster.fasta $PREFIX.trim.unique.good.filter.unique.precluster.pick.fasta
        ln -s $PREFIX.trim.unique.good.filter.unique.precluster.names $PREFIX.trim.unique.good.filter.unique.precluster.pick.names
        ln -s $PREFIX.trim.good.groups $PREFIX.trim.good.pick.groups
    fi

    # Move files to friendlier locations
    ln -s $PREFIX.trim.unique.good.filter.unique.precluster.pick.fasta $PREFIX.clean.fasta
    ln -s $PREFIX.trim.unique.good.filter.unique.precluster.pick.names $PREFIX.clean.names
    ln -s $PREFIX.trim.good.pick.groups $PREFIX.clean.groups
done

########################
# Step 3a: Classifying #
########################

# Classify and remove undesirable reads. Classification should be done with a
# concatenated file (R1 + NNNNNNNN + R2_rc).

if [ "$OTU_MODE" = "masked" ]; then
    python make_contigs.py --filtered \
        --r1_fasta R1.clean.fasta --r1_name R1.clean.names --r1_group R1.clean.groups \
        --r2_fasta R2.clean.fasta --r2_name R2.clean.names --r2_group R2.clean.groups \
        --out_fasta masked.fasta  --out_name masked.names  --out_group masked.groups

    # Use our trimmed SILVA to classify. Trimming the reference has been shown to
    # improve the accuracy of classification (TODO: citation)
    #
    # DIFFERENCE: Here we use SILVA instead of greengenes because
    # only SILVA contains archaea.
    #
    # User-provided parameters:
    #     CLASSIFY_CONFIDENCE - Confidence cutoff for the mothur classifier; default
    #                           is 80.
    #
    # Output File Names:
    #     masked.nr_v123.wang.taxonomy
    #     masked.nr_v123.wang.tax.summary
    #
    $MOTHUR "#classify.seqs(fasta=masked.fasta, group=masked.groups, reference=silva.trimmed.align, taxonomy=silva.nr_v123.tax, cutoff=$CLASSIFY_CONFIDENCE, processors=$PROCESSORS)"

    # Remove undesirable sequences: for instance, we don't want chloroplasts since
    # they are derived from food. Users should be able to check which groups they
    # want to exclude. We remove from the file we'll use to make OTUs.
    #
    # User-defined parameters:
    #     REMOVE_LIST - A dash ('-') delimited list of taxon names to remove. User
    #                   should be able to check the ones they want (options:
    #                   Chloroplast, Mitochondria, unknown, Archaea, Eukaryota) and
    #                   include custom names.
    #
    # Output File Names:
    #    masked.nr_v123.wang.pick.taxonomy
    #    masked.pick.names
    #    masked.pick.fasta
    #    masked.pick.groups
    $MOTHUR "#remove.lineage(taxonomy=masked.nr_v123.wang.taxonomy, name=masked.names, group=masked.groups, fasta=masked.fasta, taxon=$REMOVE_LIST)"

    # Link files
    ln -s masked.nr_v123.wang.pick.taxonomy final.taxonomy
    ln -s masked.pick.names final.taxonomy.names # Same file, but pipeline uses a copy b/c taxonomy might not correspond
    ln -s masked.pick.fasta final.fasta
    ln -s masked.pick.groups final.groups
    ln -s masked.pick.names final.names
else
    OTU_INPUT=$OTU_MODE.clean

    # To make our concatenated file match our current name/group files, first
    # extract the IDs (i.e. accnos) of the reads in the read we've chosen to make
    # OTUs.
    #
    # Output File Names:
    #     $OTU_INPUT.accnos
    #
    $MOTHUR "#list.seqs(name=$OTU_INPUT.names)"

    # Extract those sequences from the concatenated classifying input.
    #
    # Output File Names:
    #     concat.pick.fasta
    #
    $MOTHUR "#get.seqs(fasta=concat.fasta, accnos=$OTU_INPUT.accnos)"

    # Get unique sequences for concatenated fasta
    #
    # Output File Names:
    #     concat.pick.unique.fasta
    #     concat.pick.names
    #
    $MOTHUR "#unique.seqs(fasta=concat.pick.fasta)"

    # Use our trimmed SILVA to classify. Trimming the reference has been shown to
    # improve the accuracy of classification (TODO: citation)
    #
    # DIFFERENCE: Here we use SILVA instead of greengenes because
    # only SILVA contains archaea.
    #
    # User-provided parameters:
    #     CLASSIFY_CONFIDENCE - Confidence cutoff for the mothur classifier; default
    #                           is 80.
    #
    # Output File Names:
    #     concat.pick.unique.nr_v123.wang.taxonomy
    #     concat.pick.unique.nr_v123.wang.tax.summary
    #
    $MOTHUR "#classify.seqs(fasta=concat.pick.unique.fasta, group=$OTU_INPUT.groups, reference=silva.trimmed.align, taxonomy=silva.nr_v123.tax, cutoff=$CLASSIFY_CONFIDENCE, processors=$PROCESSORS)"

    # Remove undesirable sequences: for instance, we don't want chloroplasts since
    # they are derived from food. Users should be able to check which groups they
    # want to exclude. We remove from the file we'll use to make OTUs.
    #
    # User-defined parameters:
    #     REMOVE_LIST - A dash ('-') delimited list of taxon names to remove. User
    #                   should be able to check the ones they want (options:
    #                   Chloroplast, Mitochondria, unknown, Archaea, Eukaryota) and
    #                   include custom names.
    #
    # Output File Names:
    #    concat.pick.unique.nr_v123.wang.pick.taxonomy
    #    concat.pick.pick.names
    #
    $MOTHUR "#remove.lineage(taxonomy=concat.pick.unique.nr_v123.wang.taxonomy, name=concat.pick.names, taxon=$REMOVE_LIST)"

    # Move file to friendlier location
    ln -s concat.pick.unique.nr_v123.wang.pick.taxonomy final.taxonomy
    ln -s concat.pick.pick.names final.taxonomy.names # Taxonomy uses a different names file!

    # The taxonomy file and its namefile don't correspond with other files. Thus we
    # have to remove lineages in the taxonomy, then get the corresponding sequences
    # in the clean files in subsequent steps.
    #
    # Output File Names:
    #    $OTU_INPUT.pick.fasta
    #    $OTU_INPUT.pick.groups
    #    $OTU_INPUT.pick.names
    #
    $MOTHUR "#list.seqs(name=final.taxonomy.names); get.seqs(fasta=$OTU_INPUT.fasta, group=$OTU_INPUT.groups, name=$OTU_INPUT.names, accnos=final.taxonomy.accnos, dups=false)"

    # Move files to friendlier locations
    ln -s $OTU_INPUT.pick.fasta final.fasta
    ln -s $OTU_INPUT.pick.groups final.groups
    ln -s $OTU_INPUT.pick.names final.names

fi

#######################
# Step 3b: Clustering #
#######################

if [ "$REMOVE_SINGLETONS" = true ]; then
    # Remove singletons if necessary to speed up clustering.
    #     Output File Names:
    #     final.rare.names
    #     final.abund.names
    #     final.rare.accnos
    #     final.abund.accnos
    #     final.rare.fasta
    #     final.abund.fasta
    $MOTHUR "#split.abund(fasta=final.fasta, name=final.names, cutoff=1, accnos=true)"
    $MOTHUR "#list.seqs(name=final.abund.names)" # Need this because the output of split.abund has only uniques
    $MOTHUR "#get.seqs(accnos=final.abund.accnos, dups=false, group=final.groups)"
    $MOTHUR "#get.seqs(accnos=final.abund.accnos, dups=false, taxonomy=final.taxonomy, name=final.taxonomy.names)"

    # Overwrite old links with the new files, which have singletons removed
    ln -sf final.abund.fasta final.fasta
    ln -sf final.abund.names final.names
    ln -sf final.pick.groups final.groups
    ln -sf final.pick.taxonomy final.taxonomy
    ln -sf final.taxonomy.pick.names final.taxonomy.names
fi

# Calculate distances and cluster

# Calculate a distance matrix for the sequences.
# CHANGED: 0.20 -> 0.10 since we're making 0.03 OTUs
#
# Output File Names:
#     final.dist
#
$MOTHUR "#dist.seqs(fasta=final.fasta, cutoff=0.10, processors=$PROCESSORS)"

# Cluster sequences to make OTUs.
#
# Output File Names:
#     final.an.sabund
#     final.an.rabund
#     final.an.list
#
$MOTHUR "#cluster(column=final.dist, name=final.names)"


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
make.shared(list=final.an.list, group=final.groups, label=0.03)

# Move shared table to friendlier location
system(cp final.an.shared final.otu.shared)

# Get consensus OTU classifications using existing classifications
# Use name file corresponding to taxonomy (not the FASTA)
classify.otu(list=final.an.list, group=final.groups, taxonomy=final.taxonomy, name=final.taxonomy.names, label=0.03, reftaxonomy=silva.nr_v123.tax)

# Make trees indicating community similarity
tree.shared(shared=final.otu.shared, calc=thetayc-jclass)

# Distance table for communities, used for AMOVA
dist.shared(shared=final.otu.shared, calc=thetayc)

# AMOVA (analysis of molecular variance) detects significant difference between
# treatment groups
amova(phylip=final.otu.thetayc.0.03.lt.dist, design=rawfile.design)

# Generate collector's curves showing how richness, diversity, etc. change with
# sampling effort
collect.single(shared=final.otu.shared)

# Get single-sample summary statistics
summary.single(shared=final.otu.shared, calc=nseqs-coverage-sobs-invsimpson-chao)

# Rarefaction curve (richness vs. sampling effort) with confidence intervals
rarefaction.single(shared=final.otu.shared)
"

run_mothur_command "$COMMAND"

if [ "$DO_OTU_ENRICHMENT" = "true" ]; then
    # Metastats: detect differentially-abundant OTUs
    $MOTHUR "#metastats(shared=final.otu.shared, design=rawfile.design)"
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
    $MOTHUR "#make.lefse(shared=final.otu.shared, design=rawfile.design, constaxonomy=final.an.0.03.cons.taxonomy, label=0.03)"
fi

# Make the BIOM file, with OTU abundance and taxonomy information
$MOTHUR "#make.biom(shared=final.otu.shared, constaxonomy=final.an.0.03.cons.taxonomy)"

# Using the BIOM package (bundled in QIIME), output human-readable description
# of the BIOM file.
biom summarize-table -i final.otu.0.03.biom -o otu_table.biom.summary.txt

## make better plots
Rscript betterplots.R rawfile.final.otu.0.03.biom rawfile.mapping Phylum NO
Rscript betterplots.R rawfile.final.otu.0.03.biom rawfile.mapping Class NO
Rscript betterplots.R rawfile.final.otu.0.03.biom rawfile.mapping Order NO
Rscript betterplots.R rawfile.final.otu.0.03.biom rawfile.mapping Family NO
Rscript betterplots.R rawfile.final.otu.0.03.biom rawfile.mapping Genus NO


if [ "$DO_CORE_DIVERSITY" = true ]; then
    # Sort the samples in the OTU table by treatment
    sort_otu_table.py -i final.otu.0.03.biom -o final.otu.0.03.sorted.biom -m rawfile.mapping -s TreatmentGroup

    # Use Andrew's script to calculate best subsample size
    sub=$(perl calculate_subsample.pl -f $QIIME_SUBSAMPLE_FRAC otu_table.biom.summary.txt 2> subsampling_summary.txt)

    # Do the standard diversity analyses and plots in the QIIME workflow
    core_diversity_analyses.py -o $PWD/core_diversity -i $PWD/final.otu.0.03.sorted.biom -m $PWD/rawfile.mapping -e $sub --parallel --jobs_to_start $PROCESSORS --nonphylogenetic_diversity -c "TreatmentGroup"
fi

if [ "$DO_INTERACTIVE_HEATMAP" = true ]; then
    # Make QIIME's interactive HTML-based heatap
    make_otu_heatmap_html.py -i final.otu.0.03.sorted.biom -o OTU_Heatmap/
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
dist.seqs(fasta=final.fasta, output=phylip, processors=$PROCESSORS)

# Use clearcut to construct the phylogenetic tree
clearcut(phylip=final.phylip.dist)

# Use unweighted UniFrac to get phylogenetic distances between samples.
# Unweighted UniFrac does not consider abundances in distance calculation.
unifrac.unweighted(tree=final.phylip.tre, name=final.names, group=final.groups, distance=lt, processors=$PROCESSORS, random=F)

# Use weighted UniFrac to get phylogenetic distances between samples.
# Weighted UniFrac weights OTUs by abundance in distance calculation.
unifrac.weighted(tree=final.phylip.tre, name=final.names, group=final.groups, distance=lt, processors=$PROCESSORS, random=F)

# Principal coordinate analysis of the UniFrac distance matrices
pcoa(phylip=final.phylip.tre1.unweighted.phylip.dist)
pcoa(phylip=final.phylip.tre1.weighted.phylip.dist)
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
phylotype(taxonomy=final.taxonomy, name=final.taxonomy.names)

# Make a shared file. The command label=1 means the most specific level
# available in the taxonomy (e.g. species)
make.shared(list=final.tx.list, group=final.groups, label=1)

system(cp final.tx.shared final.phylotype.shared)

# Label the phylotypes with their consensus taxonomy
# Use name file corresponding to taxonomy (not the FASTA)
classify.otu(list=final.tx.list, group=final.groups, taxonomy=final.taxonomy, name=final.taxonomy.names, label=1)

# Make a tree of sample similarities using phylotype abundance
tree.shared(shared=final.phylotype.shared, calc=thetayc-jclass)
"

run_mothur_command "$COMMAND"

