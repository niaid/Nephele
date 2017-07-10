#!/usr/bin/env python

##############################################################
# $Id$
# Project:   MiSeq MOTHUR 18S pipeline
# Language:  Python 2.7
# Authors:   Joe Wan, Mariam Quinones, Alex Levitsky
# History:   August 2015 Start of development 
##############################################################

import sys, os, random, time, glob
import re
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

##### Predefined and calculated options

for key in ['LOG_FILE']:
   if(key not in config.keys()):
      config[key]=''

if(''==config['LOG_FILE']):
   config['LOG_FILE']='logfile.txt'

work_dir=os.getcwd()+'/'
log_file=work_dir+config['LOG_FILE']

send2log( '18S MiSeq MOTHUR pipeline started', log_file )

# get env.json if available
if os.path.isfile('./env.json'):
   send2log( 'env.json=', log_file )
   syscall( 'cat ./env.json >> '+log_file)
   send2log( "\n", log_file )

# get machine's memory
config['MEMORY']=syscall("cat /proc/meminfo | grep MemTotal | awk '{ print $2 }'")
mem=int(config['MEMORY'])
send2log( 'Memory='+config['MEMORY']+'KB', log_file )

# get number of cores
config['PROCESSORS']=syscall('cat /proc/cpuinfo  | grep processor | wc -l')
num_proc=int(config['PROCESSORS'])
if(num_proc > 1):
   num_proc-=1
config['PROCESSORS']=str(num_proc)
send2log( 'number of cores='+config['PROCESSORS'], log_file )

# it should be proper memory/processor ratio set here
# ???

w="18S MiSeq MOTHUR pipeline configuration\n"
for k in sorted(config.keys()):
   config[k]=config[k].replace("\"", "_")
   config[k]=config[k].replace("\'", "_")
   if 'UseCode'==k:
      continue
   w=w+k+','+config[k]+"\n"
# print configuration to log file
send2log( w, log_file )

####################################################

# DEFAULT OPTIONS
options_18S={
      "CLASSIFY_CONFIDENCE":"80",\
      "SCREEN_MAXAMBIG":"0",\
      "FORWARD_PRIMER":"",\
      "REVERSE_PRIMER":"",\
      "PRECLUSTER_DIFFS":"2",\
      "DO_CORE_DIVERSITY":"true",\
      "DO_INTERACTIVE_HEATMAP":"true",\
      "DO_OTU_ENRICHMENT":"true",\
      "PHYLOTYPE_LEVEL":"1",\
      "MOTHUR":"./mothur",\
      "PROCESSORS":"1",\
      "OTU_MODE":"masked",\
      "TRIM_MAXAMBIG":"0",\
      "QAVERAGE":"30",\
      "PRECLUSTER_DIFFS":"2",\
      "REMOVE_LIST":"Chloroplast-mitochondria-unknown-Archaea-Bacteria",\
      "OPTIMIZE":"start-end-minlength",\
      "OPTIMIZE_CRITERIA":"90",\
      "REMOVE_SINGLETONS":"true",\
      "QIIME_SUBSAMPLE_FRAC":"0.1"
}

for k in ( options_18S.keys() ):
   if k not in config.keys():
       config[k]=''
for k in (options_18S.keys() ):
   if ''==config[k]:
      # set up default values
      config[k]=options_18S[k]
      continue

# create forward and reverse primers from oligo file
cmd='grep -i forward '+config['OLIGO_FILE']
w=''
w=syscall(cmd)
config['FORWARD_PRIMER']=w.split('\t')[1]
cmd='grep -i reverse '+config['OLIGO_FILE']
w=''
w=syscall(cmd)
config['REVERSE_PRIMER']=w.split('\t')[1]

# check map file and create STABILITY FILE and DESIGN FILE from map file
config['STABILITY_FILE']='rawfile.files'
config['DESIGN_FILE']='rawfile.design'
send2log( 'Creating stability file '+config['STABILITY_FILE']+' from ForwardFastqFile and ReverseFastqFile columns in mapping file...', log_file )
send2log( 'Creating design file '+config['DESIGN_FILE']+' from  mapping file...', log_file )

# copy mapping file
if not os.path.isfile( work_dir+'/rawfile.mapping' ):
   w=''
   w=syscall('cp '+config['MAP_FILE']+' rawfile.mapping')
   send2log( w, log_file )
map_file=open( config['MAP_FILE'], 'r')
#SampleID       ForwardFastqFile    ReverseFastqFile        BarcodeSequence LinkerPrimerSequence    TreatmentGroup
# F3D0    F3D0_S188_L001_R1_001.fastq     F3D0_S188_L001_R2_001.fastq     CCGTCAATTC      CCGTCAATTA      Early
# F3D1    F3D1_S189_L001_R1_001.fastq     F3D1_S189_L001_R2_001.fastq     CCGTCAATTC      CCGTCAATTA      Early
stability_file=open( work_dir+config['STABILITY_FILE'], 'w')
design_file=open( work_dir+config['DESIGN_FILE'], 'w')
# #SampleID       TreatmentGroup
# F3D0    Early
# F3D1    Early
# F3D141  Late
samples_list=[]
n_Forward=0
n_Reverse=0
n_Treatment=0
l=[]
for line in map_file:
   if("" == line): # check for end of file
      break
   s=line.rstrip("\n")
   s.strip()
   if("" == s): # ignore empty lines
      continue
   if "#"==s[:1] and 0==n_Forward and 0==n_Reverse and 0==n_Treatment:  # header line determine numbers for ForwardFastq and ReverseFastqFile
      # check map file
      for column in ['#SampleID','ForwardFastqFile','ReverseFastqFile','BarcodeSequence','LinkerPrimerSequence','TreatmentGroup']:
         if column not in s:
            send2log( 'ERROR: mandatory column:'+column+'is not in mapping file. Can not continue', log_file )
            sys.exit(77)
     # del l[:] # clear list
      l=s.split("\t")
      for j in range( 1,len(l) ):
         if 'ForwardFastqFile'== l[j]:
            n_Forward=j
            continue
         if 'ReverseFastqFile'== l[j]:
            n_Reverse=j
            continue
         if 'TreatmentGroup'== l[j]:
            n_Treatment=j
            continue

      if (0==n_Forward or 0==n_Reverse):
         send2log( 'ERROR: ForwardFastqFile or ReverseFastqFile columns does not exist in mapping file. Can not continue', log_file )
         sys.exit(77)

      design_file.write("#SampleID\tTreatmentGroup\n")
   else: # non-header lines with samples
      del l[:] # clear list
      l=s.split("\t")
      # check for .gz extention
      if '.gz' in l[n_Forward]:
         l[n_Forward]= re.sub('\.gz$', '', l[n_Forward])
      if '.gz' in l[n_Reverse]:
         l[n_Reverse]= re.sub('\.gz$', '', l[n_Reverse])
      samples_list.append(l[0])
      stability_file.write(l[0]+"\t"+l[n_Forward]+"\t"+l[n_Reverse]+"\n")
      design_file.write(l[0]+"\t"+l[n_Treatment]+"\n")
map_file.close()
stability_file.close()

#################################
# !!!!!!!!!!!!!!!!!!!! temporary
#config['OPTIMIZE']='start-end-minlength'
# !!!!!!!!!!!!!!!!!!!! temporary

# create intermediate configuration file for 18S pipelines
conf_file=open( './config_18S.txt', 'w')
for k in sorted(options_18S.keys()):
   #conf_file.write(k+'='+config[k]+"\n")
   conf_file.write(k+"=\""+config[k]+"\"\n")
conf_file.close

# unzip reads archive
send2log( 'unzip reads archive STARTED', log_file)
cmd='unzip -oqj '+config['ZIP_FILE']+' >>'+log_file+' 2>&1'
w=syscall(cmd)
send2log( w, log_file)
send2log( 'unzip archive DONE', log_file)

# ungzip gzipped files if any
# create list of *.gz files
w=''
w=syscall('ls *.gz 2>&1')
if 'No such file' not in w :
   gz_list=w.split()
   for gz_file in gz_list:
      cmd='gzip -d '+gz_file+' >> ../'+log_file+' 2>&1'
      exec_sys(cmd)
      
