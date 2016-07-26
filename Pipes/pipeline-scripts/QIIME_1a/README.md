#####  run:
set time
make sure everything is executable

config backup etc is to with excel file / tab delimited file.

##### pqiime
Take one or two args, ie the conf file (555 means no config file) and if you want to run in debug mode or not
read the config file that David sends from the front end

There's BETADIV tacked onto the back of QIIME and MOTHUR getting called, copies stuff over to achieve this. This should just be packaged into some python code

##### config.csv is the only point of contact / interface
Mothur works in its own shell, usually you make a file with commands
There's a complicated way of defaulting things here, setting to 0 and so on.
(Took months to figure this out.)

##### env.json
JOB ID, and so on that can be used to re-run / details of run

##### /bcbb/MCP_TEST_PIPELINES
contains old results and misc stuff  

##### /opt/AmazonCLI/jobs/DOWNLOAD
old results here too
