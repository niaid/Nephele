#!/bin/bash

# . /home/ubuntu/qiime_software/activate.sh >logfile.txt 2>&1
# . /home/ubuntu/qiime_software/activate.sh

count=`ls -1 *.zip 2>/dev/null | wc -l`
if [ $count != 0 ]; then for f in *.zip; do unzip -oqj $f; done fi
count=`ls -1 *.tgz 2>/dev/null | wc -l`
if [ $count != 0 ]; then for f in *.tgz; do tar xzf $f; done fi
count=`ls -1 *.gz 2>/dev/null | wc -l`
if [ $count != 0 ]; then for f in *.gz; do gunzip -f $f; done fi
count=`ls -1 *.tar 2>/dev/null | wc -l`
if [ $count != 0 ]; then for f in *.tar; do tar xf $f; done fi
count=`ls -1 *.gz 2>/dev/null | wc -l`
if [ $count != 0 ]; then for f in *.gz; do gunzip -f $f; done fi

if [[ -e mothur ]]; then
    chmod a+x ./mothur >> logfile.txt 2>&1
fi
if [[ -e pqiime.py ]]; then
    chmod a+x ./pqiime.py >> logfile.txt 2>&1
fi

if [[ -e push_to_aws.py ]]; then
    chmod a+x ./push_to_aws.py >> logfile.txt 2>&1
fi

# check map file format and convert if necessary
cp config.csv config.csv.bak && \
chmod a+x mapcheck.sh && \
./mapcheck.sh config.csv >config.csv.tmp && \
mv config.csv.tmp config.csv && \
rm -rf config.csv.bak excelparser.zip excelparser/ mapcheck.sh

# Running pipeline
/usr/bin/python pqiime.py ./config.csv >> runtime.txt 2>&1


TZ='America/New_York' date >Pipeline_done.txt
/usr/local/nephele/nephelenode.sh --notify "completed"
