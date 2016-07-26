#!/usr/bin/env python

##############################################################
# $Id$
# Project:   MOTHUR 16S pipeline
# Language:  Python 2.7
# Authors:   Mariam Quinones, Alex Levitsky
# History:   April 2014 Start of development, October 2014 revision 3 
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

def add2mothur_cmd(mothur_cmd,file): #######################
   cmd='echo '+"'"+mothur_cmd+"' >> "+file
   exec_sys(cmd)
### add_to_mothur_cmd ###

def exec_mothur( mothur_cmd ): #######################
   ts=str(int(time.time()))
   fn='mothur_batch'+ts
   cmd='echo '+"'"+mothur_cmd+"' > "+fn
   exec_sys(cmd)
   # quit()
   mothur_cmd='quit()'
   cmd='echo '+"'"+mothur_cmd+"' >> "+fn
   exec_sys(cmd)
   # Execute Mothur command  #########################
   cmd='./mothur '+fn
   exec_sys(cmd)
### exec_mothur ###

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

##### TomCat ##################
#if os.path.isdir('/var/lib/tomcat7/webapps/vfs'):
#   exec_sys('sudo ln -s /var/lib/tomcat7/webapps/vfs /home/ubuntu/WoRkDiR' )

##### Predefined and calculated options

for key in ['LOG_FILE','NUM_OF_PROC']:
   if(key not in config.keys()):
      config[key]=''

if(''==config['LOG_FILE']):
   config['LOG_FILE']='logfile.txt'

#config['LOG_FILE']='logfile.txt'
#work_dir='./'
#log_file=work_dir+config['LOG_FILE']

work_dir=os.getcwd()+'/'
log_file=work_dir+config['LOG_FILE']

send2log( 'MOTHUR pipeline started', log_file )

# get env.json if available
if os.path.isfile('./env.json'):
   send2log( 'env.json=', log_file )
   syscall( 'cat ./env.json >> '+log_file)
   send2log( "\n", log_file )

# get number of cores
config['NUM_OF_PROC']=syscall('cat /proc/cpuinfo  | grep processor | wc -l')
num_proc=int(config['NUM_OF_PROC'])
if(num_proc > 1):
   num_proc-=1
config['NUM_OF_PROC']=str(num_proc)
num_proc=config['NUM_OF_PROC']
send2log( 'number of cores='+config['NUM_OF_PROC'], log_file )

# get machine's memory
config['MEMORY']=syscall("cat /proc/meminfo | grep MemTotal | awk '{ print $2 }'")
mem=int(config['MEMORY'])
send2log( 'Memory='+config['MEMORY']+'KB', log_file )

w="MOTHUR pipeline configuration\n"
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
for key in ['FLIP','KEEPFIRST','MAXAMBIG','MAXFLOWS','MAXHOMOP','MINFLOWS','MINLENGTH',\
            'CORE_DIVERSITY_ANALYSES','BOOTSTRAPPED_TREE','BS_LIST','STABILITY_FILE',\
            'OPTIMIZE','CRITERIA','PDIFFS','COMP_WITH_DACC','MAP_FILE','DESIGN_MAP_FILE']:
   if(key not in config.keys()):
      config[key]=''

if(''==config['OPTIMIZE']):
   config['OPTIMIZE']='start-end'
if(''==config['CRITERIA']):
   config['CRITERIA']='90'
if (''==config['MAP_FILE']):
   config['MAP_FILE']=config['DESIGN_MAP_FILE']
if (''!=config['DESIGN_MAP_FILE']):
   config['MAP_FILE']=config['DESIGN_MAP_FILE']

send2log("The Mapping file is now set to " +config['MAP_FILE'], log_file)

if len(config['FLIP'])>1:
   config['FLIP']=config['FLIP'][0]

# Generate -c option for core_diversity_analyses.py
config['C_OPT']=''
map_file=open( work_dir+config['MAP_FILE'], 'r')
l=[]
for line in map_file:
   if("" == line): # check for end of file
      break
   s=line.rstrip("\n")
   s.strip()
   if("" == s): # ignore empty lines
      continue
   del l[:] # clear list
   l=s.split("\t")
   for j in range( 1,len(l) ):
      if 'description' in l[j].lower():
         break;
      if len( config['C_OPT'] ) >3:
         config['C_OPT']= config['C_OPT']+','+l[j]
      if 'treatment' in l[j].lower():
         config['C_OPT']=l[j] # start columns' collection
   break
map_file.close()
if len( config['C_OPT'] ) <3:
   config['C_OPT']='TreatmentGroup'

# Generate oligo and design file
if ('454_SFF_FILE' == config['INPUT_TYPE'] ) or ('IONTORRENT_SFF_FILE' == config['INPUT_TYPE']) :
   # unzip sff files if they are zipped
   w=''
   w=syscall('ls *.zip')
   if(''!=w):
      zip_list=w.split()
      for zip_file in zip_list:
         cmd='unzip -oqj '+gz_file+' >> ../'+log_file+' 2>&1'
         exec_sys(cmd)

   # Generate OLIGO and DESIGN file from map file
   send2log( 'Generating OLIGO and DESIGN file from map file...', log_file )
   config['OLIGO_FILE']='oligo.txt'
   config['DESIGN_FILE']='rawfile.design'
   map_file=open( work_dir+config['MAP_FILE'], 'r')
   # #SampleID       BarcodeSequence LinkerPrimerSequence    ReversePrimer   TreatmentGroup  Description
   # SRS020478_Saliva        TGCATATACG      ATTACCGCGGCTGCTGG               Saliva  FROM HPM
   # SRS020592_Saliva        TGTACAGCTC      ATTACCGCGGCTGCTGG               Saliva  FROM HPM
   # SRS020649_Saliva        CTATGTACAG      ATTACCGCGGCTGCTGG               Saliva  FROM HPM

   oligo_file=open( work_dir+config['OLIGO_FILE'], 'w')
   # forward ATTACCGCGGCTGCTGG
   # barcode TGCATATACG SRS020470_Stool
   # barcode TGTACAGCTC SRS020478_Saliva
   # barcode CTATGTACAG SRS020584_Stool

   design_file=open( work_dir+config['DESIGN_FILE'], 'w')
   # group   tissue
   # SRS021073_Saliva        Saliva
   # SRS020819_Saliva        Saliva
   # SRS021109_Stool Stool

   first_line=1
   samples_list=[]
   n_Barcode=0
   n_linkerPrimer=0
   n_Treatment=0
   l=[]
   for line in map_file:
      if("" == line): # check for end of file
         break
      s=line.rstrip("\n")
      s.strip()
      if("" == s): # ignore empty lines
         continue
      if "#"==s[:1] and 0==n_Barcode and 0==n_linkerPrimer and 0==n_Treatment:  # header line determine numbers for BarcodeSequence LinkerPrimerSequence
         # check map file
         for column in ['#SampleID','BarcodeSequence','LinkerPrimerSequence','TreatmentGroup']:
            if column not in s:
               send2log( 'ERROR: mandatory column:'+column+' is not in mapping file. Can not continue', log_file )
               sys.exit(77)
         del l[:] # clear list
         l=s.split("\t")
         for j in range( 1,len(l) ):
            if 'BarcodeSequence'== l[j]:
               n_Barcode=j
               continue
            if 'LinkerPrimerSequence'== l[j]:
               n_linkerPrimer=j
               continue
            if 'TreatmentGroup'== l[j]:
               n_Treatment=j
               continue
         if (0==n_Barcode or 0==n_linkerPrimer):
            send2log( 'ERROR: BarcodeSequence or LinkerPrimerSequence columns does not exist in mapping file. Can not continue', log_file )
            sys.exit(77)

         design_file.write("group\ttissue\n")
      else: # non-header lines with samples
         del l[:] # clear list
         l=s.split("\t")
         samples_list.append(l[0])
         if 1==first_line:
            oligo_file.write("forward\t"+l[n_linkerPrimer]+"\n")
            first_line=0

         oligo_file.write("barcode\t"+l[n_Barcode]+"\t"+l[0]+"\n")
         design_file.write(l[0]+"\t"+l[n_Treatment]+"\n")
   map_file.close()
   oligo_file.close()
   design_file.close()

# get necessary files from s3
for res_file in ['97_otu_map.txt','LookUp_Titanium.pat','silva.bacteria.fasta',\
            'gg_13_5_97.fasta','gg_13_5_97.gg.tax']:
   if not( os.path.isfile('./'+res_file) ):
send2log( 'Work folder '+work_dir+' contains:' , log_file )
syscall( 'ls >> '+log_file )


if '454_SFF_FILE' == config['INPUT_TYPE']:

   config['RAW_FILE']=os.path.splitext(config['RAW_FILE_FULL'])[0]
   config['RAW_FILE_EXT']=os.path.splitext(config['RAW_FILE_FULL'])[1][1:]
   raw_file=work_dir+config['RAW_FILE']
   if (config['RAW_FILE_FULL'] != 'rawfile.sff') and (not os.path.isfile('rawfile.sff') ):
      exec_sys('mv '+config['RAW_FILE_FULL']+' rawfile.sff' )
   ### Processing Step 1: Extract Reads from raw sff file (454) and trim to a minimum length

   send2log('Processing Step 1: Extract Reads from raw sff file (454) and trim to a minimum length STARTED', log_file)
   mothur_batch=work_dir+'mothur_p1.batch'
   cmd="echo '# Processing Step 1: Extract Reads from raw sff file (454) and trim to a minimum length' >"+mothur_batch
   exec_sys(cmd)

   # sffinfo(sff=rawfile.sff, flow=T)
   add2mothur_cmd('sffinfo(sff=rawfile.sff)',mothur_batch)

   # summary.seqs(fasta=rawfile.fasta)
   add2mothur_cmd('summary.seqs(fasta=rawfile.fasta)',mothur_batch)

   # trim.flows(flow=rawfile.flow, oligos=oligo.txt, pdiffs=2, bdiffs=1, processors=2, minflows=360, maxflows=720)"
   add2mothur_cmd('trim.flows(flow=rawfile.flow'\
             +', oligos='+config['OLIGO_FILE']\
             +', pdiffs='+config['PDIFFS']+', bdiffs='+config['BDIFFS']+', processors='+num_proc \
             +', minflows='+config['MINFLOWS']+', maxflows='+config['MAXFLOWS']+')',mothur_batch)

   # shhh.flows(file=rawfile.flow.files, processors=8, lookup=/bcbb/quinones/software/mothur_1.32.1/mothur/LookUp_Titanium.pat)
   add2mothur_cmd('shhh.flows(file=rawfile.flow.files'\
             +', processors='+num_proc\
             +', lookup=LookUp_Titanium.pat)',mothur_batch)

   # trim.seqs(fasta=rawfile.shhh.fasta, name=rawfile.shhh.names, oligos=stool_saliva_SRR057663.oligo_sort.txt, pdiffs=2, bdiffs=1, maxhomop=8, minlength=200, flip=T, processors=8)
   add2mothur_cmd('trim.seqs(fasta=rawfile.shhh.fasta'\
             +', name=rawfile.shhh.names'\
             +', oligos='+config['OLIGO_FILE']\
             +', pdiffs='+config['PDIFFS']+', bdiffs='+config['BDIFFS']\
             +', maxhomop='+config['MAXHOMOP']+', minlength='+config['MINLENGTH']+', flip='+config['FLIP']\
             +', processors='+num_proc+')',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Processing Step 1: Extract Reads from raw sff file (454) and trim to a minimum length DONE',log_file )

if 'IONTORRENT_SFF_FILE' == config['INPUT_TYPE']:

   # unzip reads archive
   send2log( 'unzip reads archive STARTED', log_file)
   cmd='unzip -oqj '+config['READS_ZIP']+' >>'+log_file+' 2>&1'
   exec_sys(cmd)
   send2log( 'unzip archive DONE', log_file)

   # ungzip gzipped files if any
   # create list of *.gz files
   w=''
   w=syscall('ls *.gz')
   if(''!=w):
      gz_list=w.split()
      for gz_file in gz_list:
         cmd='gzip -d '+gz_file+' >> '+log_file+' 2>&1'
         exec_sys(cmd)

   # Processing Step 1: Extract Reads from raw sff file (454) and trim to a minimum length
   # the original sff file has 19 samples but I will only process 4 for this test.
   send2log('Processing Step 1: Extract Reads from raw sff file (IonTorrent) and trim to a minimum length STARTED', log_file)

   # create list of *.sff files
   w=syscall('ls *.sff')  
   sff_list=w.split()
   file_str='-'.join(sff_list)
   # print file_str

   mothur_batch=work_dir+'mothur_p1.batch'
   cmd="echo '# Processing Step 1: Extract Reads from raw sff file (IonTorrent) and trim to a minimum length' >"+mothur_batch
   exec_sys(cmd)

   # because sff.multiple command is not working properly, the commands below will be used instead.
   # for faster demo, I am picking only the 57,61,68 and 78 for the step 'merge.files' but all the input sff files should be used in use script.
   # mothur "#sffinfo(sff=IonOct57.sff-IonOct61.sff-IonOct68.sff-IonOct78.sff)
   add2mothur_cmd('sffinfo(sff='+file_str+')',mothur_batch)

   file_str=file_str.replace("sff","flow")
   # print file_str

   # mothur "#merge.files(input=IonOct57.flow-IonOct61.flow-IonOct68.flow-IonOct78.flow, output=rawfile.flow)"
   add2mothur_cmd('merge.files(input='+file_str+', output=rawfile.flow)',mothur_batch)

   file_str=file_str.replace("flow","fasta")
   # print file_str

   # mothur "#merge.files(input=IonOct57.fasta-IonOct61.fasta-IonOct68.fasta-IonOct78.fasta, output=rawfile.fasta)"
   add2mothur_cmd('merge.files(input='+file_str+', output=rawfile.fasta)',mothur_batch)

   # mothur "#summary.seqs(fasta=rawfile.fasta)"
   add2mothur_cmd('summary.seqs(fasta=rawfile.fasta)',mothur_batch)

   # mothur "#trim.flows(flow=rawfile.flow, oligos=oligo.txt, pdiffs=1, bdiffs=1, processors=8, order=I)"
   add2mothur_cmd('trim.flows(flow=rawfile.flow'\
             +', oligos='+config['OLIGO_FILE']\
             +', pdiffs='+config['PDIFFS']+', bdiffs='+config['BDIFFS']+', processors='+num_proc\
             +', order=I)',mothur_batch)

   # mothur "#shhh.flows(file=rawfile.flow.files, processors=8, order=I, lookup=/bcbb/quinones/software/mothur_1.31.2/mothur/LookUp_Titanium.pat)"
   add2mothur_cmd('shhh.flows(file=rawfile.flow.files'\
             +', processors='+num_proc+', order=I'\
             +', lookup=LookUp_Titanium.pat)',mothur_batch)

   # mothur "#trim.seqs(fasta=rawfile.shhh.fasta, name=rawfile.shhh.names, oligos=oligo.txt, pdiffs=1, bdiffs=1, maxhomop=8, 
   # minlength=200, flip=T, processors=8, keepfirst=430, maxambig=0)"
   add2mothur_cmd('trim.seqs(fasta=rawfile.shhh.fasta'\
             +', name=rawfile.shhh.names'\
             +', oligos='+config['OLIGO_FILE']\
             +', pdiffs='+config['PDIFFS']+', bdiffs='+config['BDIFFS']\
             +', maxhomop='+config['MAXHOMOP']+', minlength='+config['MINLENGTH']+', flip='+config['FLIP']\
             +', processors='+num_proc+', keepfirst='+config['KEEPFIRST']\
             +', maxambig='+config['MAXAMBIG']+')',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   send2log( 'Processing Step 1: Extract Reads from raw sff file (IonTorrent) and trim to a minimum length DONE',log_file )
   exec_sys(cmd)

if ('454_SFF_FILE' == config['INPUT_TYPE'] ) or ('IONTORRENT_SFF_FILE' == config['INPUT_TYPE']) :

   ### Processing Step 2: Clusters redundant sequences and aligns to the SILVA based reference alignment provided

   send2log('Processing Step 2: Clusters redundant sequences and aligns to the SILVA based reference alignment provided STARTED', log_file)
   mothur_batch=work_dir+'mothur_p2.batch'
   cmd="echo '# Processing Step 2: Clusters redundant sequences and aligns to the SILVA based reference alignment provided' >"+mothur_batch
   exec_sys(cmd)

   # unique.seqs(fasta=rawfile.shhh.trim.fasta, name=rawfile.shhh.trim.names)
   add2mothur_cmd('unique.seqs(fasta=rawfile.shhh.trim.fasta, name=rawfile.shhh.trim.names)',mothur_batch)

   # summary.seqs(fasta=rawfile.shhh.trim.unique.fasta, name=rawfile.shhh.trim.unique.names, processors=8)
   add2mothur_cmd('summary.seqs(fasta=rawfile.shhh.trim.unique.fasta,'\
            +' name=rawfile.shhh.trim.unique.names, processors='+num_proc+')',mothur_batch)

   # align.seqs(fasta=rawfile.shhh.trim.unique.fasta, reference=silva.bacteria.fasta, processors=8, flip=T)
   add2mothur_cmd('align.seqs(fasta=rawfile.shhh.trim.unique.fasta,'\
            +' reference=silva.bacteria.fasta, processors='+num_proc+', flip=T)',mothur_batch)

   # screen.seqs(fasta=rawfile.shhh.trim.unique.align, name=rawfile.shhh.trim.unique.names, group=rawfile.shhh.groups, optimize=start, criteria=97, processors=8)
   add2mothur_cmd('screen.seqs(fasta=rawfile.shhh.trim.unique.align,'\
            +' name=rawfile.shhh.trim.unique.names,'\
            +' group=rawfile.shhh.groups, optimize='+config['OPTIMIZE']+', criteria='+config['CRITERIA']+', processors='+num_proc+')',mothur_batch)

   # filter.seqs(fasta=rawfile.shhh.trim.unique.good.align, vertical=T, trump=., processors=8)
   add2mothur_cmd('filter.seqs(fasta=rawfile.shhh.trim.unique.good.align,'\
            +' vertical=T, trump=., processors='+num_proc+')',mothur_batch)

   # unique.seqs(fasta=rawfile.shhh.trim.unique.good.filter.fasta, name=rawfile.shhh.trim.unique.good.names)
   add2mothur_cmd('unique.seqs(fasta=rawfile.shhh.trim.unique.good.filter.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.names)',mothur_batch)

   # pre.cluster(fasta=rawfile.shhh.trim.unique.good.filter.unique.fasta, name=rawfile.shhh.trim.unique.good.filter.names, group=rawfile.shhh.good.groups, diffs=2)
   add2mothur_cmd('pre.cluster(fasta=rawfile.shhh.trim.unique.good.filter.unique.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.filter.names,'\
            +' group=rawfile.shhh.good.groups, diffs=2)',mothur_batch)

   # chimera.uchime(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.fasta, name=rawfile.shhh.trim.unique.good.filter.unique.precluster.names,
   #    group=rawfile.shhh.good.groups, processors=8)
   add2mothur_cmd('chimera.uchime(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.filter.unique.precluster.names,'\
            +' group=rawfile.shhh.good.groups, processors='+num_proc+')',mothur_batch)

   # remove.seqs(accnos=rawfile.shhh.trim.unique.good.filter.unique.precluster.uchime.accnos, fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.fasta,
   #    name=rawfile.shhh.trim.unique.good.filter.unique.precluster.names, group=rawfile.shhh.good.groups, dups=T)
   add2mothur_cmd('remove.seqs(accnos=rawfile.shhh.trim.unique.good.filter.unique.precluster.uchime.accnos,'\
            +' fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.filter.unique.precluster.names,'\
            +' group=rawfile.shhh.good.groups, dups=T)',mothur_batch)

   # classify.seqs(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.fasta, name=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.names,
   #    template=gg_13_5_99.fasta, taxonomy=gg_13_5_99.pds.tax, cutoff=80, processors=8, group=rawfile.shhh.good.pick.groups)
   add2mothur_cmd('classify.seqs(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.names,'\
            +' template=gg_13_5_97.fasta, taxonomy=gg_13_5_97.gg.tax, cutoff=80, processors='+num_proc+','\
            +' group=rawfile.shhh.good.pick.groups)',mothur_batch)

   #mothur "#remove.lineage(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.fasta,
   # name=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.names,
   # group=rawfile.shhh.good.pick.groups, taxonomy=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy,
   # taxon=Chloroplast-Mitochondria-unknown-Archaea-Eukaryota)"
   add2mothur_cmd('remove.lineage(fasta=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.fasta,'\
            +' name=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.names,'\
            +' group=rawfile.shhh.good.pick.groups,'\
            +' taxonomy=rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy,'\
            +' taxon=Chloroplast-Mitochondria-unknown-Archaea-Eukaryota)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Processing Step 2: Clusters redundant sequences and aligns to the SILVA based reference alignment provided DONE',log_file )

   ### Processing Step 3: OTU Clustering

   send2log('Processing Step 3: OTU Clustering STARTED', log_file)
   mothur_batch=work_dir+'mothur_p3.batch'
   cmd="echo '# Processing Step 3: OTU Clustering' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.pick.fasta rawfile.final.fasta)"
   add2mothur_cmd('system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.pick.fasta'\
         +' rawfile.final.fasta)',mothur_batch)

   # mothur "#system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.pick.names rawfile.final.names)"
   add2mothur_cmd('system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.pick.names'\
         +' rawfile.final.names)',mothur_batch)

   # mothur "#system(cp rawfile.shhh.good.pick.pick.groups rawfile.final.groups)"
   add2mothur_cmd('system(cp rawfile.shhh.good.pick.pick.groups'\
         +' rawfile.final.groups)',mothur_batch)

   # mothur "#system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy rawfile.final.taxonomy)"
   add2mothur_cmd('system(cp rawfile.shhh.trim.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy'\
         +' rawfile.final.taxonomy)',mothur_batch)

   # mothur "#dist.seqs(fasta=rawfile.final.fasta, cutoff=0.15, processors=8)"
   add2mothur_cmd('dist.seqs(fasta=rawfile.final.fasta, cutoff=0.15,'\
         +' processors='+num_proc+')',mothur_batch)

   # mothur "#dist.seqs(fasta=rawfile.final.fasta, cutoff=0.15, processors=8, output=phylip)"
   add2mothur_cmd('dist.seqs(fasta=rawfile.final.fasta, cutoff=0.15,'\
         +' processors='+num_proc+',output=phylip)',mothur_batch)

   # mothur "#cluster(column=rawfile.final.dist, name=rawfile.final.names)"
   add2mothur_cmd('cluster(column=rawfile.final.dist,'\
         +' name=rawfile.final.names)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Processing Step 3: OTU Clustering DONE',log_file )

   ### Analysis - Step 1a (alpha and beta diversity from OTUs)

   send2log('Analysis - Step 1a (alpha and beta diversity from OTUs) STARTED', log_file)
   mothur_batch=work_dir+'mothur_a1a.batch'
   cmd="echo '# Analysis - Step 1a (alpha and beta diversity from OTUs)' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#make.shared(list=rawfile.final.an.list, group=rawfile.final.groups, label=0.03)"
   add2mothur_cmd('make.shared(list=rawfile.final.an.list, group=rawfile.final.groups, label=0.03)',mothur_batch)

   # mothur "#classify.otu(list=rawfile.final.an.list, name=rawfile.final.names, taxonomy=rawfile.final.taxonomy, 
   # group=rawfile.final.groups, label=0.03, reftaxonomy=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.gg.tax)"
   add2mothur_cmd('classify.otu(list=rawfile.final.an.list, name=rawfile.final.names, taxonomy=rawfile.final.taxonomy,'\
         +' group=rawfile.final.groups, label=0.03, reftaxonomy=gg_13_5_97.gg.tax)',mothur_batch)

   # mothur "#tree.shared(shared=rawfile.final.an.shared, calc=thetayc-jclass)"
   add2mothur_cmd('tree.shared(shared=rawfile.final.an.shared, calc=thetayc-jclass)',mothur_batch)

   # mothur "#summary.single(shared=rawfile.final.an.shared)"
   add2mothur_cmd('summary.single(shared=rawfile.final.an.shared)',mothur_batch)

   # mothur "#rarefaction.single(shared=rawfile.final.an.shared)" 
   add2mothur_cmd('rarefaction.single(shared=rawfile.final.an.shared)',mothur_batch)

   #metastats needs the design file from user
   #mothur "#metastats(shared=rawfile.final.an.shared, design=Iontorent_demo.design)"
   add2mothur_cmd('metastats(shared=rawfile.final.an.shared, design='+config['DESIGN_FILE']+')',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Analysis - Step 1a (alpha and beta diversity from OTUs) DONE',log_file )

   ### Analysis - Step 1b Prepare files for processing with Qiime and Huttenhower tools

   send2log('Analysis - Step 1b Prepare files for processing with Qiime and Huttenhower tools STARTED', log_file)
   mothur_batch=work_dir+'mothur_a1b.batch'
   cmd="echo '# Analysis - Step 1b Prepare files for processing with Qiime and Huttenhower tools' >"+mothur_batch
   exec_sys(cmd)

   # make.lefse will not be done for IonTorrent test data
   # make.lefse(shared=rawfile.final.an.shared, label=0.03, design=??, constaxonomy=rawfile.final.an.0.03.cons.taxonomy)"
   if ('454_SFF_FILE' == config['INPUT_TYPE'] ):

      # make.lefse(shared=rawfile.final.an.shared, label=0.03, design=stool_saliva_SRR057663.design, constaxonomy=rawfile.final.an.0.03.cons.taxonomy)
      # add2mothur_cmd('make.lefse(shared=rawfile.final.an.shared, label=0.03,'\
      #     +' design=stool_saliva_SRR057663.design, constaxonomy=rawfile.final.an.0.03.cons.taxonomy)',mothur_batch)
      add2mothur_cmd('make.lefse(shared=rawfile.final.an.shared, label=0.03,'\
           +' design='+config['DESIGN_FILE']+', constaxonomy=rawfile.final.an.0.03.cons.taxonomy)',mothur_batch)

   # make biom for picrust
   # mothur "#make.biom(shared=rawfile.final.an.shared, label=0.03, reftaxonomy=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.gg.tax, 
   # constaxonomy=rawfile.final.an.0.03.cons.taxonomy"
   add2mothur_cmd('make.biom(shared=rawfile.final.an.shared, label=0.03, reftaxonomy=gg_13_5_97.gg.tax,'\
        +' constaxonomy=rawfile.final.an.0.03.cons.taxonomy)',mothur_batch)
   #    +' constaxonomy=rawfile.final.an.0.03.cons.taxonomy, picrust=97_otu_map.txt)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)

   # source /usr/local/stow/qiime180/qiime_software/activate.sh
   # biom summarize-table -i rawfile.final.an.0.03.biom -o rawfile.biom.summary.txt
   cmd='biom summarize-table -i rawfile.final.an.0.03.biom -o rawfile.biom.summary.txt'
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # core_diversity_analyses.py -o core_diversity/ -i rawfile.final.an.0.03.biom -m Iontorrent_demo.mapping 
   # -e 1000 --nonphylogenetic_diversity -c "Treatment"

   if os.path.isfile( config['MAP_FILE'] ):
      # check for Treatment or TreatmentGroup
      treatment='Treatment'
      work=syscall('grep TreatmentGroup '+config['MAP_FILE'])
      if len(work)>3:
         treatment='TreatmentGroup'
      #cmd='core_diversity_analyses.py -o core_diversity/ -i rawfile.final.an.0.03.biom -m '+config['MAP_FILE']\
      #    +" -e 1000 --nonphylogenetic_diversity -c \"Treatment\""
      #cmd='core_diversity_analyses.py -o core_diversity/ -i rawfile.final.an.0.03.biom -m '+config['MAP_FILE']\
      #    +" -e 1000 --nonphylogenetic_diversity -c \""+treatment+"\""
      cmd='core_diversity_analyses.py -o core_diversity/ -i rawfile.final.an.0.03.biom -m '+config['MAP_FILE']\
          +" -e 1000 --nonphylogenetic_diversity -c \""+config['C_OPT']+"\""
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

   cmd='make_otu_heatmap_html.py -i rawfile.final.an.0.03.biom -o OTU_Heatmap/'
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   send2log( 'Analysis - Step 1b Prepare files for processing with Qiime and Huttenhower tools DONE',log_file )

   ### Analysis - Step 2 (Phylotype analysis alternate workflow for beta diversity)

   send2log('Analysis - Step 2 (Phylotype analysis alternate workflow for beta diversity) STARTED', log_file)
   mothur_batch=work_dir+'mothur_a2.batch'
   cmd="echo '# Analysis - Step 2 (Phylotype analysis alternate workflow for beta diversity)' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#phylotype(taxonomy=rawfile.final.taxonomy)"
   add2mothur_cmd('phylotype(taxonomy=rawfile.final.taxonomy)',mothur_batch)                                                                                                                          

   # mothur "#count.seqs(name=rawfile.final.names, group=rawfile.final.groups)"
   add2mothur_cmd('count.seqs(name=rawfile.final.names, group=rawfile.final.groups)',mothur_batch)

   # mothur "#make.shared(list=rawfile.final.tx.list, count=rawfile.final.count_table, label=1)"
   add2mothur_cmd('make.shared(list=rawfile.final.tx.list, count=rawfile.final.count_table, label=1)',mothur_batch)

   # mothur "#system(cp rawfile.final.tx.shared rawfile.final.phylotype.shared)"
   add2mothur_cmd('system(cp rawfile.final.tx.shared rawfile.final.phylotype.shared)',mothur_batch)

   # mothur "#classify.otu(list=rawfile.final.tx.list, count=rawfile.final.count_table, 
   # taxonomy=rawfile.final.taxonomy, label=1, count=rawfile.final.count_table)"
   add2mothur_cmd('classify.otu(list=rawfile.final.tx.list, count=rawfile.final.count_table,'\
        +' taxonomy=rawfile.final.taxonomy, label=1, count=rawfile.final.count_table)',mothur_batch)

   # mothur "#tree.shared(shared=rawfile.final.phylotype.shared, calc=thetayc-jclass)"
   add2mothur_cmd('tree.shared(shared=rawfile.final.phylotype.shared, calc=thetayc-jclass)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Analysis - Step 2 (Phylotype analysis alternate workflow for beta diversity) DONE',log_file )

   ### Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots

   send2log('Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots STARTED', log_file)
   mothur_batch=work_dir+'mothur_a3.batch'
   cmd="echo '# Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#clearcut(phylip=rawfile.final.phylip.dist)"
   add2mothur_cmd('clearcut(phylip=rawfile.final.phylip.dist)',mothur_batch)

   # unifrac.unweighted(tree=rawfile.final.phylip.tre, name=rawfile.final.names, group=rawfile.final.groups, distance=lt, processors=8, random=F)
   #mothur "#unifrac.unweighted(tree=rawfile.final.phylip.tre, name=rawfile.final.names, 
   # group=rawfile.final.groups, distance=lt, processors=8, random=F)"
   add2mothur_cmd('unifrac.unweighted(tree=rawfile.final.phylip.tre, name=rawfile.final.names,'\
         +' group=rawfile.final.groups, distance=lt, processors='+num_proc+', random=F)',mothur_batch)

   # mothur "#unifrac.weighted(tree=rawfile.final.phylip.tre, name=rawfile.final.names, 
   # group=rawfile.final.groups, distance=lt, processors=8, random=F)"
   add2mothur_cmd('unifrac.weighted(tree=rawfile.final.phylip.tre, name=rawfile.final.names,'\
         + 'group=rawfile.final.groups, distance=lt, processors='+num_proc+', random=F)',mothur_batch)

   # mothur "#pcoa(phylip=rawfile.final.phylip.tre1.unweighted.phylip.dist)"
   add2mothur_cmd('pcoa(phylip=rawfile.final.phylip.tre1.unweighted.phylip.dist)',mothur_batch)

   # mothur "#pcoa(phylip=rawfile.final.phylip.tre1.weighted.phylip.dist)"
   add2mothur_cmd('pcoa(phylip=rawfile.final.phylip.tre1.weighted.phylip.dist)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots DONE',log_file )

# MiSeq input

if 'PAIR_FASTQ_FILE' == config['INPUT_TYPE']:

   # check map file and create STABILITY FILE and DESIGN FILE from map file
   send2log( 'Creating stability file:rawfile.files from ForwardFastqFile and ReverseFastqFile columns in mapping file...', log_file )
   send2log( 'Creating design file: rawfile_Map.design from  mapping file...', log_file )
   config['STABILITY_FILE']='rawfile.files'
   config['DESIGN_FILE']='rawfile_Map.design'

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
         del l[:] # clear list
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
   design_file.close()

   # currently we always use generated stability file
   #if ''==config['STABILITY_FILE'] and os.path.isfile("./"+config['STABILITY_FILE'] ):
   #   # rename STABILITY FILE
   #   if 'rawfile.files' != config['STABILITY_FILE']:
   #      cmd='mv ./'+config['STABILITY_FILE']+' ./rawfile.files >>'+log_file+' 2>&1'
   #      exec_sys(cmd)
   #else:
   #   # use generated from map file stability file
   #   syscall('mv stability_file.tmp rawfile.files')
   #config['STABILITY_FILE']='rawfile.files'
 
   # create design file from map file
   #cmd='/bin/bash create_map_design.sh '+config['MAP_FILE']
   #send2log( 'executing:'+cmd, log_file )
   #exec_sys(cmd)
   #config['DESIGN_FILE']='rawfile_Map.design'

   # unzip reads archive
   send2log( 'unzip reads archive STARTED', log_file)
   cmd='unzip -oqj '+config['READS_ZIP']+' >>'+log_file+' 2>&1'
   exec_sys(cmd)
   send2log( 'unzip archive DONE', log_file)

   # ungzip gzipped files if any
   # create list of *.gz files
   w=''
   w=syscall('ls *.gz 2>&1')
   if 'No such file' not in w :
      gz_list=w.split()
      for gz_file in gz_list:
         cmd='gzip -d '+gz_file+' >> '+log_file+' 2>&1'
         exec_sys(cmd)

   # Processing step 1.

   # init Mothur batch file for this step
   send2log('Processing step 1 STARTED', log_file)
   mothur_batch=work_dir+'mothur_p1.batch'
   cmd="echo '# Processing Step 1' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#make.contigs(file=rawfile.files, processors=4)"
   add2mothur_cmd('make.contigs(file='+config['STABILITY_FILE']+', processors='+num_proc+')',mothur_batch)

   # mothur "#summary.seqs(fasta=rawfile.trim.contigs.fasta, processors=4)"
   add2mothur_cmd('summary.seqs(fasta=rawfile.trim.contigs.fasta, processors='+num_proc+')',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)

   # check for NBases from rawfile.trim.contigs.summary
   maxlen='0'
   if os.path.isfile( 'rawfile.trim.contigs.summary' ):
      # maxlen=syscall( "cat ./rawfile.trim.contigs.summary | awk \'{print$4}\' | sort -nu | tail -1") # max value of column
      maxlen=syscall( "cat ./rawfile.trim.contigs.summary | awk \'{ sum += $4; n++ } END { if (n > 0) print sum / n; }\'") # average 
      send2log( 'checking NBases in rawfile.trim.contigs.summary, maxlen='+maxlen, log_file)
      i_maxlen=int( round( float(maxlen) )+1)
      if i_maxlen > int(config['MAXLENGTH']):
         send2log(config['MAXLENGTH']+' is smaller than nbases in rawfile.trim.contigs.summary: '+str(i_maxlen)+' corrected', log_file)
         config['MAXLENGTH']=str(i_maxlen);
   mothur_batch=work_dir+'mothur_p1c.batch'

   # mothur "#screen.seqs(fasta=rawfile.trim.contigs.fasta, group=rawfile.contigs.groups, maxambig=0, maxlength=275)"
   add2mothur_cmd('screen.seqs(fasta=rawfile.trim.contigs.fasta, group=rawfile.contigs.groups,'\
         +'  maxambig=0, maxlength='+config['MAXLENGTH']+')',mothur_batch)

   # mothur "#unique.seqs(fasta=rawfile.trim.contigs.good.fasta)"
   add2mothur_cmd('unique.seqs(fasta=rawfile.trim.contigs.good.fasta)',mothur_batch)

   #mothur "#count.seqs(name=rawfile.trim.contigs.good.names, group=rawfile.contigs.good.groups)"
   add2mothur_cmd('count.seqs(name=rawfile.trim.contigs.good.names, group=rawfile.contigs.good.groups)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)

   # get count of start and end for pcr.seqs
   cmd='head -n 1000 rawfile.trim.contigs.good.unique.fasta > rawfile.trim.contigs.good.unique.1000.fasta'
   send2log( 'executing: '+cmd, log_file)
   exec_sys(cmd)

   # mothur "#align.seqs(fasta=rawfile.trim.contigs.good.unique.1000.fasta, reference=/bcbb/microbiome_cloud_test/silva.bacteria.fasta, processors=4, flip=F)"
   cmd="./mothur \"#align.seqs(fasta=rawfile.trim.contigs.good.unique.1000.fasta, reference=silva.bacteria.fasta, processors="+num_proc+", flip=T)\""
   send2log( 'executing: '+cmd, log_file)
   exec_sys(cmd)

   # mothur "#summary.seqs(fasta=rawfile.trim.contigs.good.unique.1000.align)" > start-end.txt
   cmd="./mothur \"#summary.seqs(fasta=rawfile.trim.contigs.good.unique.1000.align)\" > start-end.txt"
   send2log( 'executing: '+cmd, log_file)
   exec_sys(cmd)

   # cat start-end.txt | grep 'Median' | awk '{print "start="$2 "\t" "end="$3}' > start-end.values.txt
   cmd="cat start-end.txt | grep 'Median' | awk '{print \"start=\"$2 \", \" \"end=\"$3}'"
   send2log( 'executing: '+cmd, log_file)
   start_end=syscall(cmd)
   send2log( 'start-end: '+start_end, log_file)

   ## the step below, takes the start and end values from txt file. A short script needs to be written to write proper command line as below)
   #mothur "#pcr.seqs(fasta=/bcbb/microbiome_cloud_test/silva.bacteria.fasta, start=13862, end=23444, keepdots=F, processors=4)"
   cmd="./mothur \"#pcr.seqs(fasta=silva.bacteria.fasta, "+start_end+", keepdots=F, processors="+num_proc+")\""
   send2log( 'executing: '+cmd, log_file)
   exec_sys(cmd)

   #mv /bcbb/microbiome_cloud_test/silva.bacteria.pcr.fasta silva.v4.fasta
   cmd="mv silva.bacteria.pcr.fasta silva.v4.fasta"
   send2log( 'executing: '+cmd, log_file)
   exec_sys(cmd)

   send2log( 'Processing step 1 DONE',log_file)

   # Processing step 2.

   send2log( 'Processing step 2 STARTED', log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_p2.batch'
   cmd="echo '# Processing Step 2' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#align.seqs(fasta=rawfile.trim.contigs.good.unique.fasta, reference=silva.v4.fasta, processors=4, flip=F)"
   add2mothur_cmd('align.seqs(fasta=rawfile.trim.contigs.good.unique.fasta, reference=silva.v4.fasta, processors='+num_proc+', flip=T)',mothur_batch)

   # mothur "#summary.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table)"
   add2mothur_cmd('summary.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table)',mothur_batch)

   # mothur "# screen.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table, 
   # summary=rawfile.trim.contigs.good.unique.summary, optimize=start-end-minlength, criteria=90)"
   add2mothur_cmd('screen.seqs(fasta=rawfile.trim.contigs.good.unique.align, count=rawfile.trim.contigs.good.count_table,'\
         +' summary=rawfile.trim.contigs.good.unique.summary, optimize=start-end-minlength, criteria='+config['CRITERIA']+')',mothur_batch)

   # mothur "#filter.seqs(fasta=rawfile.trim.contigs.good.unique.good.align, vertical=T, trump=.)"
   add2mothur_cmd('filter.seqs(fasta=rawfile.trim.contigs.good.unique.good.align, vertical=T, trump=.)',mothur_batch)

   # mothur "#unique.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.fasta, count=rawfile.trim.contigs.good.good.count_table)"
   add2mothur_cmd('unique.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.fasta,'\
        +' count=rawfile.trim.contigs.good.good.count_table)',mothur_batch)

   # mothur "#pre.cluster(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.fasta, 
   # count=rawfile.trim.contigs.good.unique.good.filter.count_table, diffs=2)"
   add2mothur_cmd('pre.cluster(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.fasta,'\
        +' count=rawfile.trim.contigs.good.unique.good.filter.count_table, diffs=2)',mothur_batch)

   # mothur "#chimera.uchime(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta, 
   # count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.count_table, dereplicate=t)"
   add2mothur_cmd('chimera.uchime(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta,'\
        +' count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.count_table, dereplicate=t)',mothur_batch)

   # mothur "#remove.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta, 
   # accnos=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.accnos)"
   add2mothur_cmd('remove.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.fasta,'\
        +' accnos=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.accnos)',mothur_batch)

   # mothur "#classify.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta, 
   # count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table, 
   # reference=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.fasta, 
   # taxonomy=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.gg.tax, cutoff=80)"
   add2mothur_cmd('classify.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta,'\
        +' count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table,'\
        +' reference=gg_13_5_97.fasta, taxonomy=gg_13_5_97.gg.tax, cutoff=80, probs=f)',mothur_batch)

   # mothur "#remove.lineage(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta, 
   # count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table, 
   # taxonomy=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy, 
   # taxon=Chloroplast-Mitochondria-unknown-Archaea-Eukaryota)"
   add2mothur_cmd('remove.lineage(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta,'\
        +' count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table,'\
        +' taxonomy=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy,'\
        +' taxon=Chloroplast-Mitochondria-unknown-Archaea-Eukaryota)',mothur_batch)

   ########## 30-JUN-2015 addition #### begin ############################
   # mothur "#split.abund(fasta=filename.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta,
   # count=filename.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.pick.count_table,
   # cutoff=1, accnos=true)"
   add2mothur_cmd('split.abund(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta,'\
        +' count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.count_table,'\
        +' cutoff=1, accnos=true)' ,mothur_batch)

   # Output File Names:
   # rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.pick.rare.count_table
   # rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.pick.abund.count_table
   # rare.accnos
   # abund.accnos
   # rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.rare.fasta
   # rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.abund.fasta

   # mothur "#remove.seqs(accnos=rare.accnos, taxonomy=filename.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy)"
   add2mothur_cmd('remove.seqs(accnos=rare.accnos,'\
        +' taxonomy=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy)',mothur_batch)
   ########## 30-JUN-2015 addition #### end ############################

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)
   send2log( 'Processing step 2 DONE', log_file )

   # Processing step 3.

   send2log( 'Processing step 3 OTU Clustering STARTED', log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_p3.batch'
   cmd="echo '# Processing Step 3 OTU Clustering' >"+mothur_batch
   exec_sys(cmd)

   ########## 30-JUN-2015 addition change corresponding copy commands ############################

   # instead of:
   # mothur "#system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta rawfile.final.fasta)"
   # add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta'\
   #      +'  rawfile.final.fasta)',mothur_batch)

   # add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.abund.fasta rawfile.final.fasta'\
   add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.abund.fasta'\
          +' rawfile.final.fasta)',mothur_batch)

   # instead of
   # mothur "#system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.count_table rawfile.final.count_table)"
   #add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.count_table'\
   #      +' rawfile.final.count_table)',mothur_batch)

   # mothur "#system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.abund.count_table rawfile.final.count_table)"
   add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.pick.abund.count_table'\
         +' rawfile.final.count_table)',mothur_batch)

   # instead of:
   # mothur "#system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy rawfile.final.taxonomy)"
   add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy'\
         +' rawfile.final.taxonomy)',mothur_batch)

   # mothur "#system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.pick.taxonomy rawfile.final.taxonomy)"
   add2mothur_cmd('system(cp rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.pick.taxonomy'\
         +' rawfile.final.taxonomy)',mothur_batch)

   ########## 30-JUN-2015 addition change corresponding copy commands ############################

   if int(num_proc)>4:
      np='4'
   else:
      np=num_proc

   # mothur "#cluster.split(fasta=rawfile.final.fasta, count=rawfile.final.count_table, taxonomy=rawfile.final.taxonomy, splitmethod=classify, taxlevel=4, processors=4)"
   add2mothur_cmd('cluster.split(fasta=rawfile.final.fasta, count=rawfile.final.count_table,'\
         + ' taxonomy=rawfile.final.taxonomy, splitmethod=classify, taxlevel=4, processors='+np+')',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)
   send2log( 'Processing step 3 DONE',log_file )

   # Analysis - Step 1a (alpha and beta diversity from OTUs).

   send2log( 'Analysis - Step 1a (alpha and beta diversity from OTUs) STARTED',log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_a1a.batch'
   cmd="echo '# Analysis - Step 1a (alpha and beta diversity from OTUs' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#make.shared(list=rawfile.final.an.unique_list.list, count=rawfile.final.count_table, label=0.03)"
   add2mothur_cmd('make.shared(list=rawfile.final.an.unique_list.list,'\
         +' count=rawfile.final.count_table, label=0.03)',mothur_batch)

   # mothur "#system(cp rawfile.final.an.unique_list.shared rawfile.final.otu.shared)"
   add2mothur_cmd('system(cp rawfile.final.an.unique_list.shared rawfile.final.otu.shared)',mothur_batch)

   # mothur "#metastats(shared=rawfile.final.otu.shared, design=../miseq_design.design)"
   add2mothur_cmd('metastats(shared=rawfile.final.otu.shared, design='+config['DESIGN_FILE']+')',mothur_batch)

   # mothur "#classify.otu(list=rawfile.final.an.unique_list.list, count=rawfile.final.count_table, 
   # taxonomy=rawfile.final.taxonomy, label=0.03, reftaxonomy=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.gg.tax)"
   add2mothur_cmd('classify.otu(list=rawfile.final.an.unique_list.list, count=rawfile.final.count_table,'\
         +' taxonomy=rawfile.final.taxonomy, label=0.03, reftaxonomy=gg_13_5_97.gg.tax)',mothur_batch)

   # mothur "#tree.shared(shared=rawfile.final.otu.shared, calc=thetayc-jclass)"
   add2mothur_cmd('tree.shared(shared=rawfile.final.otu.shared, calc=thetayc-jclass)',mothur_batch)

   # summary.single(shared=rawfile.final.otu.shared, calc=nseqs-coverage-sobs-invsimpson-chao).
   # add2mothur_cmd('summary.single(shared=rawfile.final.otu.shared, calc=nseqs-coverage-sobs-invsimpson-chao)',mothur_batch)
   add2mothur_cmd('summary.single(shared=rawfile.final.otu.shared)',mothur_batch)

   # mothur "#rarefaction.single(shared=rawfile.final.otu.shared)"
   add2mothur_cmd('rarefaction.single(shared=rawfile.final.otu.shared)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)
   send2log( 'Analysis - Step 1a (alpha and beta diversity from OTUs) DONE',log_file )

   # Analysis - Step 1b Create proper output files for LEfSe, Qiime plots

   send2log( 'Analysis - Step 1b Create proper output files for LEfSe, Qiime plots',log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_a1b.batch'
   cmd="echo '# Analysis - Step 1b Create proper output files for LEfSe, Qiime plots' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#make.lefse(shared=rawfile.final.otu.shared, design=miseq_mouse.design, 
   # constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy)"
   add2mothur_cmd('make.lefse(shared=rawfile.final.otu.shared, design='+config['DESIGN_FILE']+','\
           +' constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy)',mothur_batch)

   # mothur "#make.biom(shared=rawfile.final.otu.shared, constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy, 
   # picrust=/bcbb/microbiome_cloud_test/97_otu_map.txt, label=0.03, 
   # reftaxonomy=/bcbb/quinones/greengenes/gg_13_5_otus/gg_13_5_formothur/gg_13_5_97.gg.tax)"
   add2mothur_cmd('make.biom(shared=rawfile.final.otu.shared,'\
           +' constaxonomy=rawfile.final.an.unique_list.0.03.cons.taxonomy,'\
           +' picrust=97_otu_map.txt, label=0.03, reftaxonomy=gg_13_5_97.gg.tax)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file                                                                                                                                                        
   exec_sys(cmd)

   send2log( 'Analysis - Step 1b Prepare files for processing with Qiime and Huttenhower tools DONE',log_file )

   ### Analysis - Step 2 independent of Step 1 Phylotype analysis (alternative workflow for beta diversity) ###

   send2log( 'Analysis - Step 2 Phylotype analysis (alternative workflow for beta diversity) STARTED',log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_a2.batch'
   cmd="echo '# Analysis - Step 2 Phylotype analysis (alternative workflow for beta diversity)' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#phylotype(taxonomy=rawfile.final.taxonomy)"
   add2mothur_cmd('phylotype(taxonomy=rawfile.final.taxonomy)',mothur_batch)

   # mothur "#make.shared(list=rawfile.final.tx.list, count=rawfile.final.count_table, label=1)"
   add2mothur_cmd('make.shared(list=rawfile.final.tx.list, count=rawfile.final.count_table, label=1)',mothur_batch)

   # mothur "#system(cp rawfile.final.tx.shared rawfile.final.phylotype.shared)"
   add2mothur_cmd('system(cp rawfile.final.tx.shared rawfile.final.phylotype.shared)',mothur_batch)

   # mothur "#classify.otu(list=rawfile.final.tx.list, count=rawfile.final.count_table, taxonomy=rawfile.final.taxonomy, label=1)"
   add2mothur_cmd('classify.otu(list=rawfile.final.tx.list, count=rawfile.final.count_table,'\
         +' taxonomy=rawfile.final.taxonomy, label=1)',mothur_batch)

   # mothur "#tree.shared(shared=rawfile.final.phylotype.shared, calc=thetayc-jclass)"
   add2mothur_cmd('tree.shared(shared=rawfile.final.phylotype.shared, calc=thetayc-jclass)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Analysis - Step 2 Phylotype analysis (alternative workflow for beta diversity)  DONE',log_file )

   # Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots

   send2log( 'Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots STARTED',log_file )
   # init Mothur batch file for this step
   mothur_batch=work_dir+'mothur_a3.batch'
   cmd="echo '# Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plot' >"+mothur_batch
   exec_sys(cmd)

   # mothur "#dist.seqs(fasta=rawfile.final.fasta, output=phylip, processors=8)"
   add2mothur_cmd('dist.seqs(fasta=rawfile.final.fasta, output=phylip, processors='+num_proc+')',mothur_batch)

   # mothur "#clearcut(phylip=rawfile.final.phylip.dist)"
   add2mothur_cmd('clearcut(phylip=rawfile.final.phylip.dist)',mothur_batch)

   # mothur "#unifrac.unweighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table, distance=lt, processors=8, random=F)"
   add2mothur_cmd('unifrac.unweighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table,'\
            +' distance=lt, processors='+num_proc+', random=F)',mothur_batch)

   # mothur "#unifrac.weighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table, distance=lt, processors=8, random=F)"
   add2mothur_cmd('unifrac.weighted(tree=rawfile.final.phylip.tre, count=rawfile.final.count_table,'\
            +' distance=lt, processors='+num_proc+', random=F)',mothur_batch)

   # mothur "#pcoa(phylip=rawfile.final.phylip.tre1.unweighted.phylip.dist)"
   add2mothur_cmd('pcoa(phylip=rawfile.final.phylip.tre1.unweighted.phylip.dist)',mothur_batch)

   # this step is not in original script
   # pcoa(phylip=rawfile.final.phylip.tre1.weighted.phylip.dist).
   add2mothur_cmd('pcoa(phylip=rawfile.final.phylip.tre1.weighted.phylip.dist)',mothur_batch)

   # 13-NOV-2014 addition
   # mothur "#get.oturep(count=rawfile.final.count_table, fasta=rawfile.final.fasta, list=rawfile.final.an.unique_list.list, method=abundance, label=0.03)"
   add2mothur_cmd('get.oturep(count=rawfile.final.count_table, fasta=rawfile.final.fasta,'\
           +' list=rawfile.final.an.unique_list.list, method=abundance, label=0.03)',mothur_batch)

   # quit()
   add2mothur_cmd('quit()',mothur_batch)
   # execute mothur
   cmd='./mothur '+mothur_batch+' >>'+log_file
   exec_sys(cmd)
   send2log( 'Analysis Step 3: Phylogenetic tree approach, unifrac and pcoA plots DONE',log_file )

   ############################################  QIIME ##############################################
   # BELOW ARE THE QIIME STEPS.  To run qiime1.8 in HPC I used code below
   #       source /usr/local/stow/qiime180/qiime_software/activate.sh
   # # summarize table
   # sort biom - this is nice to have

   # run calculate_subsample.pl

   send2log( 'executing QIIME STEPS', log_file )

   # biom summarize-table -i rawfile.final.otu.0.03.biom -o otu_table.biom.summary.txt
   cmd='biom summarize-table -i rawfile.final.otu.0.03.biom -o otu_table.biom.summary.txt'
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # check that all samples are still in biom file:
   for sample in samples_list:
      work=syscall('grep '+sample+' ./otu_table.biom.summary.txt')
      if len(work)>2:
         send2log( 'Sample '+sample+' is in mapping file and BIOM file', log_file )
         # this sample is OK
      else:
         syscall( 'grep -v '+sample+' '+config['MAP_FILE']+' >map_file.tmp')
         syscall( 'mv map_file.tmp '+config['MAP_FILE'] )
         send2log( 'removing sample '+sample+' from mapping file', log_file )

   # check for Treatment or TreatmentGroup
   treatment='Treatment'
   work=syscall('grep TreatmentGroup '+config['MAP_FILE'])
   if len(work)>3:           
      treatment='TreatmentGroup'
   cmd='sort_otu_table.py -i rawfile.final.otu.0.03.biom'\
        +' -o rawfile.final.otu.0.03.sorted.biom'\
        +' -m '+config['MAP_FILE']+' -s '+treatment
   # sort_otu_table.py -i /bcbb/quinones/microbiome_cloud_project/MiSeq_SOP/rawfile.final.otu.0.03.biom 
   # -o /bcbb/quinones/microbiome_cloud_project/MiSeq_SOP/rawfile.final.otu.0.03.biom 
   # -m /bcbb/quinones/microbiome_cloud_project/MiSeq_SOP/HMPsample_barcode.mapping -s Treatment
   #cmd='sort_otu_table.py -i rawfile.final.otu.0.03.biom'\
   #    +' -o rawfile.final.otu.0.03.sorted.biom'\
   #    +' -m '+config['MAP_FILE']+' -s Treatment'

   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # Custom script to determine the number to subsample. Requires user input (fraction of max).
   # The number to subsample will be the smallest sample that passes the threshold.
   # Output: subsampling_summary.txt value for $sub
   # run calculate_subsample.pl

   sub=syscall('./calculate_subsample.pl -f '+config['FRACTION_OF_MAXIMUM_SAMPLE_SIZE']+' otu_table.biom.summary.txt 2> subsampling_summary.txt')
   send2log( 'sub='+sub, log_file )

   # diversity (in real pipeline using the perl script above, use $sub instead of -e 2000
   # core_diversity_analyses.py -o qiime_div/ --suppress_alpha_diversity \
   # -i rawfile.final.otu.0.03.sorted.biom -m /bcbb/quinones/microbiome_cloud_project/MiSeq_SOP/HMPsample_barcode.mapping \
   # --nonphylogenetic_diversity -c "Treatment" -e 2000

   #cmd='core_diversity_analyses.py -o qiime_div/ --suppress_alpha_diversity '\
   #    +' -i rawfile.final.otu.0.03.sorted.biom -m '+config['MAP_FILE']\
   #    +" --nonphylogenetic_diversity -c \"Treatment\" -e "+sub
   #cmd='core_diversity_analyses.py -o qiime_div/ --suppress_alpha_diversity '\
   #    +' -i rawfile.final.otu.0.03.sorted.biom -m '+config['MAP_FILE']\
   #    +" --nonphylogenetic_diversity -c \""+treatment+"\" -e "+sub
   cmd='core_diversity_analyses.py -o qiime_div/ --suppress_alpha_diversity '\
       +' -i rawfile.final.otu.0.03.sorted.biom -m '+config['MAP_FILE']\
       +" --nonphylogenetic_diversity -c \""+config['C_OPT']+"\" -e "+sub
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   #cmd='make_otu_heatmap_html.py -i rawfile.final.an.0.03.biom -o OTU_Heatmap/'
   cmd='make_otu_heatmap_html.py -i rawfile.final.otu.0.03.sorted.biom -o OTU_Heatmap/'
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # Run picrust (this step is not fully functional on the HPC cluster yet)
   # normalize_by_copy_number.py -i rawfile.final.otu.0.03.sorted.biom -o normalized_otus.biom
   # predict_metagenomes.py -i normalized_otus.biom -o metagenome_predictions.biom
   # categorize_by_function.py -i predicted_metagenomes.biom -c KEGG_Pathways -l 3 -o predicted_metagenomes.L3.biom
   # categorize_by_function.py -f -i predicted_metagenomes.biom -c KEGG_Pathways -l 3 -o predicted_metagenomes.L3.txt
#############################################################################

if 'NONE'!=config['BS_LIST']:
   if 'MAP_FILE' not in config.keys():
      config['MAP_FILE']=config['DESIGN_MAP_FILE']
   # create config file
   biom_file=syscall('ls rawfile.final*.biom | grep -v sorted')
   if len(biom_file) > 0:
      send2log( 'Checking for most similar samples in HMP DACC', log_file )
      send2log( 'for BIOM file:'+biom_file+" created by this pipeline: with mapping file: "+config['MAP_FILE'], log_file )
      fhc=open( 'beta_div_conf.csv', 'w')
      fhc.write('BIOM_FILE_0,'+biom_file+"\n")
      fhc.write('MAP_FILE_0,'+config['MAP_FILE']+"\n")
      fhc.write('BS_LIST,'+config['BS_LIST']+"\n")
      fhc.write("DACC_ONLY,YES\n")
      fhc.write("METRICS,bray_curtis\n")
      fhc.write("MAX_NUM,5\n")
      fhc.write("PIPELINE_TYPE,COMP_WITH_DACC\n")
      fhc.close()
      cmd="./beta_div.py beta_div_conf.csv >> "+log_file+" 2>&1"
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

send2log( 'Mothur Pipeline DONE',log_file )
