# Executables removal
rm -rf ./arguments.json
#

# Archive with contents of work folder
zip -r WorkFolder.zip *
chmod 777 ./WorkFolder.zip
echo "WorkFolder.zip created" >> logfile.txt 2>&1
#
# Custom part from Andrew
out=SelectedFiles
mkdir $out
# Copy selected files and directories that a user will want to look at first
# Note that some of the files might not exist, depending on the users choices when submitting the job
if [ -f sl_out/histograms.txt ];
then
   cp -R sl_out/histograms.txt $out/
fi

cp anadama_products/*_humann/*.tsv $out/
cp anadama_products/*png $out/
cp -R anadama_products/*metaphlan2_merged_meta.biom_barcharts/taxa_summary_plots $out/
cp anadama_products/*merged_meta.biom_maaslin.tsv $out/
cp anadama_products/*merged_meta.biom $out/


# cp -R final.fasta $out/
# cp -R otu_table.biom $out/
# cp -R tree.tre $out/
# cp -R subsampling_summary.txt $out/
# cp -R jack/weighted_unifrac/upgma_cmp/jackknife_named_nodes_weighted.pdf $out/
# cp -R jack/unweighted_unifrac/upgma_cmp/jackknife_named_nodes_unweighted.pdf $out/
# cp -R core_diversity $out/
# cp -R OTU_Heatmap $out/
# cp -R *metastats $out/
# cp -R *lefse $out/
# cp -R *shared $out/
# cp -R *_with_HMPDACC_v13 $out/
# cp -R *_with_HMPDACC_v35 $out/

# cp -R heat_map $out/
# cp -R otus $out/
# cp -R joined_otus $out/
# cp -R sl_out $out/

# logfile
if [ -f logfile.txt ];
then
   cp -R logfile.txt $out/
fi

if [ -f otu_table.dummy.lefse_summary ];
then
   cp -R otu_table.dummy.lefse_summary $out/
fi
# cp -R metagenome_predictions.biom $out/		# commented out right now because we don't have PICRUSt
# Command to make a zipped tar archive
cd $out
zip -r ../SelectedFiles.zip * 
mv ../SelectedFiles.zip ../PipelineResults.zip
chmod 777 ../PipelineResults.zip

# philip start
# cd ..
# ./push_to_aws.py
# sudo shutdown -h "now"
# philip end


cd ..
