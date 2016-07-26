#!/usr/bin/python3
import os
import json
import csv
import cfg as neph_cfg
from collections import namedtuple
from itertools import groupby
import logging
from sh import mkdir, wget, unzip
from optparse import OptionParser
import subprocess
import multiprocessing
# get body site
# learn relevant sample IDs (#SampleID) from PSN file, write to a file.
# write every line of body site of interest (HMPbodysubsite) to a file.
# run filter_samples_from_otu_table.py using the above.
# done.
#     Steps for comparison (see logfile.txt)
# a) Merge biom files of user with with biom file for HMP (otu_table_psn_v13.biom) using qiime Script "merge_otu_tables.py"
# b) Merge mapping file of user with mapping file of HMP (v13_map_uniquebyPSN.txt) using qiime script "merge_mapping_files.py"
# c) Run beta diversity without a tree file and using bray_curtis using qiime script
# beta_diversity.py -i merged.biom -m bray_curtis -o merged_dir
# d) sort distance matrix using Alex custom script and parameters to select the closest matches (a defined number) and report the IDs of the HMP matches using the qiime script 
# f) filter biom file to retain only those IDs for the closest matches using qiime script (see line: filter_samples_from_otu_table.py -i ../merged.biom -o selected.biom --sample_id_fp ../S_023556.list -m ../merged_map.txt --output_mapping_fp selected.map_txt)
# g) run script in qiime to plot bargraphs

IDs_to_dist = namedtuple('IDs_to_dist', ['user_s_id','DACC_s_id','distance'] )
Sample = namedtuple('Sample', ['sample_id', 'fwd_fq_file'] )

class Cfg:
    _FILE_ROOT = '/home/ubuntu/ref_dbs/otus/beta_div_analysis_files/'

    DAC_body_sites = ['Anterior_nares',
                      'Attached_Keratinized_gingiva',
                      'Buccal_mucosa',
                      'Hard_palate',
                      'HMPbodysubsite',
                      'Left_Antecubital_fossa',
                      'Left_Retroauricular_crease',
                      'Mid_vagina',
                      'Palatine_Tonsils',
                      'Posterior_fornix',
                      'Right_Antecubital_fossa',
                      'Right_Retroauricular_crease',
                      'Saliva',
                      'Stool',
                      'Subgingival_plaque',
                      'Supragingival_plaque',
                      'Throat',
                      'Tongue_dorsum',
                      'Vaginal_introitus']
    composite_sites = ['Oral_cavity', 'Skin', 'Urogenital_tract']

    HMP_SPLT_OUT_DIR = 'hmp_split_lib_out_dir'
    USER_SPLT_OUT_DIR = 'user_split_lib_out_dir'    

    HMP_CLOSED_OTUS_OUT_DIR = 'hmp_closed_otus_out_dir'
    USER_CLOSED_OTUS_OUT_DIR = 'user_closed_otus_out_dir'
    DACC_BIOM_FILE = HMP_CLOSED_OTUS_OUT_DIR + '/otu_table.biom'
    USER_BIOM_FILE = USER_CLOSED_OTUS_OUT_DIR + '/otu_table.biom'

    MERGED_BIOM_FILE_OUT = 'user_dacc_merged.biom'
    MERGED_MAP_FILE_OUT = 'user_dacc_merged.map'
    BETA_PLOTS_OUT_DIR = 'beta_diversity_plots'
    TAX_LEVEL_PLOTTED = 4
    
    BETA_DIV_OUT_DIR = 'beta_diversity_outs'
    BETA_DIV_OUT_FNAME = BETA_DIV_OUT_DIR + '/bray_curtis_user_dacc_merged.txt'
    OTU_HEATMAP_OUT_DIR = 'OTU_Heatmap/'

def setup_logger( log_name ):
    formatter = logging.Formatter(fmt='[ %(asctime)s - %(levelname)s ] %(message)s\n')
    fh = logging.FileHandler('logfile_cmp_to_DACC.txt')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    return logger

def exec_cmnd( cmds, log ):
    if cmds is None:
        return    
    if isinstance(cmds, str):
        l = list()
        l.append( cmds )
        cmds = l        
    while len(cmds) > 0:
        cmd = cmds.pop()
        log.info( cmd )
        try:
            if cmd.startswith('mothur'): # this might not be needed
                os.system(cmd)
            else:
                e = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
                if len(e) > 0:
                    print(e)
        except subprocess.CalledProcessError as cpe:
            out_bytes = cpe.output       # Output generated before error

def gen_filter_cmnd( input_biom, sample_ids_file, mapping_fp, output_mapping_fp, output_biom ):
    return 'filter_samples_from_otu_table.py '\
        ' --input_fp=' + input_biom\
        + ' --sample_id_fp='+ sample_ids_file \
        + ' --mapping_fp=' + mapping_fp\
        + ' --output_mapping_fp='+ output_mapping_fp\
        + ' --output_fp=' + output_biom

def gen_summarize_taxa_cmd( biom_file, sample ):
    return 'summarize_taxa.py '\
        + ' --otu_table_fp=' + biom_file\
        + ' --output_dir=' + sample

def gen_merge_otu_tables_cmd(biom_file_a, biom_file_b):
    return 'merge_otu_tables.py '\
        + ' --input_fps=' + biom_file_a + ',' + biom_file_b\
        + ' --output_fp=' + Cfg.MERGED_BIOM_FILE_OUT

def gen_merge_map_files_cmd(map_file_a, map_file_b):
    return 'merge_mapping_files.py '\
        + ' --mapping_fps=' + ','.join([map_file_a, map_file_b])\
        + ' --no_data_value=NO_DATA'\
        + ' --output_fp=' + Cfg.MERGED_MAP_FILE_OUT

def gen_beta_diversity_cmd( biom_file ):
    return 'beta_diversity.py '\
        + ' --input_path=' + biom_file \
        + ' --metrics=bray_curtis'\
        + ' --output_dir=' + Cfg.BETA_DIV_OUT_DIR

def gen_beta_diversity_through_plots( biom_file, map_file, tree_file, out_dir ):
    return 'beta_diversity_through_plots.py '\
        + ' --otu_table_fp=' + biom_file \
        + ' --mapping_fp='+ map_file\
        + ' --tree_fp='+ tree_file\
        + ' --jobs_to_start=' + str(int(multiprocessing.cpu_count()))\
        + ' --parallel'\
        + ' --output_dir=' + out_dir
        
def gen_plot_taxa_summary_cmd( counts_fname, out_dir ):
    return 'plot_taxa_summary.py '\
        + ' --counts_fname=' + counts_fname\
        + ' --dir_path=' + out_dir

# this seems to hang
# def gen_make_otu_heatmap_cmd ( biom_file ):
#     return 'make_otu_heatmap.py '\
#         ' --otu_table_fp=' + biom_file\
#         + ' --imagetype=png'\
#         + ' --output_fp=' + Cfg.OTU_HEATMAP_OUT_DIR 

def find_max_float_in_file( fname ):
    with open(fname, 'r') as f_in:
        reader = csv.reader(f_in, delimiter='\t')
        next(reader) # ignore the first line
        max_vals = list( max(row[1:-1]) for row in reader )
        return float(max(max_vals))

def gen_sample_sample_dist_dict( user_samples, dist_matrix ):
    distances = list()
    samples = [ s.sample_id for s in user_samples ]
    with open(dist_matrix, 'r') as f_in:
        lines = f_in.read().strip().splitlines()
        sample_ids_top_line = lines.pop(0).split("\t")
        for line in lines:
            elts = line.split("\t")
            sample_row_id = elts.pop(0)
            if sample_row_id not in samples:
                continue
            for index, dist in enumerate(elts):
                sample_y = sample_ids_top_line[index]
                if sample_y == sample_row_id or sample_y in samples:
                    continue
                i = IDs_to_dist(user_s_id = sample_row_id, DACC_s_id = sample_y, distance = float(dist))
                distances.append(i)
    return distances

def print_n_samples_to_file( samples, n ):
    if n > len(samples):
        n = len(samples)
    user_s_id = samples[0].user_s_id
    if not os.path.isdir( user_s_id ):
        mkdir( user_s_id )
    fname = user_s_id + '/' + user_s_id + '.list'
    with open(fname, 'w') as f_out:
        print ("\t".join(['S_ID', 'Distance']), file=f_out)
        for i in range(0, n):
            print ("\t".join([ samples[i].DACC_s_id, str( samples[i].distance )]), file=f_out)
    return fname

def get_DACC_region_file( region ):
    fname = region + '_reads.zip'
    if not os.path.isfile(fname):
        wget('path_to_hmp_data' + fname)
        unzip('-o', fname)
    
def get_DACC_map_file (body_site, region_dacc):
    fname = 'path_to_hmp_data' + body_site + '_' + region_dacc +'.mapping.txt'
    if not os.path.isfile(os.path.basename(fname)):
        wget(fname)
    return os.path.basename(fname)

def gen_closed_reference_cmd( inputs, out_dir, ref_fasta_file, ref_taxonomy_file ):
    return  "pick_closed_reference_otus.py "\
        + " -i " + inputs\
        + " --output_dir=" + out_dir \
        + ' --reference_fp=' + ref_fasta_file \
        + ' --taxonomy_fp=' + ref_taxonomy_file \
        + ' --parallel'\
        + ' --jobs_to_start='+ str(int(multiprocessing.cpu_count() / 4))\
        + ' --force' 
        
def gen_split_lib_for_fastq_cmd( samples, dacc_map_file, out_dir ):
    inputs = list()          # seq file names
    sample_ids = list()      # all sample IDs        
    for sample in samples:
        inputs.append(sample.fwd_fq_file)
        sample_ids.append(sample.sample_id)
        s = 'split_libraries_fastq.py '\
            + ' --output_dir=' + out_dir\
            + ' --barcode_type=not-barcoded'\
            + ' --mapping_fps=' + dacc_map_file \
            + ' --phred_offset=64'\
            + ' -i ' + ','.join(inputs) \
            + ' --sample_ids=' + ','.join(sample_ids)
    return s

def gen_samples( fname ):
    with open(fname) as f:
        reader = csv.DictReader(f, delimiter='\t')
        samples = [ Sample( sample_id = row['#SampleID'],
                            fwd_fq_file = row['ForwardFastqFile'] ) for row in reader ]
        return samples
    
def main( inputs ):
    log = setup_logger('COMPARE_TO_HMP')
    DACC_map_file = get_DACC_map_file( inputs.body_site, inputs.region_dacc )
    DACC_reads_fname = get_DACC_region_file( inputs.region_dacc )
    DACC_samples = gen_samples( DACC_map_file )
    user_samples = gen_samples( inputs.map_file )
    
    exec_cmnd( gen_split_lib_for_fastq_cmd( DACC_samples, DACC_map_file, Cfg.HMP_SPLT_OUT_DIR),log)
    exec_cmnd( gen_split_lib_for_fastq_cmd( user_samples,
                                            inputs.map_file,
                                            Cfg.USER_SPLT_OUT_DIR), log)
    # for DACC
    exec_cmnd(gen_closed_reference_cmd( Cfg.HMP_SPLT_OUT_DIR + '/seqs.fna',
                                        Cfg.HMP_CLOSED_OTUS_OUT_DIR,
                                        neph_cfg.DB_V_TO_REF_FASTA_FILE[inputs.hmp_database],
                                        neph_cfg.DB_V_TO_REF_TAXONOMY_FILE[inputs.hmp_database] ),log)
    # for user
    exec_cmnd(gen_closed_reference_cmd( Cfg.USER_SPLT_OUT_DIR + '/seqs.fna',
                                        Cfg.USER_CLOSED_OTUS_OUT_DIR,
                                        neph_cfg.DB_V_TO_REF_FASTA_FILE[inputs.hmp_database],
                                        neph_cfg.DB_V_TO_REF_TAXONOMY_FILE[inputs.hmp_database] ),log)

    exec_cmnd(gen_merge_otu_tables_cmd( Cfg.DACC_BIOM_FILE, Cfg.USER_BIOM_FILE ), log)
    exec_cmnd(gen_merge_map_files_cmd( DACC_map_file, inputs.map_file ), log)
    exec_cmnd(gen_beta_diversity_cmd( Cfg.MERGED_BIOM_FILE_OUT ), log )
    exec_cmnd(gen_beta_diversity_through_plots( Cfg.MERGED_BIOM_FILE_OUT,
                                                Cfg.MERGED_MAP_FILE_OUT,
                                                neph_cfg.DB_V_TO_TREE_FILE[inputs.hmp_database],
                                                Cfg.BETA_PLOTS_OUT_DIR ), log)
    s_ids_to_dist = gen_sample_sample_dist_dict( user_samples, Cfg.BETA_DIV_OUT_FNAME )
    max_dist = find_max_float_in_file( Cfg.BETA_DIV_OUT_FNAME )
    by_dist = sorted(s_ids_to_dist, key=lambda i: (i.user_s_id, i.distance))
    normalized = list( IDs_to_dist( user_s_id = sample.user_s_id,
                                    DACC_s_id = sample.DACC_s_id,
                                    distance = sample.distance / max_dist) for sample in by_dist )

    for sample, items in groupby( normalized, key=lambda i: i.user_s_id ):
        group = list(items)
        if group[0].distance == 1:
            log.warning('Sample {0} is unrelated to DACC. Unable to perform further analysis.'
                        .format(sample))
        else:
            id_file = print_n_samples_to_file( group, int(inputs.nearest_n_samples) )
            exec_cmnd( gen_filter_cmnd( Cfg.MERGED_BIOM_FILE_OUT,
                                        id_file,
                                        Cfg.MERGED_MAP_FILE_OUT,
                                        id_file + '.map',
                                        id_file + '.biom'), log )
            exec_cmnd( gen_summarize_taxa_cmd(id_file + '.biom', sample), log)
            in_fname_base = id_file + '_L' + str(Cfg.TAX_LEVEL_PLOTTED)
            exec_cmnd( gen_plot_taxa_summary_cmd(in_fname_base + '.txt', sample), log)
            #           exec_cmnd( gen_make_otu_heatmap_cmd( id_file + '.biom' ), log)
    
if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--body_site",
                      type = "choice",
                      choices = Cfg.DAC_body_sites + Cfg.composite_sites,
                      help="Select one of:" + ','.join(Cfg.composite_sites + Cfg.DAC_body_sites) )
    parser.add_option( "--map_file", type = "string" )
    parser.add_option( "-n", "--nearest_n_samples", type = "int") # MAX_NUM
    parser.add_option( "--hmp_database", type = "choice", choices = ["Greengenes_97",
                                                                     "Greengenes_99",
                                                                     'SILVA_97', "SILVA_99"] )
    parser.add_option( "--region_dacc", type = "choice", choices = [ "v1v3", "v3v5", "v6v9" ] )
    (options, args) = parser.parse_args()
    if not os.path.isfile(options.map_file):
        print("Ensure your map file exists, cannot find:" + options.map_file)
        exit(1)
    main(options)
