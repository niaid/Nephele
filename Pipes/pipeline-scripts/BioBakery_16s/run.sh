TZ='America/New_York' date >logfile.txt
chmod a+x ./biobakery.py >> logfile.txt 2>&1
if [[ -e push_to_aws.py ]]; then
    chmod a+x ./push_to_aws.py >> logfile.txt 2>&1
fi

# check map file format and convert if necessary
cp config.csv config.csv.bak && \

chmod a+x mapcheck.sh && \
./mapcheck.sh config.csv >config.csv.tmp && \
mv config.csv.tmp config.csv && \
rm -rf config.csv.bak excelparser.zip excelparser/ mapcheck.sh

./biobakery.py config.csv >>logfile.txt 2>&1

TZ='America/New_York' date >>logfile.txt
TZ='America/New_York' date >Pipeline_done.txt

/bin/bash ./exit_script.sh >> logfile.txt 2>&1
