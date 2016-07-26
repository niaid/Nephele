#!/usr/bin/env python

##############################################################
# $Id$
# Project:   WGS pipeline for Nephele project
# Language:  Python 2.7
# Authors:   Philip Macmenamin, Randall Schwager, Alex Levitsky
# History:   July 2015 Start of development
##############################################################

__author__ = "Alex Levitsky"
__copyright__ = ""
__credits__ = ["Alex Levitsky"]
__license__ = ""
__version__ = "1.0.1-dev"
__maintainer__ = "Alex Levitsky"
__status__ = "Development"

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
   os.system( "echo >>"+log_file)
   if 0!=os.system( "echo '"+date+' '+message+"' >>"+log_file):
      sys.exit(777)
### send2log ###

def exec_sys(cmd): #######################
   #print >> sys.stderr, "Executing:",cmd
   if 0!=os.system(cmd):
      print >> sys.stderr, "ERROR when executing:",cmd
      sys.exit(777)
### exec_sys ###

###########  main  ##############################
def main():
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

   work_dir=os.getcwd()
   config['LOG_FILE']='logfile.txt'
   log_file=work_dir+'/'+config['LOG_FILE']

   ##### Define optional and default parameters
   for key in ['ZIP_FILE', 'MAP_FILE']:
      if(key not in config.keys()):
         config[key]=''

   send2log( 'WGS pipeline started', log_file )

   # get env.json if available
   if os.path.isfile('./env.json'):
      send2log( 'env.json=', log_file )
      syscall( 'cat ./env.json >> '+log_file)

   w="WGS pipeline configuration\n"
   for k in sorted(config.keys()):
      if 'UseCode'==k:
         continue
      config[k]=config[k].replace("\"", "_")
      config[k]=config[k].replace("\'", "_")
      w=w+k+','+config[k]+"\n"
   # print configuration to log file
   send2log( w, log_file )

   ####################################################
   os.chdir(work_dir)

   cmd='unzip -oqj ./'+config['READS_ZIP']
   exec_sys(cmd)
   cmd='rm -rf ./'+config['READS_ZIP']
   exec_sys(cmd)
   send2log( "reads unarchived", log_file )

############ execute wgsp.sh ###########################
	
   ana_file = open("wgsp_exe.sh", 'w')
   command="anadama pipeline anadama_workflows.pipelines:WGSPipeline -f 'raw_seq_files: glob:*.fastq' -o 'decontaminate.threads: 32' -o 'metaphlan2.nproc: 8'  -A anadama_workflows.pipelines:VisualizationPipeline -f 'sample_metadata: " + config['MAP_FILE'] + "'"
   send2log(command, log_file)
   ana_file.write(command)
   ana_file.write("\n")
   ana_file.close()
   #exec_sys(cmd)

   ######### end main ####################################

if __name__ == "__main__":
    main()
