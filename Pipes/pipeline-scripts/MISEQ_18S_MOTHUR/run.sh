#!/bin/bash
TZ='America/New_York' date >logfile.txt
#not needed on newest AMI (I think?)
#. /home/ubuntu/qiime_software/activate.sh >>logfile.txt 2>&1
if [[ -e push_to_aws.py ]]; then
    chmod a+x ./push_to_aws.py >> logfile.txt 2>&1
fi
# check map file format and convert if necessary
cp config.csv config.csv.bak && \

chmod a+x mapcheck.sh && \
./mapcheck.sh config.csv >config.csv.tmp && \
mv config.csv.tmp config.csv && \
rm -rf config.csv.bak excelparser.zip excelparser/ mapcheck.sh

# creating intermediate configuration file
./miseq_18S.py config.csv >>logfile.txt 2>&1

# choosing pipeline type
str=`grep READS_TYPE config.csv`
#echo "+$str+" >>logfile.txt 2>&1
opt=${str:11} 
echo $opt >>logfile.txt 2>&1

if [ "$opt" == "DISJUNCT" ] ; then
   echo "Running mothur_illumina_disjunct.sh" >>logfile.txt
   ./mothur_illumina_disjunct.sh config_18S.txt >>logfile.txt 2>&1
else
   echo "Running mothur_illumina.sh" >>logfile.txt
   ./mothur_illumina.sh config_18S.txt >>logfile.txt 2>&1
fi

TZ='America/New_York' date >>logfile.txt
echo "Pipeline done" >>logfile.txt
TZ='America/New_York' date >Pipeline_done.txt
/bin/bash ./exit_script.sh >> logfile.txt 2>&1
