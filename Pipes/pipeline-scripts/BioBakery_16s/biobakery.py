#!/usr/bin/env python

##############################################################
# $Id$
# Project:   BioBakery WGS and 16s pipelines
# Language:  Python 2.7
# Authors:   Randall Schwager, Alex Levitsky
# History:   October 2014 Start of development
##############################################################

import sys, os, random, time, glob
syscall = lambda cmd: (os.popen(cmd).read()).rstrip("\n")

def read_config( file_name, config ): #########################
   config_file=open( file_name, 'r')
   l=[]
   for line in config_file:
      if("" == line): # check for end of file
         break
      s=line.rstrip("\n")
      s.strip()
      if("" == s): # ignore empty lines
         continue
      if("#"==s[:1]): # ignore comments
         continue
      del l[:] # clear list
      l=s.split(',')
      config[l[0]]=l[1]
   config_file.close()
### read_config ###

def send2log( message, log_file ): #######################
   date = syscall("TZ='America/New_York' date")
   if 0!=os.system( "echo '"+date+' '+message+"' >>"+log_file):
      sys.exit(777)
### send2log ###

def exec_sys(cmd): #######################
   #print >> sys.stderr, "Executing:",cmd
   if 0!=os.system(cmd):
      print >> sys.stderr, "ERROR when executing:",cmd
      sys.exit(777)
      #os.environ['EXIT_STATUS'] = '1'
### exec_sys ###

###########  main  ##############################
if len( sys.argv ) < 2:
   print >> sys.stderr, "\n\n\nUsage: " + sys.argv[0] + " <configuration file>\n\n\n"
   sys.exit(551)

# Read config file
conf_file = sys.argv[1]
if not os.path.isfile( conf_file ):
   print >> sys.stderr, "ERROR: no config file:" + conf_file
   sys.exit(555)
config = {}
read_config( conf_file,config )

##### Define optional and default parameters

for key in ['STUDY_TITLE', 'PLATFORM', 'PIPELINE_TYPE', 'BB_WORK_DIR']:
   if(key not in config.keys()):
      config[key]=''
if(''==config['STUDY_TITLE']):
   config['STUDY_TITLE']='test'
if(''==config['PLATFORM']):
   config['PLATFORM']='454'
if(''==config['PIPELINE_TYPE']):
   config['PIPELINE_TYPE']='wgs'
if(''==config['BB_WORK_DIR']):
   config['BB_WORK_DIR']='bb_work_dir'
if(''==config['SAMPLE_TYPE']):
   config['SAMPLE_TYPE']='unknown'

######   !!! Hardcoded for 16s !!!  #######
config['PIPELINE_TYPE']='16s'
###########################################

##### Predefined and calculated options
work_dir=os.getcwd()
config['LOG_FILE']='logfile.txt'
log_file=work_dir+'/'+config['LOG_FILE']

send2log( 'BioBakery pipeline started', log_file )

# get env.json if available
if os.path.isfile('./env.json'):
   send2log( 'env.json=', log_file )
   syscall( 'cat ./env.json > '+log_file)

# get number of cores
config['NUM_OF_PROC']=syscall('cat /proc/cpuinfo  | grep processor | wc -l')
num_proc=int(config['NUM_OF_PROC'])
if(num_proc > 1):
   num_proc-=1
config['NUM_OF_PROC']=str(num_proc)
send2log( 'number of cores='+config['NUM_OF_PROC'], log_file )

# get machine's memory
config['MEMORY']=syscall("cat /proc/meminfo | grep MemTotal | awk '{ print $2 }'")
mem=int(config['MEMORY'])
send2log( 'Memory='+config['MEMORY']+'KB', log_file )

w="BioBakery pipeline configuration\n"
for k in sorted(config.keys()):
   config[k]=config[k].replace("\"", "_")
   config[k]=config[k].replace("\'", "_")
   w=w+k+','+config[k]+"\n"
# print configuration to log file
send2log( w, log_file )

####################################################

# prepare work directory
if os.path.isdir(config['BB_WORK_DIR']):
   cmd='sudo rm -rf '+config['BB_WORK_DIR']
   exec_sys(cmd)
os.makedirs(config['BB_WORK_DIR'])
os.chdir(config['BB_WORK_DIR'])

# check for Map file name
if 'map.txt'==config['MAP_FILE']:
   cmd='mv ../'+config['MAP_FILE']+' ./'
   exec_sys(cmd)
else:
   cmd='mv ../'+config['MAP_FILE']+' ./map.txt'
   exec_sys(cmd)
cmd='mv ../'+config['READS_ZIP']+' ./'
exec_sys(cmd)
cmd='unzip -oqj ./'+config['READS_ZIP']
exec_sys(cmd)
cmd='rm -rf ./'+config['READS_ZIP']
exec_sys(cmd)
send2log( "reads unarchived", log_file )

if('16s'==config['PIPELINE_TYPE']):
   s0='yes'
else:
   s0='no'
send2log( 'Running mibc_build initialize-project', log_file )
cmd="mibc_build initialize-project "\
       +"\'study_description: "+config['STUDY_TITLE']+"\' "\
       +"\'sample_type: "+config['SAMPLE_TYPE']+"\' "\
       +"\'filename:\' "\
       +"\'16s_data: "+s0+"\' "\
       +"\'study_title: "+config['STUDY_TITLE']+"\' "\
       +"\'platform: "+config['PLATFORM']+"\' "\
       +"\'visualize: yes\'"
send2log( 'executing:'+cmd, log_file )
exec_sys(cmd)

os.chdir(work_dir)

send2log( 'Running mibc_build runproject', log_file )
#cmd="mibc_build runproject --project wgs_work/ --reporter=verbose > wgs_run.log 2>&1"
cmd="mibc_build runproject --project "+config['BB_WORK_DIR']+"/ --reporter=verbose >> "+log_file+" 2>&1"
send2log( 'executing:'+cmd, log_file )
exec_sys(cmd)

#############################################################################
send2log( 'Pipeline DONE',log_file )
