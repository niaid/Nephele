# remove executables
rm -rf ./create_map_design.sh
rm -rf ./calculate_subsample.pl
rm -rf ./miseq_18S.py
rm -rf ./mothur
rm -rf ./uchime
rm -rf silva.nr_v123.align
rm -rf silva.trimmed.align
rm -rf silva.seed_v123.align
rm -rf silva.trimmed.8mer


#
# Archive with contents of work folder
echo "Creating archives"
zip -r WorkFolder.zip *
chmod 777 ./WorkFolder.zip
#
# Custom files from Mariam
# Select files
echo "Creating PipelineResults File"
mkdir SelectedFiles
mkdir trees
mkdir biome_files
mkdir metastats
cp *final*tre* trees/
cp *biom* biome_files/
cp -r biome_files SelectedFiles/
cp -r trees SelectedFiles/ 
cp -r OTU_Heatmap SelectedFiles/
cp -r *div* SelectedFiles/
cp *metastats metastats/
cp -r metastats SelectedFiles/
cp *groups.summary SelectedFiles/
cp *final.taxonomy SelectedFiles/
cp *cons.tax.summary SelectedFiles/
cp *0.03.cons.tax.summary SelectedFiles/
cp *0.03.cons.taxonomy SelectedFiles/
cp *lefse* SelectedFiles/
cp *0.03.rep.fasta SelectedFiles/
cp config.csv SelectedFiles/
cp rawfile.trim.contigs.good.unique.fasta SelectedFiles/
cp -r taxa_plots_and_heatmaps SelectedFiles/

# logfile
if [ -f logfile.txt ];
then
   cp -R logfile.txt SelectedFiles/
fi
# Command to make a zipped tar archive
cd SelectedFiles
zip -r ../SelectedFiles.zip *
mv ../SelectedFiles.zip ../PipelineResults.zip
chmod 777 ../PipelineResults.zip


echo "Finished creating PipelineResults File"
cd ..
rm -rf $out

