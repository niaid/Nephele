TZ='America/New_York' date >>logfile.txt
echo "initiation" >>logfile.txt
echo "running pipeline" >>logfile.txt

cp config.csv config.csv.bak && \

chmod a+x mapcheck.sh && \
./mapcheck.sh config.csv >config.csv.tmp && \
mv config.csv.tmp config.csv

echo "Starting WGS" >> logfile.txt
./wgsp.py config.csv >>logfile.txt 2>&1
chmod a+x wgsp_exe.sh
source /home/ubuntu/anadama_env/bin/activate
./wgsp_exe.sh >>logfile.txt 2>&1
TZ='America/New_York' date >>logfile.txt
TZ='America/New_York' date >Pipeline_done.txt
/bin/bash ./exit_script.sh >> logfile.txt 2>&1

