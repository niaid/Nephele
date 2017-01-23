TZ='America/New_York' date >>logfile.txt
#. /home/ubuntu/qiime_software/activate.sh >>logfile.txt 2>&1
chmod a+x ./create_map_design.sh >> logfile.txt 2>&1
chmod a+x ./calculate_subsample.pl >> logfile.txt 2>&1
chmod a+x ./pmothur.py >> logfile.txt 2>&1
chmod a+x ./beta_div.py >> logfile.txt 2>&1
chmod a+x ./mothur >> logfile.txt 2>&1
chmod a+x ./uchime >> logfile.txt 2>&1
chmod a+x ./exit_script.sh >> logfile.txt 2>&1
chmod a+x ./push_to_aws.py >> logfile.txt 2>&1
#touch ./PipelineResults.zip
#chmod 777 ./PipelineResults.zip

# check map file format and convert if necessary
cp config.csv config.csv.bak && \

chmod a+x mapcheck.sh && \
./mapcheck.sh config.csv >config.csv.tmp && \
mv config.csv.tmp config.csv && \
rm -rf config.csv.bak excelparser.zip excelparser/ mapcheck.sh

# Running pipeline
./pmothur.py ./config.csv >>logfile.txt 2>&1

TZ='America/New_York' date >>logfile.txt
TZ='America/New_York' date >Pipeline_done.txt

/bin/bash ./exit_script.sh >> logfile.txt 2>&1
