#!/usr/bin/env python
import sys
from os import getenv
from sh import zip, wc
#, aws

ZIP_SYNC_AND_JP = zip.bake('--filesync', '--junk-paths')
line_count = wc.bake('-l')
# aws_cp_s3 = aws.bake('s3','cp', '--quiet')

DEFAULT_AWS_TYPE = 'c3.8xlarge' # c3.8xlarge
JOINED_OUTS_OUT_DIR = 'joined_outs'
SPLIT_LIB_OUT_DIR = 'split_lib_out'
DENOISE_OUT_DIR = 'denoise_out'
QIIME_CHIMERA_CHECK_OUT_DIR = 'qiime_chimera_check_out'
PICK_OTUS_OUT_DIR = 'otus'
CORE_DIVERSITY_OUT_DIR = 'core_diversity'
ALPHA_RAREFACTION_OUT_DIR='alpha_rarefaction'
COMPUTE_CORE_MICROBIOME_OUT_DIR='core_microbiome'
HEATMAP_OUT_DIR = 'heat_map'
VALIDATE_MAPPING_OUT_DIR = 'validate_mapping_out'
JACKKNIFED_OUT_DIR = 'jackknifed'
PYNAST_ALIGNED_SEQS_OUT_DIR = PICK_OTUS_OUT_DIR + '/pynast_aligned_seqs'
COLLATED_OUT_DIR = 'nephele_outputs'
MIN_NUM_SAMPLES_FOR_CORE_DIV = 4
TAXA_PLOTS_OUT_DIR = 'taxa_plots'
TAXA_SUMMRY_PLOTS_OUT_DIR = TAXA_PLOTS_OUT_DIR + '/taxa_summary_plots/'
ALL_RESULTS_ZIP_FILE_NAME = 'PipelineResults.zip ' 
EVERYTHING_ZIP_FILE_NAME = 'WorkFolder.zip '
SCRIPTS_BUNDLE_ZIP_FILE_NAME = 'scripts_bundle.zip'
ZIP_RECURS_QUIET = 'zip -r -q   ' # --junk-paths <<- this makes zip fail if two files have the same name
PIGZ_RECURS_QUIET = 'pigz -r -q --zip'
REMOTE_WORK_DIR = 'remote_work_dir'
LOCAL_WORK_DIR = 'local_results_dir'
RUN_SCRIPT = 'run.sh'
CONFIG_FNAME = 'config.csv'
CONFIG_DEFAULT_FNAME = 'config_default.csv'
BARCODE_FORMAT_TYPES = ['Golay_12', 'Hamming_8', 'variable_length']
DEFAULT_OTU_PARAMS_FNAME = 'otus_params.txt'
DEFAULT_C_OPT = 'TreatmentGroup'
PROCESS_SFF_OUT_DIR = 'process_sff_out'
CHIMERA_FILE = 'CHIMERAS_FOUND.txt'

# this gets used to define what's in the ALL_RESULTS_ZIP_FILE_NAME archive
#               COMPUTE_CORE_MICROBIOME_OUT_DIR,
all_results = [JOINED_OUTS_OUT_DIR,
               SPLIT_LIB_OUT_DIR, 
               PICK_OTUS_OUT_DIR, 
               CORE_DIVERSITY_OUT_DIR, 
               HEATMAP_OUT_DIR,
               JACKKNIFED_OUT_DIR,
               COLLATED_OUT_DIR,
               'validate_mapping_out_dir' ] # config_fname
FILES_TO_CP_TO_S3 = ('logfile.txt','WorkFolder.zip','PipelineResults.zip')

QIIME_SW_VERS  = ['QIIME 1.9.1: Quantitative Insights Into Microbial Ecology.',
                  'UCHIME 4.2',
                  'Mothur v.1.36.1' ]

DB_V_TO_REF_FASTA_FILE = dict()
DB_V_TO_REF_FASTA_FILE['Greengenes_94'] = '/home/ubuntu/ref_dbs/rep_set/94_otus.fasta'
DB_V_TO_REF_FASTA_FILE['Greengenes_97'] = '/home/ubuntu/ref_dbs/rep_set/97_otus.fasta'
DB_V_TO_REF_FASTA_FILE['Greengenes_99'] = '/home/ubuntu/ref_dbs/rep_set/99_otus.fasta'
DB_V_TO_REF_FASTA_FILE['SILVA_97'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/rep_set/rep_set_16S_only/97/97_otus_16S.fasta'
DB_V_TO_REF_FASTA_FILE['SILVA_99'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/rep_set/rep_set_16S_only/99/99_otus_16S.fasta'
DB_V_TO_REF_FASTA_FILE['ITS_97'] = '/home/ubuntu/ref_dbs/its_12_11_otus/rep_set/97_otus.fasta'
DB_V_TO_REF_FASTA_FILE['ITS_99'] = '/home/ubuntu/ref_dbs/its_12_11_otus/rep_set/99_otus.fasta'

DB_V_TO_REF_TAXONOMY_FILE = dict()
DB_V_TO_REF_TAXONOMY_FILE['Greengenes_94'] = '/home/ubuntu/ref_dbs/taxonomy/94_otu_taxonomy.txt'
DB_V_TO_REF_TAXONOMY_FILE['Greengenes_97'] = '/home/ubuntu/ref_dbs/taxonomy/97_otu_taxonomy.txt'
DB_V_TO_REF_TAXONOMY_FILE['Greengenes_99'] = '/home/ubuntu/ref_dbs/taxonomy/99_otu_taxonomy.txt'
DB_V_TO_REF_TAXONOMY_FILE['SILVA_97'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/taxonomy/16S_only/97/taxonomy_7_levels.txt'
DB_V_TO_REF_TAXONOMY_FILE['SILVA_99'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/taxonomy/16S_only/99/taxonomy_7_levels.txt'
DB_V_TO_REF_TAXONOMY_FILE['ITS_97'] = '/home/ubuntu/ref_dbs/its_12_11_otus/taxonomy/97_otu_taxonomy.txt'
DB_V_TO_REF_TAXONOMY_FILE['ITS_99'] = '/home/ubuntu/ref_dbs/its_12_11_otus/taxonomy/99_otu_taxonomy.txt'

DB_V_TO_TREE_FILE = dict()
DB_V_TO_TREE_FILE['Greengenes_94'] = '/home/ubuntu/ref_dbs/trees/94_otus.tree'
DB_V_TO_TREE_FILE['Greengenes_97'] = '/home/ubuntu/ref_dbs/trees/97_otus.tree'
DB_V_TO_TREE_FILE['Greengenes_99'] = '/home/ubuntu/ref_dbs/trees/99_otus.tree'
DB_V_TO_TREE_FILE['SILVA_97'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/trees/97/97_otus.tre'
DB_V_TO_TREE_FILE['SILVA_99'] = '/home/ubuntu/ref_dbs/silva/SILVA123_QIIME_release/trees/99/99_otus.tre'
DB_V_TO_TREE_FILE['ITS_97'] = '/home/ubuntu/ref_dbs/trees/97_otus.tree'
DB_V_TO_TREE_FILE['ITS_99'] = '/home/ubuntu/ref_dbs/trees/99_otus.tree'


# often pipes will output a warning, and I'd like this not to clutter up logs
WARNINGS_LOG_NAME = 'warnings.txt'
