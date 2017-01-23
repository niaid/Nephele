#!/bin/bash

# . /home/ubuntu/qiime_software/activate.sh >logfile.txt 2>&1
# . /home/ubuntu/qiime_software/activate.sh


# handle zip / compressed files with spaces
touch ._stuff
find . -name "*.zip" -exec sh -c 'unzip -oqj "{}" ' \;
rm ._*
find . -name "*.tgz" -exec sh -c 'tar xzf "{}" ' \;
find . -name "*.gz"  -exec sh -c 'gunzip -f "{}" ' \;
find . -name "*.tar" -exec sh -c 'tar xf "{}" ' \;
find . -name "*.gz"  -exec sh -c 'gunzip -f "{}" ' \;


if [[ -e mothur ]]; then
    chmod a+x ./mothur >> logfile.txt 2>&1
fi
if [[ -e pqiime.py ]]; then
    chmod a+x ./pqiime.py >> logfile.txt 2>&1
fi

if [[ -e push_to_aws.py ]]; then
    chmod a+x ./push_to_aws.py >> logfile.txt 2>&1
fi

export BLASTMAT="/usr/share/ncbi/data/"

# Running pipeline
/usr/bin/python pqiime.py ./config.csv >> runtime.txt 2>&1


TZ='America/New_York' date >Pipeline_done.txt
/usr/local/nephele/nephelenode.sh --notify "completed"
