# remove executables
rm -rf ./create_map_design.sh
rm -rf ./calculate_subsample.pl
rm -rf ./pmothur.py
rm -rf ./beta_div.py
rm -rf ./mothur
rm -rf ./uchime
#
rm -rf ./arguments.json
#
# Archive with contents of work folder
zip -r WorkFolder.zip *
chmod 777 ./WorkFolder.zip
#
# Custom files from Mariam
# Select files
mkdir SelectedFiles
mkdir trees
mkdir biome_files
mkdir metastats
cp *final*tre* trees/
cp *biom* biome_files/
cp -r biome_files SelectedFiles/
cp -r trees SelectedFiles/ 
cp -r OTU_Heatmap SelectedFiles/
cp -r core_diversity SelectedFiles/
cp *metastats metastats/
cp -r metastats SelectedFiles/
cp *groups.summary SelectedFiles/
cp *final.taxonomy SelectedFiles/
cp *cons.tax.summary SelectedFiles/
cp *0.03.cons.tax.summary SelectedFiles/
cp *0.03.cons.taxonomy SelectedFiles/
cp *lefse* SelectedFiles/
cp *trim.unique.fasta SelectedFiles/
#cp -r *_with_HMPDACC_v13 SelectedFiles/ 
#cp -r *_with_HMPDACC_v35 SelectedFiles/ 
# logfile
if [ -f logfile.txt ];
then
   cp -R logfile.txt SelectedFiles/
fi
#
# Command to make a zipped tar archive
cd SelectedFiles
zip -r ../SelectedFiles.zip *
mv ../SelectedFiles.zip ../PipelineResults.zip
chmod 777 ../PipelineResults.zip
# philip start
# cd ..
# ./push_to_aws.py
# sudo shutdown -h "now"
# philip end

cd ..
