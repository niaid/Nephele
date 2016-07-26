# zip installation
sudo apt-get update && sudo apt-get install --yes zip

# Executables removal
# rm -rf ./arguments.json
# rm -rf ./nephele-notify
# rm -rf ./biobakery.py

# Archive with contents of work folder
# Exclude web directories, hidden files, and other non-necessary files
zip -9 -r WorkFolder.zip * -x "*/\.*" 'arguments.json' 'biobakery.py' 'env.json' "__MACOSX/*" "WEB-INF/*" "META-INF/*" "Storage*"
chmod 777 ./WorkFolder.zip

# philip start
# ./push_to_aws.py
# philip end
cp logfile.txt bb_work_dir44/mibc_products/.
cp config.csv bb_work_dir44/mibc_products/.
cd bb_work_dir44/mibc_products
zip -9 -r ../../SelectedFiles.zip *
mv ../../SelectedFiles.zip ../../PipelineResults.zip
# cd ../../
# sudo shutdown -h "now"
