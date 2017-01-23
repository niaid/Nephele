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



cd ..
