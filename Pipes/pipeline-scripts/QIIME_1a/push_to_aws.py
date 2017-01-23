#!/usr/bin/env python
# this is a stop gap... will be rm;d soon!
import os, json, subprocess

def lookup_job_id():
    if os.path.isfile('env.json'):
        with open( 'env.json' ) as data_file:
            data = json.load(data_file)
            if 'jobId' in data.keys():
                return data['jobId']
            else:
                # logging.error('No jobId could be found in env.json \n' + data)
                # self.exit_and_fail()
                return False
    
def push_results_to_aws():
    j_id = lookup_job_id()
    if not j_id:
        # logging.info( "I'm not going to push any results, because I have no env.json file")
        exit(0)
    files_to_cp_to_s3 = ('logfile.txt','WorkFolder.zip','PipelineResults.zip')
    for f in files_to_cp_to_s3:
        dest = '' + j_id + '/out/'+ j_id +'_' + f
        # logging.info('Copying ' + f + ' to ' + dest)
        exec_cmnd('/usr/local/bin/aws s3 cp ' + f + ' ' + dest)

def exec_cmnd(cmd):
    if cmd is False:
        return
    elif cmd is None:
        exit( 1 )

    try:
        error = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        exit(1)


push_results_to_aws()
