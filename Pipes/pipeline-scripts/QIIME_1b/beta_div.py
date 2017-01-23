#!/usr/bin/env python

##############################################################
# $Id$
# Project:   BETA DIVERSITY for Nephele project
# Language:  Python 2.7
# Author:    Alex Levitsky
# History:   April 2015 Start of development
##############################################################

__author__ = "Alex Levitsky"
__copyright__ = ""
__credits__ = ["Alex Levitsky"]
__license__ = ""
__version__ = "1.0.1-dev"
__maintainer__ = "Alex Levitsky"
__email__ = "levitskyaa@niaid.nih.gov"
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

def map_file_to_hash( map_file, biom_file, map_hash, check ): #########################
   fh=open( map_file, 'r')
   i=0
   l=[]
   for line in fh:
      if("" == line): # check for end of file
         break
      s=line.rstrip("\n")
      s.strip()
      if("" == s): # ignore empty lines
         continue
      del l[:] # clear list
      l=s.split("\t")
      if 0==i:
         desc_col_numb=0
         for j in range(len(l)):
            if l[j].lower().find('description') != -1:
               desc_col_numb=j
               break
         i=1
      else:
         # check for consistency with biom file
         if 1==check:
            exist_in_biom=syscall("grep "+l[0]+" "+biom_file)
            if len(exist_in_biom) >10:
               map_hash[l[0]]=l[desc_col_numb]
            else:
               print l[0]+" is not in "+biom_file 
         else:
            map_hash[l[0]]=l[desc_col_numb]
   fh.close()
### map_file_to_hash ###

def sort_distance_matrix( dist_matrix, map0, map1, max_num, from_sec_file_only, output_file ): #########################
   fh=open( dist_matrix, 'r')
   fho=open( output_file, 'w')
   # find maximum element in distance matrix to norm
   i=0
   l=[]
   max_dist=0.0
   for line in fh:
      if("" == line): # check for end of file
         break
      s=line.rstrip("\n")
      s.strip()
      if("" == s): # ignore empty lines
         continue
      del l[:] # clear list
      l=s.split("\t")
      # for header line
      if 0==i:
         i=1
      else:
         # for all other lines
         for j in range( 1,len(l) ):
            if float(l[j]) > max_dist:
               max_dist=float(l[j])

   fh.seek(0)
   # process file with distance matrix line by line
   i=0
   l=[]
   header={}
   for line in fh:
      if("" == line): # check for end of file
         break
      s=line.rstrip("\n")
      s.strip()
      if("" == s): # ignore empty lines
         continue
      del l[:] # clear list
      l=s.split("\t")
      if 0==i:
         # process header line
         for j in range(len(l)):
            header[j]=l[j]
         # print header,"\n"
         i=1
      else:
         # process data lines
         if l[0] in map0.keys():
            #print "For sample "+l[0]+" "+str(max_num)+" most similar samples are:"
            fho.write("For sample "+l[0]+" "+str(max_num)+" most similar samples are:\n")
            fho.write("\tSampleId\tDistance\tDescription\n")
            fhl=open( l[0]+'.list', 'w')
            fhl.write(l[0]+"\n")
            abun={}
            for j in range(1,len(l)):
               abun[header[j]]=str(float(l[j])/max_dist)
            count=0
            for x in sorted( abun, key=abun.get ):
               if ( 'YES'==from_sec_file_only ) and ( x in map0.keys() ):
                  continue
               if count<max_num:
                  if x!=l[0]:
                     fhl.write(x+"\n")
                  descr=""
                  if x in map0.keys():
                      descr=map0[x]
                  if x in map1.keys():
                      descr=map1[x]
                  fho.write("\t"+x+"\t"+abun[x]+"\t"+descr+"\n")
                  count=count+1
               else:
                  break
            fhl.close()
            fho.write("\n")
   fh.close()
   fho.close()
### sort_distance_matrix ###

def draw_graphs( graph_dir, biom_file, map_file, list_file, log_file ): #######################
   # Draw results
   os.mkdir(graph_dir)
   os.chdir(graph_dir)

   # filter_samples_from_otu_table.py -i v13_merged.biom -o selected1.biom --sample_id_fp ids1.txt -m  v13_merged_map.txt --output_mapping_fp selected1.map_txt
   cmd='filter_samples_from_otu_table.py -i ../'+biom_file+' -o selected.biom --sample_id_fp ../'+list_file+\
         ' -m ../'+map_file+' --output_mapping_fp selected.map_txt >> '+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # summarize_taxa.py -i selected1.biom -o taxonomy_summaries1/
   cmd='summarize_taxa.py -i selected.biom -o taxonomy_summaries/ >> '+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   #for tax_level in [2,3,4,5,6]:
   for tax_level in [2,4,6]:
      # plot_taxa_summary.py -i taxonomy_summaries/selected_L2.txt -o taxonomy_plot_L2/
      cmd='plot_taxa_summary.py -i taxonomy_summaries/selected_L'+str(tax_level)+'.txt -o taxonomy_plot_L'+\
            str(tax_level)+'/ >> '+log_file+" 2>&1"
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

   # make_otu_heatmap_html.py -i selected.biom -o OTU_Heatmap/
   cmd='make_otu_heatmap_html.py -i selected.biom -o OTU_Heatmap/ >> '+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # return to upper directory
   os.chdir('../')
### draw graphs ###

def comp_2_bioms( wdir, biom_0, biom_1, map_0, map_1, metrics, output_file, max_num, num_proc, from_sec_file_only, parallel, tree, log_file ): #######################
   os.mkdir(wdir)
   os.chdir(wdir)
   # Merge two BIOM files
   cmd='merge_otu_tables.py -i ../'+biom_0+',../'+biom_1+' -o '+'merged.biom >> '+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # Merge mapping files
   cmd='merge_mapping_files.py -m ../'+map_0+',../'+map_1+" -o merged_map.txt -n 'NoData' >> "+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   # Calculate beta diversity with euclidean or bray_curtis metrics
   if ('euclidean'==metrics) or ('bray_curtis'==metrics):
      #if "YES"==parallel:
      #     cmd='parallel_beta_diversity.py -i merged.biom -m '+metrics+' --jobs_to_start '+num_proc+' -o merged_dir >> '+log_file+" 2>&1"
      #else:
      #     cmd='beta_diversity.py -i merged.biom -m '+metrics+' -o merged_dir >> '+log_file+" 2>&1"
      cmd='beta_diversity.py -i merged.biom -m '+metrics+' -o merged_dir >> '+log_file+" 2>&1"
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

   # Calculate beta diversity with unweighted_unifrac metrics
   if ('unweighted_unifrac'==metrics) or ('weighted_unifrac'==metrics):
      if "YES"==parallel:
         cmd='parallel_beta_diversity.py -i merged.biom -m '+metrics+' --jobs_to_start '+num_proc+' -o merged_dir >> '+log_file+" 2>&1"
      else:
         cmd='beta_diversity.py -i merged.biom -m '+metrics+' -t '+tree+' -o merged_dir >> '+log_file+" 2>&1"
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

   # Calculate beta diversity with weighted_unifrac metrics
   if 'weighted_unifrac'==metrics:
      cmd='beta_diversity.py -i merged.biom -m '+metrics+' -t '+tree+' -o merged_dir >> '+log_file+" 2>&1"
      #cmd='parallel_beta_diversity.py -i merged.biom -m '+metrics+' --jobs_to_start '+num_proc+' -o merged_dir >> '+log_file+" 2>&1"
      send2log( 'executing:'+cmd, log_file )
      exec_sys(cmd)

   # Find most similar samples
   map0={}
   map1={}
   map_file_to_hash("../"+map_0,"../"+biom_0,map0,1)
   map_file_to_hash("../"+map_1,"../"+biom_1,map1,0)
   #map_file_to_hash("../"+map_1,map1)

   for key in map0.keys():
      if key in map1.keys():
         #print 'Map files have the same ID: ',key
         send2log('Map files have the same ID: '+key, log_file)

   send2log( 'executing: sort_distance_matrix(./merged_dir/'+metrics+"_merged.txt",log_file )
   sort_distance_matrix( "./merged_dir/"+metrics+"_merged.txt", map0, map1, int(max_num), from_sec_file_only, output_file )

   # Draw results
   for key in map0.keys():
      draw_graphs( key+'_plots', 'merged.biom', 'merged_map.txt', key+'.list', log_file )
   os.chdir('../')
### comp_2_bioms ###

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

   ##### Define optional and default parameters
   for key in ['PIPELINE_TYPE', 'BIOM_FILE_0', 'MAP_FILE_0', 'DACC_ONLY', 'MAX_NUM', 'PIPELINE_TYPE','METRICS','BS_LIST','PARALLEL']:
      if(key not in config.keys()):
         config[key]=''
   ##### Predefined and calculated options
   if(''==config['PIPELINE_TYPE']):
      config['PIPELINE_TYPE']='COMP_WITH_DACC'
   if(''==config['MAX_NUM']):
      config['MAX_NUM']='7'
   if(''==config['DACC_ONLY']):
      config['DACC_ONLY']='YES'
   if(''==config['METRICS']):
      config['METRICS']='bray_curtis'
   if(''==config['PARALLEL']):
      config['PARALLEL']='NO'
   if(''==config['BS_LIST']):
      config['BS_LIST']='NONE'

   config['DACC_ONLY']='YES'
   if int(config['MAX_NUM'])<1:
      config['MAX_NUM']=1
   if int(config['MAX_NUM'])>100:
      config['MAX_NUM']=100

   work_dir=os.getcwd()
   config['LOG_FILE']='logfile.txt'
   log_file=work_dir+'/'+config['LOG_FILE']

   send2log( 'Beta-diversity pipeline started', log_file )

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

   eff_num_proc=mem/(8*1024*1024)
   #print "Needed number of processors=", eff_num_proc
   if num_proc > eff_num_proc:
      config['NUM_OF_PROC']=str(eff_num_proc)
   send2log( 'effective number of cores='+config['NUM_OF_PROC'], log_file )

   w="Beta-diversity pipeline configuration\n"
   for k in sorted(config.keys()):
      config[k]=config[k].replace("\"", "_")
      config[k]=config[k].replace("\'", "_")
      w=w+k+','+config[k]+"\n"
   # print configuration to log file
   send2log( w, log_file )

   ####################################################
   os.chdir(work_dir)

   # get neccessary files from s3
   for res_file in ['otu_table_psn_v13.biom','otu_table_psn_v35.biom','v13_map_uniquebyPSN.txt','v35_map_uniquebyPSN.txt']:
      if not( os.path.isfile('./'+res_file) ):
         syscall('wget -q '+res_file)
   send2log( 'Work folder '+work_dir+' contains:' , log_file )
   syscall( 'ls >> '+log_file )

   if('COMP_WITH_DACC'==config['PIPELINE_TYPE']):
      if('NONE'==config['BS_LIST']):
         send2log( 'Nothing to do, exiting...', log_file )
         sys.exit(0)
      else:
         if 'ALL' in config['BS_LIST']:
             send2log( 'Using all HMP DACC body sites', log_file ) 
         else:
             send2log( 'Using following body sites '+config['BS_LIST'], log_file )
      for v in ['v13','v35']:
         if not ( 'ALL' in config['BS_LIST'] ):   # filter is not empty
            config['BS_LIST'].strip()
            send2log( 'using filter:'+config['BS_LIST'], log_file )
            bs_list=[]
            bs_list=config['BS_LIST'].split(':')

            b2compare2=v+'_filtered.biom'
            m2compare2=v+'_map_filtered.txt'
            ids_filtered=v+'_ids_filtered.txt'

            # create filtered map file

            fhi=open( v+'_map_uniquebyPSN.txt', 'r')
            fho=open( m2compare2+'2', 'w')
            fho_id=open( ids_filtered, 'w')
            l=[]
            for line in fhi:
               if "" == line: # check for end of file
                  break
               s=line.rstrip("\n")
               s.strip()
               if '#' == s[:1]:
                  fho.write(s+"\n")
               if("" == s): # ignore empty lines
                  continue
               del l[:] # clear list
               l=s.split("\t")
               if l[5] in bs_list:
                  fho.write(s+"\n")
                  fho_id.write(l[0]+"\n")
            fhi.close()
            fho.close()
            fho_id.close()

            # create filtered biom file and map files
            cmd='filter_samples_from_otu_table.py -i otu_table_psn_'+v+'.biom -o '+b2compare2+' --sample_id_fp '+ids_filtered+\
                      ' -m '+v+'_map_uniquebyPSN.txt --output_mapping_fp '+m2compare2+' >> '+log_file+" 2>&1"
            send2log( 'executing:'+cmd, log_file )
            exec_sys(cmd)
         else:
            b2compare2='otu_table_psn_'+v+'.biom'
            m2compare2=v+'_map_uniquebyPSN.txt'

         wdir="compare_"+config['BIOM_FILE_0']+"_with_"+"HMPDACC_"+v
         comp_2_bioms(  wdir, config['BIOM_FILE_0'], b2compare2, config['MAP_FILE_0'], m2compare2,\
               config['METRICS'], "most_similar_HMP_DAC_"+v+"_samples.txt", config['MAX_NUM'], config['NUM_OF_PROC'], config['DACC_ONLY'],\
               config['PARALLEL'], 'rep_set_'+v+'.tre', log_file )

   if('COMP_2_BIOMS'==config['PIPELINE_TYPE']):
      wdir="compare_"+config['BIOM_FILE_0']+"_with_"+config['BIOM_FILE_1']
      comp_2_bioms( wdir, config['BIOM_FILE_0'],  config['BIOM_FILE_1'], config['MAP_FILE_0'], config['MAP_FILE_1'], config['METRICS'],\
            "most_similar_samples.txt", config['MAX_NUM'], config['NUM_OF_PROC'], config['DACC_ONLY'], config['PARALLEL'], "", log_file )

   #############################################################################
   # Remove BIOM files
   cmd="rm -rf otu_table_psn_v13.biom  >> "+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)
   cmd="rm -rf otu_table_psn_v35.biom  >> "+log_file+" 2>&1"
   send2log( 'executing:'+cmd, log_file )
   exec_sys(cmd)

   send2log( 'Beta Diversity DONE',log_file )

if __name__ == "__main__":
    main()
