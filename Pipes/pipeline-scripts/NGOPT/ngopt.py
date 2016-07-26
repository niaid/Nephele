#!/usr/bin/env python

##############################################################
# $Id$
# Project:   MiSeq Metagenomic Assembly pipeline for Nephele project
# Language:  Python 2.7
# Author:    Alex Levitsky
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
   os.system( "echo >> "+log_file)
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
   for key in ['INPUT_TYPE', 'R1', 'R2', 'ZIP_FILE', 'LIB_FILE', 'BLAST_STEP','PREFIX']:
      if(key not in config.keys()):
         config[key]=''
   ##### Predefined and calculated options
   if(''==config['LIB_FILE']):
      config['INPUT_TYPE']='FASTQ_FILES'
   if(''==config['PREFIX']):
      config['PREFIX']='MiSEQ_metagenomic'
   if(''==config['BLAST_STEP']):
      config['BLAST_STEP']='YES'

   send2log( 'MiSeq Metagenomic Assembly pipeline started', log_file )

   # get env.json if available
   if os.path.isfile('./env.json'):
      send2log( 'env.json=', log_file )
      syscall( 'cat ./env.json >> '+log_file)

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

   w="MiSeq Metagenomic Assembly pipeline configuration\n"
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
   # unzip reads
   if os.path.isfile(work_dir+'/'+config['ZIP_FILE']):
      # check files extension
      w=''
      if config['ZIP_FILE'][-4:]=='.zip':
         send2log( 'unzip -oqj '+config['ZIP_FILE'], log_file )
         w=syscall('unzip -oqj '+config['ZIP_FILE'])
         send2log( w, log_file )
      if (config['ZIP_FILE'][-7:]=='.tar.gz') or (config['ZIP_FILE'][-4:]=='.tgz'):
         send2log( 'tar -zxvf '+config['ZIP_FILE'], log_file )
         w=syscall('tar -zxvf '+config['ZIP_FILE'])
         send2log( w, log_file )
      if config['ZIP_FILE'][-8:]=='.tar.bz2':
         send2log( 'tar -jxvf '+config['ZIP_FILE'], log_file )
         w=syscall('tar -jxvf '+config['ZIP_FILE'])
         send2log( w, log_file )

      # unzip gzip files if any
      w=''
      w=syscall('ls *.gz')
      if len(w)>3:
         send2log( 'running gzip -d for *.gz files', log_file )
         w=''
         w=syscall('gzip -d *.gz')

   else:
      send2log( "ERROR: no zip archive with reads. Can not continue\n", log_file)
      sys.exit(777)

   if 'FASTQ_FILES'==config['INPUT_TYPE']:
      # check reads files
      w=''
      w=syscall('ls *.fastq')
      if len(w)<3:
         w=''
         w=syscall('ls *.fq')
         if len(w)<3:
            send2log( "ERROR: no reads files. Can not continue\n", log_file)
            sys.exit(777)
      l=[]
      l=w.split('\n')
      config['R1']=l[0]
      config['R2']=l[1]
      if not( os.path.exists(work_dir+'/'+config['R1']) and  os.path.exists(work_dir+'/'+config['R2']) ):
         send2log( "ERROR: no reads files. Can not continue\n", log_file)
         sys.exit(777)
      cmd='./bin/a5_pipeline.pl '+'--threads='+config['NUM_OF_PROC']+' --end=5 '+config['R1']+' '+config['R2']+' '+config['PREFIX']
      send2log( "Running pipeline:\n"+cmd, log_file )
      w=''
      w=syscall( cmd+' 2>&1' )
      send2log( w, log_file )
   else:
      if os.path.isfile(work_dir+'/'+config['LIB_FILE']):
         send2log("contents of LIB file:", log_file)  
         syscall( 'cat '+config['LIB_FILE']+ ' >> ' +log_file)
         send2log("\n", log_file)  
      else:
         send2log( "ERROR: no LIB file. Can not continue\n", log_file)
         sys.exit(777)

      #cmd='./bin/a5_pipeline.pl '+config['LIB_FILE']+' '+config['PREFIX']
      cmd='/opt/a5/bin/a5_pipeline.pl '+'--threads='+config['NUM_OF_PROC']+' --end=5 '+config['LIB_FILE']+' '+config['PREFIX']
      send2log( "Running pipeline: \n"+cmd, log_file )
      w=''
      w=syscall( cmd+' 2>&1' )
      send2log( w, log_file )

   if 'YES'==config['BLAST_STEP']:
      # BLAST step
      #send2log( 'Executing:'+cmd, log_file)
      #w=syscall(cmd)
      #send2log( w, log_file )
      #cmd ='blast-2.2.29+/bin/blastx -db BLAST_NR/nr'\
      #      + ' -out NTCC8325out.final.scaffolds.blastn_t4x.txt'\
      #      + ' -query NTCC8325out.final.scaffolds.fasta'\
      #      + ' -num_threads '+config['NUM_OF_PROC']+' -outfmt 6'

      cmd ='./blast2nr.sh '+config['PREFIX']+' '+config['NUM_OF_PROC']
      send2log( 'Executing:'+cmd, log_file)
      w=syscall(cmd)
      send2log( w, log_file )

   send2log( 'MiSeq Metagenomic Assembly pipeline DONE',log_file )

if __name__ == "__main__":
    main()
