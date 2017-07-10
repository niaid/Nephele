#!/usr/bin/env python
import sys
from os import getenv
from sh import zip, wc
#, aws

ZIP_SYNC_AND_JP = zip.bake('--filesync', '--junk-paths')
line_count = wc.bake('-l')
# aws_cp_s3 = aws.bake('s3','cp', '--quiet')

NEPH_DEV_TEAM_ADDRS = ['philip.macmenamin@nih.gov', 'Ian.misner@nih.gov', 'quinonesm@niaid.nih.gov', 'webermn@niaid.nih.gov', 'david.liou@nih.gov', 'jennifer.dommer@nih.gov']

DEFAULT_AWS_TYPE = 'c3.4xlarge' # c3.8xlarge
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
HMP_OUT_DIR = 'HMP_compare_results'
PHYLOSEQ_IMAGES_DIR = 'taxa_plots_and_heatmaps'
HMP_DB_TAR = 'HMP_ref_dbs.tar.gz'
PICRUST_DIR = 'PICRUSt_data'


# this gets used to define what's in the ALL_RESULTS_ZIP_FILE_NAME archive
#               COMPUTE_CORE_MICROBIOME_OUT_DIR,
all_results = [JOINED_OUTS_OUT_DIR,
               SPLIT_LIB_OUT_DIR,
               PICK_OTUS_OUT_DIR,
               CORE_DIVERSITY_OUT_DIR,
               HEATMAP_OUT_DIR,
               JACKKNIFED_OUT_DIR,
               COLLATED_OUT_DIR,
               HMP_OUT_DIR,
               'validate_mapping_out_dir' ] # config_fname
FILES_TO_CP_TO_S3 = ('logfile.txt','WorkFolder.zip','PipelineResults.zip')
S3_BASE_BUCKET = 's3://nephele-pipelines-development/submissions/'

QIIME_SW_VERS  = ['QIIME 1.9.1: Quantitative Insights Into Microbial Ecology.',
                  'UCHIME 4.2',
                  'Mothur v.1.39.5',
                  'SORTMERNA v 2.0' ]

SORTMERNA_DB_NAME = dict()
SORTMERNA_DB_NAME['Greengenes_97'] = 'Greengenes_97/97_otus'
SORTMERNA_DB_NAME['Greengenes_99'] = 'Greengenes_99/99_otus'
SORTMERNA_DB_NAME['SILVA_97'] = 'SILVA_97/otus_16S'
SORTMERNA_DB_NAME['SILVA_99'] = 'SILVA_99/otus_16S'
SORTMERNA_DB_NAME['ITS_97'] = 'ITS_97/ver7_97_20_11_2016'
SORTMERNA_DB_NAME['ITS_99'] = 'ITS_99/ver7_99_20_11_2016'

HMP_REF_FASTA_FILE = dict()
HMP_REF_FASTA_FILE['Greengenes_97'] = 'Greengenes_97/97_otus.fasta'
HMP_REF_FASTA_FILE['Greengenes_99'] = 'Greengenes_99/99_otus.fasta'
HMP_REF_FASTA_FILE['SILVA_97'] = 'SILVA_97/otus_16S.fasta'
HMP_REF_FASTA_FILE['SILVA_99'] = 'SILVA_99/otus_16S.fasta'
HMP_REF_FASTA_FILE['ITS_97'] = 'ITS_97/sh_refs_qiime_ver7_97_20.11.2016.fasta'
HMP_REF_FASTA_FILE['ITS_99'] = 'ITS_99/sh_refs_qiime_ver7_99_20.11.2016.fasta'

HMP_REF_TAXONOMY_FILE = dict()
HMP_REF_TAXONOMY_FILE['Greengenes_97'] = 'Greengenes_97/97_otu_taxonomy.txt'
HMP_REF_TAXONOMY_FILE['Greengenes_99'] = 'Greengenes_99/99_otu_taxonomy.txt'
HMP_REF_TAXONOMY_FILE['SILVA_97'] = 'SILVA_97/majority_taxonomy_7_levels.txt'
HMP_REF_TAXONOMY_FILE['SILVA_99'] = 'SILVA_99/majority_taxonomy_7_levels.txt'
HMP_REF_TAXONOMY_FILE['ITS_97'] = 'ITS_97/sh_taxonomy_qiime_ver7_97_20.11.2016.txt'
HMP_REF_TAXONOMY_FILE['ITS_99'] = 'ITS_99/sh_taxonomy_qiime_ver7_99_20.11.2016.txt'

HMP_TREE_FILE = dict()
HMP_TREE_FILE['Greengenes_97'] = 'Greengenes_97/97_otus.tree'
HMP_TREE_FILE['Greengenes_99'] = 'Greengenes_99/99_otus.tree'
HMP_TREE_FILE['SILVA_97'] = 'SILVA_97/97_otus.tre'
HMP_TREE_FILE['SILVA_99'] = 'SILVA_99/99_otus.tre'
# HMP_TREE_FILE['ITS_97'] = 'HMP_ref_dbs/97_otus.tree'
# HMP_TREE_FILE['ITS_99'] = 'HMP_ref_dbs/99_otus.tree'


# often pipes will output a warning, and I'd like this not to clutter up logs
WARNINGS_LOG_NAME = 'warnings.txt'
LOG_FILE = 'logfile.txt'
