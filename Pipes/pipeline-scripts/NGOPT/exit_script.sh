# Executables removal
rm -rf ./a5.py
rm -rf bin
#
rm -rf ./arguments.json
# Archive with contents of work folder
zip -r WorkFolder.zip *
chmod 777 ./WorkFolder.zip
echo "WorkFolder.zip created" >> logfile.txt 2>&1
# custom part
out=SelectedFiles
mkdir $out
# Copy selected files and directories that a user will want to look at first
cp *contigs.fasta $out/
cp *scaffolds* $out/
cp *assembly_stats.csv $out/
# logfile
if [ -f logfile.txt ];
then
   cp logfile.txt $out/
fi
cd $out
zip -r ../SelectedFiles.zip *
mv ../SelectedFiles.zip ../PipelineResults.zip
chmod 777 ../PipelineResults.zip
cd ..
rm -rf $out
