#!/usr/bin/python3
import json
import zipfile
import os
import csv
import openpyxl

import logging
import multiprocessing
import sys
from sh import head, mv, cp, mkdir, glob, zip, unzip, gunzip
import tarfile
import subprocess
from collections import namedtuple

# ref
# reference
# tax
# taxonomy

True_false_dict = {'NO':False, 'N':False, 'FALSE':False, 'YES':True, 'Y':True, 'TRUE':True}

class Cfg:
    BASE = 'fileList.paired'
    MAKE_FILE_CMD_OUTPUT = BASE + '.file'
    MAKE_CONTIG_CMD_OUTPUT = BASE + '.trim.contigs.fasta'
    MAKE_SUMMARY_SEQS_OUTPUT = BASE + '.trim.contigs.summary'
    GROUPS_FNAME = BASE + '.contigs.groups'
    GOOD_GROUPS_GROUPS_FNAME = BASE + '.contigs.good.groups'
    GOOD_CONTIGS_FQ = BASE + '.trim.contigs.good.fasta'
    UNIQUE_SEQS_OUT_NAMES = BASE + '.trim.contigs.good.names'
    UNIQUE_SEQS_OUT_FA = BASE + '.trim.contigs.good.unique.fasta'
    FILTER_UNIQUE_SEQS_OUT_NAMES = BASE + '.trim.contigs.good.unique.good.filter.count_table'
    FILTER_UNIQUE_SEQS_OUT_FA = BASE + '.trim.contigs.good.unique.good.filter.unique.fasta'

    FILTER_PRECLUSTER_COUNT_TABLE = BASE+\
                                '.trim.contigs.good.unique.good.filter.unique.precluster.count_table'
    FILTER_PRECLUSTER_FA = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.fasta'

    UCHIME_COUNT_TABLE = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.count_table'
    UCHIME_CHIMERAS = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.chimeras'
    UCHIME_ACCNOS = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.accnos'
    RM_ACCNOS = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta'
    
    UNIQUE_SEQS_OUT_FA_FRST_K = BASE + '.trim.contigs.good.unique.first1000.fasta'
    COUNT_SEQS_OUT = BASE + '.trim.contigs.good.count_table'
    GEN_ALIGN_SEQS_FIRST_K = BASE + '.trim.contigs.good.unique.first1000.align'
    GOOD_CONTIGS_ALIGN_OUTPUT = BASE + '.trim.contigs.good.unique.align'
    GOOD_UNIQUE_SUMMARY = BASE + '.trim.contigs.good.unique.summary'
    FRST_K_SMRY = 'first_K_summary.txt' # formerly : start-end.txt
    _HOME_DIR = '/home/ubuntu/'

    SCREEN_GOOD_UNIQ_COUNT_TABLE = BASE + '.trim.contigs.good.good.count_table'
    SCREEN_GOOD_UNIQ_ALIGN = BASE + '.trim.contigs.good.unique.good.align'
    SCREEN_GOOD_UNIQ_ACCNOS = BASE + '.trim.contigs.good.unique.bad.accnos'
    SCREEN_GOOD_UNIQ_SUMMARY = BASE + '.trim.contigs.good.unique.good.summary'

    CLASSIFY_SEQS_TAX_BASE = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.pick'
    #CLASSIFY_SEQS_SMRY_BASE = BASE\
    #            + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.seed_v123.wang.tax.summary'
    CLASSIFY_SEQS_ACCNOS = BASE\
                + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.seed_v123.wang.flip.accnos'

    RM_LINEAGE_TAX_BASE = BASE\
        +'.trim.contigs.good.unique.good.filter.unique.precluster.pick'
    RM_LINEAGE_FA = BASE\
        +".trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta"
    RM_LINEAGE_COUNTS = BASE\
        +'.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.pick.count_table'

    SPLIT_ABUND_RARE_COUNTS = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.denovo.'\
                              + 'uchime.pick.pick.rare.count_table'
    SPLIT_ABUND_ABUND_COUNTS = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.denovo.'\
                               + 'uchime.pick.pick.abund.count_table'
    SPLIT_ABUND_RARE_ACCNOS = 'rare.accnos'
    SPLIT_ABUND_ABUND_ACCNOS = 'abund.accnos'
    SPLIT_ABUND_RARE_FA = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.'\
                          + 'rare.fasta'
    SPLIT_ABUND_ABUND_FA = 'fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.'\
                           + 'pick.pick.abund.fasta'
    RM_LINEAGE_TAX_PICK_BASE = BASE + '.trim.contigs.good.unique.good.filter.unique.precluster.pick'

    FINAL_FA = 'final.fasta'
    FINAL_COUNT = 'final.count_table'
    FINAL_TAX = 'final.taxonomy'    
    FINAL_OTU_SHARED = 'final.otu.shared'
    FINAL_OTU_GRPS_SMMRY = 'final.otu.groups.summary'
    FINAL_BIOM = 'final.otu.0.03.biom'
    FINAL_BIOM_SHARED = 'final.otu.0.03.biom_shared'

    FINAL_TX_SABUND = 'final.tx.sabund'
    FINAL_TX_RABUND  = 'final.tx.rabund'
    FINAL_TX_LIST = 'final.tx.list'
    FINAL_TX_SHARED = 'final.tx.shared'
    FINAL_PHYLOTYPE_SHARED = 'final.phylotype.shared'

    FINAL_TX_CONS_TAX = 'final.tx.1.cons.taxonomy'
    FINAL_TX_CONS_TAX_SMRMY = 'final.tx.1.cons.tax.summary'

    FINAL_PHYLIP_DIST = 'final.phylip.dist'

    FINAL_PHYLIP_TRE= 'final.phylip.tre'
    FINAL_PHYLIP_UWSMRY = 'final.phylip.uwsummary'
    FINAL_PHYLIP_UNWEIGHTED_DIST = 'final.phylip.tre1.unweighted.phylip.dist'

    FINAL_PHYLIP_WSMRY = 'final.phylip.trewsummary'
    FINAL_PHYLIP_WEIGHTED_DIST = 'final.phylip.tre1.weighted.phylip.dist'

    CLUST_SPLIT_OUT = 'final.an.unique_list.list'

    MAKE_SHARED_OUT = 'final.an.unique_list.shared'

    TREE_SHARED_THETAYC = 'final.otu.thetayc.0.03.tre'
    TREE_SHARED_JCLASS = 'final.otu.jclass.0.03.tre'
    TREE_PHYLOTYPE_JCLASS = 'final.phylotype.jclass.1.tre'
    TREE_PHYLOTYPE_THETAYC = 'final.phylotype.thetayc.1.tre'
    
    CLASSIFY_OTUS_TAX = 'final.an.unique_list.0.03.cons.taxonomy'
    CLASSIFY_OTUS_TAX_SMMRY = 'final.an.unique_list.0.03.cons.tax.summary'
    
    
    FILTER_GOOD_UNIQUE = BASE + '.trim.contigs.good.unique.good.filter.fasta'
  
## SILVA DB CFG  
    _SILVA_ROOT = _HOME_DIR + 'ref_dbs/silva/'
    SILVA_FASTA = _SILVA_ROOT + 'silva.full_v123.fasta'
    SILVA_SEED_ALIGN = _SILVA_ROOT + 'SILVA_SEED.v123.fasta'
    SILVA_SEED_TAX = _SILVA_ROOT + 'silva.seed_v123.tax'
    SILVA_TAX = _SILVA_ROOT + 'silva.nr_v123.tax'
    SILVA_V4 = _SILVA_ROOT + 'silva.v4.fasta'
    SILVA_PCR_OUT_FNAME = _SILVA_ROOT + 'SILVA_SEED.v123.pcr.fasta'
    SILVA_CLASSIFY_SEQS = BASE\
            + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.seed_v123.wang.taxonomy'
    SILVA_CLASSIFY_SEQS_SMRY = BASE\
            + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.seed_v123.wang.taxonomy.summary'
    SILVA_RM_LINEAGE_TAX = RM_LINEAGE_TAX_BASE + '.seed_v123.wang.pick.taxonomy'
    SILVA_RM_LINEAGE_TAX_PICK = RM_LINEAGE_TAX_PICK_BASE + '.seed_v123.wang.pick.pick.taxonomy'

## GreenGenes DB CFG
    _GG_ROOT = _HOME_DIR + 'ref_dbs/gg_13_8_otus/'
    GG_FASTA = _HOME_DIR + 'ref_dbs/rep_set_aligned/99_otus.fasta'
    GG_TAX = _GG_ROOT + 'gg_13_8_99.gg.tax'
    GG_PCR_OUT_FNAME = _HOME_DIR + 'ref_dbs/rep_set_aligned/99_otus.pcr.fasta'
    GG_CLASSIFY_SEQS = BASE\
             + '.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy'
    GG_CLASSIFY_SEQS_SMRY = BASE\
             + '.trim.contigs.good.unique.good.filter.unique.precluster.pic.gg.wang.taxonomy.summary'
    GG_RM_LINEAGE_TAX = RM_LINEAGE_TAX_BASE + '.gg.wang.pick.taxonomy'
    GG_RM_LINEAGE_TAX_PICK = RM_LINEAGE_TAX_PICK_BASE + '.gg.wang.pick.pick.taxonomy'
   
   
    CUSTOM_PCR_FILE_RENAME = 'PCR_out.customized_region.align'

    OTU_BIOM_SUMMARY = 'otu_table.biom.summary.txt'
    SORTED_BIOM = 'final.otu.0.03.sorted.biom'
    OTU_HEATMAP_OUT_DIR = 'OTU_Heatmap'
    OTU_Heatmap = 'heatmap.svg'
    
    CORE_DIV_OUT_DIR = 'core_diversity'
    TREES_DIR = 'trees'
    BIOM_DIR = 'biom_files'
    METASTATS_DIR = 'metastats'
    METASTATS_OUT = 'metastats'
    COLLATED_OUTS = 'nephele_outputs'
    
    DEPTH_SCALER = 0.1
    CLASSIFY_SEQS_CUTOFF = 80
    POINT_ZERO_THREE_LABL = '0.03'
    DESIGN_FILE = 'design_file'

    LEFSE_OUT = 'final.otu.0.03.lefse'
    MAXAMBIG = 0
    MIN_NUM_SAMPLES_FOR_CD = 2  # this number of below => no core diversity run
    LOG_FILE_NAME = 'logfile.txt'
    
def ensure_file_format_is_ok( fname ):
    # this sorts nasty CRLF chars
    with open(fname, 'rU') as infile:
        text = infile.read()  # Automatic ("Universal read") conversion of newlines to "\n"
    with open(fname, 'w') as outfile:
        outfile.write(text)
    return fname
    
def read_mm_csv( fname ):
    # read in our own special flavour of CSV file and hash
    d = dict()
    with open( fname ) as f_in:
        for line in f_in:
            if line.startswith('#'): continue
            if ''.join(line).strip():
                line_as_list = line.strip().split(',')
                if len(line_as_list) is not 2:
                    log("There's something wrong with the config.csv file:")
                    log(line)
                d[line_as_list[0]] = line_as_list[1]
    return d

def mothurize ( func_name, args ):
    return 'mothur "#' + func_name + '(seed=clear,' + ','.join(args) + ')"'

def redir_out( cmd, out_fname ):
    return cmd + " > " + out_fname

def exec_cmnd( cmds ):
    if cmds is None: return
    
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


def ensure_file_is_csv( fname ):
    fname_no_ext, ext = os.path.splitext( fname )
    if ext.lower() == '.csv' or ext.lower() == '.txt' or ext.lower() == '.mapping':
        return fname
    elif ext.lower() == '.xlsx' or ext.lower() == '.xls':
        wb = openpyxl.load_workbook( fname )
        ws = wb.active
        csv_fname = fname_no_ext + '.csv'
        with open(csv_fname, 'w') as f:
            c = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            for r in ws.rows:
                c.writerow([cell.value for cell in r])
        return csv_fname
    else:
        log.error('Unable to deal with file {0}.'.format(fname))
        do_end_operations()
        exit(1)

def ignore_mac_osx_files( files):
    ret = list()
    for	f in files:
        if '__MACOSX' not in f:
            ret.append(f)
    return ret

def unzip_and_junk_path(fname):
    files_unzipped = list()
    with zipfile.ZipFile( fname ) as zf:
        files_unzipped = [os.path.basename(f) for f in ignore_mac_osx_files(zf.namelist())]
        unzip('-jo', fname)     # -o is overwrite
    return files_unzipped

def unzip_input_file( fname ):
    if zipfile.is_zipfile(fname):
        files = unzip_and_junk_path(fname)
    for f in files:
        if f.endswith('.gz'):
            gunzip(f)


    # this fails if there is some kind of dir structure:
        # with zipfile.ZipFile( fname ) as zf:
        #     files_unzipped = zf.namelist()
        #     zf.extractall( path='.')
    # return files_unzipped


# def unzip_file( fname ):
#     # check file exists
#     # untar if needed
#     # unzip if needed
#     # return fnames
#     files = list()
#     if not os.path.isfile( fname ):
#         Cfg.log.error('File: {0} does not exist!'.format( fname ))
#         return files
#     with zipfile.ZipFile( fname ) as zf:
#         files = zf.namelist()        
#     if tarfile.is_tarfile( fname ):
#         t = tarfile.TarFile(name=fname, mode='r')
#         files = t.getnames()
#         print(files)
        
def mv_if_exists( source, dest ):
    if os.path.lexists( source ):
        mv( source, dest)
    # else:
    #     Cfg.log.warn('Unable to mv {0}, does not exist.'.format(source) )


def cp_if_exists(f_to_cp, dest):
    if os.path.lexists(f_to_cp) and os.path.lexists(dest):
        cp( '-r', f_to_cp, dest)
    # else:
    #     Cfg.log.warn('Unable to cp {0}, does not exist in {1}'.format(f_to_cp, dest) )
    
def ensure_file_exists( outs ):    
    if isinstance(outs, str):
        l = list()
        l.append( outs )
        outs = l
    for out in outs:
        if os.path.isfile(out):
            log.info('File {0} exists as expected.'.format(out) )
        else:
            log.info('Unable to proceed: File {0} does not exist.'.format(out) )
            do_end_operations()
            exit(1)
    return True

def prep_output_files():
    mkdir('-p', Cfg.COLLATED_OUTS) # -p = no error if existing, make parent directories as needed
    mkdir('-p', Cfg.TREES_DIR)
    mkdir('-p', Cfg.BIOM_DIR)
    mkdir('-p', Cfg.OTU_HEATMAP_OUT_DIR)

    cp_if_exists( Cfg.TREE_SHARED_JCLASS, Cfg.TREES_DIR )
    cp_if_exists( Cfg.TREE_SHARED_THETAYC, Cfg.TREES_DIR )
    cp_if_exists( Cfg.FINAL_PHYLIP_TRE, Cfg.TREES_DIR )
    cp_if_exists( Cfg.TREE_PHYLOTYPE_JCLASS, Cfg.TREES_DIR )
    cp_if_exists( Cfg.TREE_PHYLOTYPE_THETAYC, Cfg.TREES_DIR )
    mv_if_exists( Cfg.OTU_Heatmap, Cfg.OTU_HEATMAP_OUT_DIR )

    cp_if_exists( Cfg.SORTED_BIOM, Cfg.BIOM_DIR )
    cp_if_exists( Cfg.OTU_BIOM_SUMMARY, Cfg.BIOM_DIR )
    cp_if_exists( Cfg.FINAL_BIOM, Cfg.BIOM_DIR )
    cp_if_exists( Cfg.FINAL_BIOM_SHARED, Cfg.BIOM_DIR )

    mv_if_exists( Cfg.BIOM_DIR, Cfg.COLLATED_OUTS )
    mv_if_exists( Cfg.TREES_DIR, Cfg.COLLATED_OUTS )
    mv_if_exists( Cfg.OTU_HEATMAP_OUT_DIR, Cfg.COLLATED_OUTS )
    mv_if_exists( Cfg.CORE_DIV_OUT_DIR, Cfg.COLLATED_OUTS )
    mv_if_exists( Cfg.METASTATS_DIR, Cfg.COLLATED_OUTS )

    cp_if_exists( Cfg.FINAL_OTU_GRPS_SMMRY, Cfg.COLLATED_OUTS )
    cp_if_exists( Cfg.FINAL_TAX, Cfg.COLLATED_OUTS )
    cp_if_exists( Cfg.FINAL_TX_CONS_TAX_SMRMY, Cfg.COLLATED_OUTS )
    cp_if_exists( Cfg.CLASSIFY_OTUS_TAX_SMMRY, Cfg.COLLATED_OUTS )
    cp_if_exists( Cfg.LEFSE_OUT, Cfg.COLLATED_OUTS )
    cp_if_exists( Cfg.FINAL_FA, Cfg.COLLATED_OUTS )
    cp_if_exists( 'HMP_compare_results', Cfg.COLLATED_OUTS )
    cp_if_exists( 'taxa_plots_and_heatmaps', Cfg.COLLATED_OUTS )

    # cp *trim.unique.fasta Cfg.COLLATED_OUTS/
    # #cp -r *_with_HMPDACC_v13 Cfg.COLLATED_OUTS/ 
    # #cp -r *_with_HMPDACC_v35 Cfg.COLLATED_OUTS/ 
    cp_if_exists( Cfg.LOG_FILE_NAME, Cfg.COLLATED_OUTS )

def do_end_operations():
    prep_output_files()
    compress_results()

def compress_results():
    zip('-r', 'PipelineResults.zip', Cfg.COLLATED_OUTS )
    zip('-r', 'WorkFolder.zip', glob('*') )

def setup_logger():
    formatter = logging.Formatter(fmt='[ %(asctime)s - %(levelname)s ] %(message)s')
    fh = logging.FileHandler(Cfg.LOG_FILE_NAME)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger = logging.getLogger('MOTHUR_LOG')
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    return logger

Sample = namedtuple('Sample', ['SampleID',
                               'BarcodeSequence',
                               'LinkerPrimerSequence',
                               'ForwardFastqFile',
                               'ReverseFastqFile',
                               'TreatmentGroup',
                               'Description'] ) #                                'ReversePrimer',

class Mothur_MiSeq_PE:
    def __init__(self, kwargs):
        for key, value in kwargs.items():
            if value == '': pass
            if key == 'INPUT_TYPE': self.input_type = value
            elif key == 'RAW_FILE_FULL': self.raw_file_full = value                
            elif key == "FRACTION_OF_MAXIMUM_SAMPLE_SIZE": self.fraction_of_maximum_sample_size = value
            elif key == "MAP_FILE": self.map_file = ensure_file_is_csv(value)
            elif key == "MAXLENGTH": self.maxlength = value
            elif key == "READS_ZIP": self.reads_zip = value
            elif key == 'CRITERIA': self.criteria = value
            elif key == 'DIFFERENCE_RANK': self.difference_rank = value
            elif key == 'REFERENCE_DATABASE': self.reference_database = value
            elif key == 'BDIFFS': self.bdiffs = value
            elif key == 'PDIFFS': self.pdiffs = value
            elif key == 'MAXFLOWS': self.maxflows = value
            elif key == 'MINFLOWS': self.minflows = value
            elif key == 'OPTIMIZE': self.optimize = value
            elif key == 'DATABASE': self.database = value
            # HMP STARTS HERE
            elif key == 'COMP_WITH_DACC': 
                if value.upper() not in True_false_dict:
                    log.info('Value for COMP_WITH_DACC not valid.'.format(value) )
                    do_end_operations()
                    exit(1)
                else:    
                    self.comp_with_dacc = True_false_dict[value.upper()]
            elif key == 'BODY_SITE': self.body_site = value
            elif key == 'REGION_DACC': self.region_dacc = value
            elif key == 'HMP_DATABASE': self.hmp_database = value
            elif key == 'NEAREST_N_SAMPLES': self.nearest_n_samples = value
            # HMP ENDS HERE
            else:
                log.warn('Not sure what to do with param {0}, set to {1}; ignoring.'.format(key, value))
        
        unzip_input_file(self.reads_zip)
        self.samples = self.load_samples_from_map( self.map_file )

    def gen_compare_to_HMP_cmd( self ):
        if self.comp_with_dacc:
            return  './betadiv.py '\
                + " --user_seqs=" + Cfg.MAKE_FILE_CMD_OUTPUT\
                + " --body_site=" + self.body_site\
                + " --map_file=" + self.map_file\
                + " --hmp_database=" + self.hmp_database\
                + " --nearest_n_samples=" + self.nearest_n_samples\
                + " --region_dacc=" + self.region_dacc
        
    @staticmethod
    def load_samples_from_map( fname ):
        ensure_file_exists( fname )
        ensure_file_format_is_ok( fname )
        samples = list()        
        reader = csv.DictReader( open(fname), delimiter='\t' )
        for row in reader:
            ensure_file_exists( row['ForwardFastqFile'] )
            ensure_file_exists( row['ReverseFastqFile'] )
            s = Sample( row['#SampleID'],
                        row['BarcodeSequence'],
                        row['LinkerPrimerSequence'],
                        row['ForwardFastqFile'],
                        row['ReverseFastqFile'],
                        row['TreatmentGroup'],
                        row['Description'] ) #                         row['ReversePrimer'],
            samples.append( s )
                
        if len( samples  ) == 0:
            log.error('Unable to proceed, no samples in mapping file {0}.'.format (fname) )
            do_end_operations()
            exit(1)
        return samples

    @staticmethod
    def gen_home_rolled_file_cmd( samples ):
        with open(Cfg.MAKE_FILE_CMD_OUTPUT, 'w') as f:
#            for s_id, fqs in self.sample_to_fq.items():
            for sample in samples:
                line = [sample.SampleID, sample.ForwardFastqFile, sample.ReverseFastqFile]
                print ("\t".join(line), file=f )
                
    @staticmethod
    def gen_make_file_cmd():
        # use mothur to create the file: fileList.paired.file
        # (which can be used in Make.contigs with the file arg name)
        return mothurize ('make.file', ['inputdir= .']) 

    @staticmethod
    def gen_make_contigs_cmd():
        return mothurize ('make.contigs', ['file=' + Cfg.MAKE_FILE_CMD_OUTPUT,
                                           'processors=' + str(multiprocessing.cpu_count()) ])
    @staticmethod
    def gen_summary_seqs_cmd( f_to_summarize, counts_file=None ):
        # gens:
        # fileList.paired.trim.contigs.good.unique.summary / GOOD_UNIQUE_SUMMARY
        a = ['fasta=' + f_to_summarize,
             'processors=' + str(multiprocessing.cpu_count())]
        if counts_file is not None:
            a.append( 'count='+counts_file )
        return mothurize ('summary.seqs', a )

    @staticmethod
    def gen_screen_seqs_cmd_w_opt_crit( fa, count, summary, opt, criteria ):
        # screen.seqs(fasta=rawfile.trim.contigs.good.unique.align,
        # count=rawfile.trim.contigs.good.count_table,
        # summary=rawfile.trim.contigs.good.unique.summary,
        # optimize=start-end-minlength,
        # criteria=90)
        # gens:
        # fileList.paired.trim.contigs.good.good.count_table
        # fileList.paired.trim.contigs.good.unique.good.align
        # fileList.paired.trim.contigs.good.unique.bad.accnos
        # fileList.paired.trim.contigs.good.unique.good.summary
        return mothurize ('screen.seqs', ['fasta=' + fa,
                                          'count=' + count,
                                          'summary=' + summary,
                                          'optimize=' + opt,
                                          'criteria=' + str(criteria) ] )
    @staticmethod
    def gen_screen_seqs_cmd( maxlength ):
        return mothurize ('screen.seqs', ['fasta=' + Cfg.MAKE_CONTIG_CMD_OUTPUT,
                                          'group=' + Cfg.GROUPS_FNAME,
                                          'maxambig=' + str(Cfg.MAXAMBIG),
                                          'maxlength=' + str(maxlength) ] )
    
    @staticmethod
    def gen_unique_seqs_cmd( fasta, counts_file=None ):
        # generates :
        # fileList.paired.trim.contigs.good.names
        # fileList.paired.trim.contigs.good.unique.fasta
        # or
        # fileList.paired.trim.contigs.good.unique.good.filter.count_table
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.fasta
        # eg 
        # unique.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.fasta, count=rawfile.trim.contigs.good.good.count_table)        
        a = ['fasta=' + fasta ]        
        if counts_file is not None:
            a.append( 'count=' + counts_file )
        return mothurize('unique.seqs', a )
            

    @staticmethod
    def gen_count_seqs_cmd():
        # generates :
        # fileList.paired.trim.contigs.good.count_table
        # could also do:
        # grep '>' fileList.paired.trim.contigs.good.fasta | wc -l
        return mothurize ('count.seqs', ['name=' + Cfg.UNIQUE_SEQS_OUT_NAMES,
                                         'group=' + Cfg.GOOD_GROUPS_GROUPS_FNAME ] )
    @staticmethod
    def gen_align_seqs_cmd( seqs_to_align, ref ):
        # generates : (I think)
        # fileList.paired.trim.contigs.good.unique.first1000.fasta
# 
        # fileList.paired.trim.contigs.good.unique.align.report
        # fileList.paired.trim.contigs.good.unique.align
        return mothurize('align.seqs', ['fasta=' + seqs_to_align,
                                        'reference=' + ref,
                                        'flip=T',
                                        'processors=' + str(multiprocessing.cpu_count()) ] )
#    mothur > align.seqs(fasta=20160519.trim.contigs.good.unique.fasta, reference=~/Documenten/Silva_Database/V123/silva.seed_v123.align,processors=6)
    
    @staticmethod
    def get_median_start_end( fname ):
        with open(fname) as f:
            for line in f:
                if line.startswith('Median:'):
                    a = line.split("\t")
                    if len(a) > 3:
                        return a[1],a[2]
                    else:
                        log.error("The Output of summary.seqs seems to be wrong")
    @staticmethod
    def gen_pcr_seqs_cmnd(start, end):
        # gens PCR_OUT_FNAME        
        return mothurize( 'pcr.seqs', ['fasta=' + Cfg.SILVA_SEED_ALIGN,
                                       'start=' + start,
                                       'end=' + end,
                                       'keepdots=F',
                                       'processors=' + str(multiprocessing.cpu_count()) ])

    
    @staticmethod
    def gen_filter_seqs( fa ):
        # mothur > filter.seqs(fasta=rawfile.trim.contigs.good.unique.good.align, vertical=T, trump=.)
        # gens fileList.paired.trim.contigs.good.unique.good.filter.fasta
        return mothurize( 'filter.seqs', [ 'fasta=' + fa,
                                           'vertical=T',
                                           'trump=.' ] )
    @staticmethod
    def gen_pre_cluster_cmd(fasta, counts_file, diffs):
        # gens:
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.count_table
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.fasta
        return mothurize( 'pre.cluster', ['fasta='+ fasta,
                                          'count=' + counts_file,
                                          'diffs=' + str(diffs) ] )
    @staticmethod
    def gen_chimera_uchime(fasta, counts_file):
        # gens:
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.count_table
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.chimeras
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.accnos
        return mothurize('chimera.uchime', ['fasta=' + fasta,
                                            'count=' + counts_file,
                                            'dereplicate=t' ])
    @staticmethod
    def gen_remove_seqs_cmd(fasta=None, accnos=None, tax=None):
        if tax is None:
            # gens
            # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta
            return mothurize ('remove.seqs',['fasta=' + fasta,
                                             'accnos=' + accnos ])
        elif fasta is None:
            # gens
            # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.pick.taxonomy
            return mothurize('remove.seqs',['taxonomy=' + tax,
                                            'accnos=' + accnos])
    
    # mothur > classify.seqs(fasta=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.pick.fasta, count=rawfile.trim.contigs.good.unique.good.filter.unique.precluster.uchime.pick.count_table, reference=gg_13_5_97.fasta, taxonomy=gg_13_5_97.gg.tax, cutoff=80, probs=f)
    @staticmethod
    def gen_classify_seqs_cmd( fasta, counts_file, reference, taxonomy ):
        # gens :
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.taxonomy
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.\
        #     pick.gg.wang.tax.summary
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.\
        #     pick.gg.wang.flip.accnos
        # what's up with *wang??
        return mothurize( 'classify.seqs',['fasta=' + fasta,
                                           'count=' + counts_file,
                                           'reference=' + reference,
                                           'taxonomy=' + taxonomy,
                                           'cutoff=' + str(Cfg.CLASSIFY_SEQS_CUTOFF),
                                           'probs=f'] )
    @staticmethod
    def gen_rm_lineage_cmd( fasta, counts_file, taxonomy ):
        # gens
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.pick.gg.wang.pick.taxonomy
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.fasta
        # fileList.paired.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.pick.count_table
        return mothurize('remove.lineage',['fasta=' + fasta,
                                           'count=' + counts_file,
                                           'taxonomy=' + taxonomy,
                                           'taxon=Chloroplast-Mitochondria-unknown-Archaea-Eukaryota'])
    @staticmethod
    def gen_split_abund(fasta, counts_file):
        return mothurize('split.abund',['fasta=' + fasta,
                                        'count=' + counts_file,
                                        'cutoff=1',
                                        'accnos=true'])

    @staticmethod
    def gen_cluster_split( fasta, counts_file, tax):
        return mothurize('cluster.split',['fasta=' + fasta,
                                          'count=' + counts_file,
                                          'taxonomy=' + tax,
                                          'splitmethod=classify',
                                          'taxlevel=4',
                                          'processors='  + str(multiprocessing.cpu_count()) ])
    @staticmethod
    def gen_make_shared( l, counts_file, label):
        # final.tx.shared
        return mothurize('make.shared',['list=' + l,
                                        'count=' + counts_file,
                                        'label=' + label])
    
    @staticmethod
    def gen_metastats(shared, design_file):
        return mothurize ('metastats',['shared=' + shared,
                                       'design=' + design_file ] )

# classify.otu(
# list=stability.trim.contigs.good.unique.good.filter.unique.precluster.pick.pds.wang.pick.pick.tx.list,
# count=stability.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.pick.pick.count_table,
# taxonomy=stability.trim.contigs.good.unique.good.filter.unique.precluster.pick.pds.wang.pick.pick.taxonomy,
# label=1)
    
# mothur > classify.otu(
# list=stability.trim.contigs.good.unique.good.filter.unique.precluster.pick.pick.pick.an.unique_list.list,
# count=stability.trim.contigs.good.unique.good.filter.unique.precluster.denovo.uchime.pick.pick.pick.count_table,
# taxonomy=stability.trim.contigs.good.unique.good.filter.unique.precluster.pick.pds.wang.pick.pick.taxonomy,
# label=0.03)
    @staticmethod
    def gen_classify_otus_cmd( list_file, counts_file, tax, label=None, ref_taxonomy=None):
        if ref_taxonomy is not None:
            # generates:
            # final.an.unique_list.0.03.cons.taxonomy
            # final.an.unique_list.0.03.cons.tax.summary
            return mothurize( 'classify.otu', ['list=' + list_file,
                                               'count=' + counts_file,
                                               'taxonomy=' + tax,
                                               'label=' + Cfg.POINT_ZERO_THREE_LABL,
                                               'reftaxonomy=' + ref_taxonomy])
        else:
            # final.tx.1.cons.taxonomy
            # final.tx.1.cons.tax.summary
            return mothurize( 'classify.otu', ['list=' + list_file,
                                               'count=' + counts_file,
                                               'taxonomy=' + tax,
                                               'label=' + label] )
    

    @staticmethod
    def gen_tree_shared(shared):
        # final.otu.thetayc.0.03.tre
        # final.otu.jclass.0.03.tre
        # and 
        # final.phylotype.thetayc.1.tre
        # final.phylotype.jclass.1.tre
        return mothurize('tree.shared',['shared=' + shared,
                                        'calc=thetayc-jclass'])
    @staticmethod
    def gen_summary_single_cmd(shared):
        return mothurize('summary.single',['shared='+shared])

    @staticmethod
    def gen_make_lefse_cmnd( shared, design, constaxonomy ):
        # gens final.otu.0.03.lefse
        return mothurize('make.lefse',['shared=' + shared,
                                       'design=' + Cfg.DESIGN_FILE,
                                       'constaxonomy=' + constaxonomy] )
    @staticmethod
    def make_design_file( map_file ):
        sample_to_treatmnt = dict()
        treat_col_num = 0
        with open(map_file) as f:
            for line in f:
                line_as_list = line.split("\t")
                if line.startswith('#'):
                    for col in line_as_list:
                        if 'reatment' in col:
                            break
                        treat_col_num += 1
                else:
                    sample_to_treatmnt[ line_as_list[0] ] = line_as_list[treat_col_num]
        # if treat_col_num == 0:
        #     self.log_file('problem')
                    
        with open(Cfg.DESIGN_FILE, 'w') as f_out:
            print ("\t".join(['SampleID','TreatmentGroup']), file=f_out)
            for k, v in sample_to_treatmnt.items():
                print ("\t".join([k,v]), file=f_out)

    @staticmethod
    def gen_make_biom(shared, constaxonomy, otu_map, ref_taxonomy):
        # final.otu.0.03.biom
        # final.otu.0.03.biom_shared
        return mothurize('make.biom', ['shared=' + shared,
                                       'constaxonomy=' + constaxonomy,
                                       'picrust=' + otu_map,
                                       'label=' + Cfg.POINT_ZERO_THREE_LABL,
                                       'reftaxonomy=' + ref_taxonomy,
                                       'metadata=design_file'] )
    @staticmethod
    def gen_make_biom_no_picrust(shared, constaxonomy, ref_taxonomy):
        # final.otu.0.03.biom
        return mothurize('make.biom', ['shared=' + shared,
                                       'constaxonomy=' + constaxonomy,
                                       'label=' + Cfg.POINT_ZERO_THREE_LABL,
                                       'reftaxonomy=' + ref_taxonomy] )

    @staticmethod
    def gen_phylotype(taxonomy):
        # final.tx.sabund
        # final.tx.rabund
        # final.tx.list
        return  mothurize('phylotype',['taxonomy=' + taxonomy])
            
    @staticmethod
    def gen_dist_seqs(fasta):
        # final.phylip.dist
        return mothurize('dist.seqs',['fasta=' + fasta,
                                      'output=phylip',
                                      'processors=' + str(multiprocessing.cpu_count())])

    @staticmethod
    def gen_clearcut(phylip):
        # final.phylip.tre
        return mothurize('clearcut',['phylip=' + phylip])

    @staticmethod
    def gen_unifrac_unweighted(tree_file, counts_file):
        # final.phylip.uwsummary
        # final.phylip.tre1.unweighted.phylip.dist
        return mothurize('unifrac.unweighted',['tree='+ tree_file,
                                               'count=' + counts_file,
                                               'distance=lt',
                                               'processors=' + str(multiprocessing.cpu_count()),
                                               'random=F'])

    @staticmethod
    def gen_unifrac_weighted(tree_file, counts_file):
        # final.phylip.trewsummary
        # final.phylip.tre1.weighted.phylip.dist
        return mothurize('unifrac.weighted',['tree='+ tree_file,
                                             'count=' + counts_file,
                                             'distance=lt',
                                             'processors=' + str(multiprocessing.cpu_count()),
                                             'random=F'])
    @staticmethod
    def gen_pcoa(phylip):
        # final.phylip.tre1.unweighted.phylip.pcoa.axes
        # final.phylip.tre1.unweighted.phylip.pcoa.loadings
        # and
        # final.phylip.tre1.weighted.phylip.pcoa.axes
        # final.phylip.tre1.weighted.phylip.pcoa.loadings
        return mothurize('pcoa',['phylip='+ phylip])

    @staticmethod
    def gen_otu_rep( count, fasta, clust_split_out):
        # final.an.unique_list.0.03.rep.count_table
        # final.an.unique_list.0.03.rep.fasta
        return mothurize ('get.oturep',['count=' + count,
                                        'fasta=' + fasta,
                                        'list=' + clust_split_out,
                                        'method=abundance',
                                        'label=' + Cfg.POINT_ZERO_THREE_LABL ])

    @staticmethod
    def gen_biom_summarize_table(f_in, f_out):
        return 'biom summarize-table '\
            + ' -i ' + f_in \
            + ' -o ' + f_out

    @staticmethod
    def gen_sort_otu_table(otu_in, map_file, sort_field):
        return 'sort_otu_table.py '\
            + ' --input_otu_table=' + otu_in \
            + ' --output_fp=' + Cfg.SORTED_BIOM \
            + ' --mapping_fp=' + map_file \
            + ' --sort_field=' + sort_field
    
    @staticmethod
    def lookup_max_depth_from_biom_summry( fname ):
        max_depth = None
        with open( fname ) as f_in:
            for line in f_in:
                if line.startswith(' Max:'):
                    _, max_depth = line.strip().split(': ')
        if max_depth is None:
            log.error('No Max depth field was found in {0}, cannot compute depth.').format( fname )
            do_end_operations()
            exit(1)
        return int(float(max_depth))

    @staticmethod
    def gen_betterplots(input_biom_fp, map_file, rank):
        return 'Rscript betterplots.R'\
            + ' ' + input_biom_fp\
            + ' ' + map_file\
            + ' ' + str(rank)\
            + ' NO'

    @staticmethod
    def gen_core_diversity_analysis(input_biom_fp, map_file, treatment_groups, depth):
        return 'core_diversity_analyses.py '\
            + ' --output_dir=' + Cfg.CORE_DIV_OUT_DIR\
            + ' --input_biom_fp=' + input_biom_fp\
            + ' --mapping_fp=' + map_file\
            + ' --nonphylogenetic_diversity'\
            + ' --categories=' + ','.join(treatment_groups)\
            + ' --sampling_depth='+ str(depth)

    @staticmethod
    def lookup_tgs_from_map_file( fname ):
        tg_header = 'TreatmentGroup'
        tgs = list()
        with open( fname ) as f_in:
            for line in f_in:
                if line.startswith('#SampleID') and tg_header in line:
                    cols = line.strip().split("\t")
                    seen_tg = False
                    for col in cols:
                        if col == tg_header:
                            seen_tg = True
                        if seen_tg and col not in ( 'Description',  'ReversePrimer' ):
                            tgs.append(col)
        if len(tgs) == 0:
            log.error('No TreatmentGroup column found in {0}. Exiting.').format(fname)
            do_end_operations()
            exit(1)            
        return tgs

    @staticmethod
    def gen_otu_heatmap_cmd( biom_file ):
        return 'make_otu_heatmap.py '\
            + ' -i ' + biom_file\
            + ' --imagetype=svg'\
            + ' -o ' + Cfg.OTU_Heatmap

log = setup_logger()            # this is a bit scruffy. This is just a global. could be singleton?
config_fname = sys.argv[1]
input_dict = ''

if __name__ == '__main__':
    if os.path.isfile( config_fname ):
        if config_fname.endswith( '.json' ):
            with open( config_fname ) as json_file:
                input_dict = json.load(json_file)
        elif config_fname.endswith( '.csv' ):
            input_dict = read_mm_csv(config_fname)
            
pipe = Mothur_MiSeq_PE( input_dict ) 

pipe.gen_home_rolled_file_cmd( pipe.samples )
ensure_file_exists( Cfg.MAKE_FILE_CMD_OUTPUT )

exec_cmnd( pipe.gen_make_contigs_cmd() )
ensure_file_exists( Cfg.MAKE_CONTIG_CMD_OUTPUT )

exec_cmnd( pipe.gen_summary_seqs_cmd( Cfg.MAKE_CONTIG_CMD_OUTPUT) )
ensure_file_exists( Cfg.MAKE_SUMMARY_SEQS_OUTPUT)

exec_cmnd( pipe.gen_screen_seqs_cmd( pipe.maxlength ) )
ensure_file_exists( Cfg.GOOD_CONTIGS_FQ )

exec_cmnd( pipe.gen_unique_seqs_cmd( Cfg.GOOD_CONTIGS_FQ) )
ensure_file_exists( Cfg.UNIQUE_SEQS_OUT_NAMES )
ensure_file_exists( Cfg.UNIQUE_SEQS_OUT_FA )

# COMP TO HMP STUFF
exec_cmnd( pipe.gen_compare_to_HMP_cmd( ) )

exec_cmnd( pipe.gen_count_seqs_cmd() )
ensure_file_exists( Cfg.COUNT_SEQS_OUT )
    
head("-1000", Cfg.UNIQUE_SEQS_OUT_FA, _out=Cfg.UNIQUE_SEQS_OUT_FA_FRST_K)
ensure_file_exists( Cfg.UNIQUE_SEQS_OUT_FA_FRST_K )
 

exec_cmnd( pipe.gen_align_seqs_cmd( Cfg.UNIQUE_SEQS_OUT_FA_FRST_K, Cfg.SILVA_SEED_ALIGN ) )
ensure_file_exists( Cfg.GEN_ALIGN_SEQS_FIRST_K )

exec_cmnd( redir_out( pipe.gen_summary_seqs_cmd(Cfg.GEN_ALIGN_SEQS_FIRST_K), Cfg.FRST_K_SMRY) )
ensure_file_exists( Cfg.FRST_K_SMRY )
median_start, median_end = pipe.get_median_start_end( Cfg.FRST_K_SMRY )
    
exec_cmnd( pipe.gen_pcr_seqs_cmnd(median_start, median_end) )
mv( Cfg.SILVA_PCR_OUT_FNAME, Cfg.CUSTOM_PCR_FILE_RENAME )

exec_cmnd( pipe.gen_align_seqs_cmd( Cfg.UNIQUE_SEQS_OUT_FA, Cfg.CUSTOM_PCR_FILE_RENAME ) )

exec_cmnd( pipe.gen_summary_seqs_cmd( Cfg.GOOD_CONTIGS_ALIGN_OUTPUT, Cfg.COUNT_SEQS_OUT) )

exec_cmnd( pipe.gen_screen_seqs_cmd_w_opt_crit(fa = Cfg.GOOD_CONTIGS_ALIGN_OUTPUT,
                                               count = Cfg.COUNT_SEQS_OUT,
                                               summary = Cfg.GOOD_UNIQUE_SUMMARY,
                                               opt = pipe.optimize,
                                               criteria = pipe.criteria ) )
ensure_file_exists( [Cfg.SCREEN_GOOD_UNIQ_COUNT_TABLE,
                     Cfg.SCREEN_GOOD_UNIQ_ALIGN,
                     Cfg.SCREEN_GOOD_UNIQ_ACCNOS,
                     Cfg.SCREEN_GOOD_UNIQ_SUMMARY] )

exec_cmnd( pipe.gen_filter_seqs( Cfg.SCREEN_GOOD_UNIQ_ALIGN ) )

exec_cmnd(pipe.gen_unique_seqs_cmd( Cfg.FILTER_GOOD_UNIQUE,
                                    Cfg.SCREEN_GOOD_UNIQ_COUNT_TABLE ))

exec_cmnd( pipe.gen_pre_cluster_cmd(Cfg.FILTER_UNIQUE_SEQS_OUT_FA,
                                                Cfg.FILTER_UNIQUE_SEQS_OUT_NAMES,
                                                pipe.difference_rank) )
ensure_file_exists(Cfg.FILTER_PRECLUSTER_COUNT_TABLE)
ensure_file_exists(Cfg.FILTER_PRECLUSTER_FA)

exec_cmnd(pipe.gen_chimera_uchime( Cfg.FILTER_PRECLUSTER_FA, Cfg.FILTER_PRECLUSTER_COUNT_TABLE) )

exec_cmnd( pipe.gen_remove_seqs_cmd(fasta=Cfg.FILTER_PRECLUSTER_FA, accnos=Cfg.UCHIME_ACCNOS ) )
ensure_file_exists( Cfg.RM_ACCNOS )

if pipe.database == 'Greengenes':    
    exec_cmnd (pipe.gen_classify_seqs_cmd( Cfg.RM_ACCNOS, Cfg.UCHIME_COUNT_TABLE,
                                                                    Cfg.GG_FASTA, 
                                                                    Cfg.GG_TAX ) )
else:
    exec_cmnd (pipe.gen_classify_seqs_cmd( Cfg.RM_ACCNOS, Cfg.UCHIME_COUNT_TABLE,
                                                                    Cfg.SILVA_SEED_ALIGN, 
                                                                    Cfg.SILVA_SEED_TAX ) )

#NEED IF STATMENT BASED UPON DB SELECTION 
if pipe.database == 'Greengenes':
    exec_cmnd( pipe.gen_rm_lineage_cmd( Cfg.RM_ACCNOS, Cfg.UCHIME_COUNT_TABLE, Cfg.GG_CLASSIFY_SEQS ) )
    ensure_file_exists([Cfg.RM_LINEAGE_FA, Cfg.GG_RM_LINEAGE_TAX, Cfg.RM_LINEAGE_COUNTS])
else:
    exec_cmnd( pipe.gen_rm_lineage_cmd( Cfg.RM_ACCNOS, Cfg.UCHIME_COUNT_TABLE, Cfg.SILVA_CLASSIFY_SEQS ) )
    ensure_file_exists([Cfg.RM_LINEAGE_FA, Cfg.SILVA_RM_LINEAGE_TAX, Cfg.RM_LINEAGE_COUNTS])

exec_cmnd( pipe.gen_split_abund( Cfg.RM_LINEAGE_FA, Cfg.RM_LINEAGE_COUNTS) )
ensure_file_exists( [Cfg.SPLIT_ABUND_RARE_FA,
                     Cfg.SPLIT_ABUND_ABUND_FA,
                     Cfg.SPLIT_ABUND_RARE_ACCNOS,
                     Cfg.SPLIT_ABUND_RARE_COUNTS,
                     Cfg.SPLIT_ABUND_ABUND_ACCNOS,
                     Cfg.SPLIT_ABUND_ABUND_COUNTS] )

#NEED IF STATMENT BASED UPON DB SELECTION 
if pipe.database == 'Greengenes':    
    exec_cmnd( pipe.gen_remove_seqs_cmd(accnos=Cfg.SPLIT_ABUND_RARE_ACCNOS, tax=Cfg.GG_RM_LINEAGE_TAX ) )
    ensure_file_exists(Cfg.GG_RM_LINEAGE_TAX_PICK)
else:
    exec_cmnd( pipe.gen_remove_seqs_cmd(accnos=Cfg.SPLIT_ABUND_RARE_ACCNOS, tax=Cfg.SILVA_RM_LINEAGE_TAX ) )
    ensure_file_exists(Cfg.SILVA_RM_LINEAGE_TAX_PICK)

cp (Cfg.SPLIT_ABUND_ABUND_FA, Cfg.FINAL_FA)
cp (Cfg.SPLIT_ABUND_ABUND_COUNTS, Cfg.FINAL_COUNT)


#NEED IF STATMENT BASED UPON DB SELECTION
if pipe.database == 'Greengenes':
    cp (Cfg.GG_RM_LINEAGE_TAX_PICK, Cfg.FINAL_TAX)
else:
    cp (Cfg.SILVA_RM_LINEAGE_TAX_PICK, Cfg.FINAL_TAX)
    

exec_cmnd( pipe.gen_cluster_split(Cfg.FINAL_FA, Cfg.FINAL_COUNT, Cfg.FINAL_TAX) )
ensure_file_exists(Cfg.CLUST_SPLIT_OUT)

exec_cmnd( pipe.gen_make_shared( Cfg.CLUST_SPLIT_OUT,
                                             Cfg.FINAL_COUNT,
                                             Cfg.POINT_ZERO_THREE_LABL ) )
ensure_file_exists(Cfg.MAKE_SHARED_OUT)

cp(Cfg.MAKE_SHARED_OUT, Cfg.FINAL_OTU_SHARED)

pipe.make_design_file( pipe.map_file )
ensure_file_exists(Cfg.DESIGN_FILE)

exec_cmnd( pipe.gen_metastats(Cfg.FINAL_OTU_SHARED, Cfg.DESIGN_FILE) )
mkdir (Cfg.METASTATS_DIR)
cp (glob('*.metastats'), Cfg.METASTATS_DIR)

#NEED IF STATMENT BASED UPON DB SELECTION
if pipe.database == 'Greengenes':
    exec_cmnd( pipe.gen_classify_otus_cmd( list_file=Cfg.CLUST_SPLIT_OUT,
                                           counts_file=Cfg.FINAL_COUNT,
                                           tax=Cfg.FINAL_TAX,
                                           ref_taxonomy= Cfg.GG_TAX) )
else:
    exec_cmnd( pipe.gen_classify_otus_cmd( list_file=Cfg.CLUST_SPLIT_OUT,
                                           counts_file=Cfg.FINAL_COUNT,
                                           tax=Cfg.FINAL_TAX,
                                           ref_taxonomy= Cfg.SILVA_SEED_TAX) )   

exec_cmnd( pipe.gen_tree_shared( Cfg.FINAL_OTU_SHARED ) )
ensure_file_exists([Cfg.TREE_SHARED_JCLASS, Cfg.TREE_SHARED_THETAYC])

exec_cmnd( pipe.gen_summary_single_cmd( Cfg.FINAL_OTU_SHARED ))
ensure_file_exists(Cfg.FINAL_OTU_GRPS_SMMRY)
exec_cmnd( pipe.gen_make_lefse_cmnd( Cfg.FINAL_OTU_SHARED,
                                     pipe.map_file,
                                     Cfg.CLASSIFY_OTUS_TAX ) )

# NEED IF STATMENT BASED UPON DB SELECTION
if pipe.database == 'Greengenes':   
    exec_cmnd( pipe.gen_make_biom_no_picrust( Cfg.FINAL_OTU_SHARED,
                                   Cfg.CLASSIFY_OTUS_TAX,
                                   Cfg.GG_TAX ) )
else:
    exec_cmnd( pipe.gen_make_biom_no_picrust( Cfg.FINAL_OTU_SHARED,
                                   Cfg.CLASSIFY_OTUS_TAX,
                                   Cfg.SILVA_TAX ) )

ensure_file_exists(Cfg.FINAL_BIOM)


#exec_cmnd( pipe.gen_make_biom( Cfg.FINAL_OTU_SHARED,
#                              Cfg.CLASSIFY_OTUS_TAX,
#                               Cfg.DB_NUM_TO_OTU_TAX_MAP[int(pipe.reference_database)],
#                               Cfg.GG_TAX ) )
#ensure_file_exists([Cfg.FINAL_BIOM, Cfg.FINAL_BIOM_SHARED])

exec_cmnd( pipe.gen_phylotype( Cfg.FINAL_TAX ) )
ensure_file_exists([Cfg.FINAL_TX_SABUND, Cfg.FINAL_TX_RABUND, Cfg.FINAL_TX_LIST])

exec_cmnd( pipe.gen_make_shared(Cfg.FINAL_TX_LIST, Cfg.FINAL_COUNT, '1') )
ensure_file_exists(Cfg.FINAL_TX_SHARED)
cp( Cfg.FINAL_TX_SHARED, Cfg.FINAL_PHYLOTYPE_SHARED )

exec_cmnd( pipe.gen_classify_otus_cmd(list_file=Cfg.FINAL_TX_LIST,
                                      counts_file=Cfg.FINAL_COUNT,
                                      tax=Cfg.FINAL_TAX,
                                      label='1') )
ensure_file_exists([Cfg.FINAL_TX_CONS_TAX, Cfg.FINAL_TX_CONS_TAX_SMRMY])

exec_cmnd( pipe.gen_tree_shared(Cfg.FINAL_PHYLOTYPE_SHARED) )

exec_cmnd( pipe.gen_dist_seqs(Cfg.FINAL_FA) )
ensure_file_exists(Cfg.FINAL_PHYLIP_DIST)

exec_cmnd( pipe.gen_clearcut(Cfg.FINAL_PHYLIP_DIST) )
ensure_file_exists(Cfg.FINAL_PHYLIP_TRE)

exec_cmnd( pipe.gen_unifrac_unweighted(Cfg.FINAL_PHYLIP_TRE, Cfg.FINAL_COUNT) )
ensure_file_exists([Cfg.FINAL_PHYLIP_UWSMRY,Cfg.FINAL_PHYLIP_UNWEIGHTED_DIST])

exec_cmnd( pipe.gen_unifrac_weighted(Cfg.FINAL_PHYLIP_TRE, Cfg.FINAL_COUNT) )
ensure_file_exists([Cfg.FINAL_PHYLIP_WSMRY, Cfg.FINAL_PHYLIP_WEIGHTED_DIST])

exec_cmnd( pipe.gen_pcoa(Cfg.FINAL_PHYLIP_UNWEIGHTED_DIST) )
exec_cmnd( pipe.gen_pcoa(Cfg.FINAL_PHYLIP_WEIGHTED_DIST) )

exec_cmnd( pipe.gen_otu_rep(Cfg.FINAL_COUNT, Cfg.FINAL_FA, Cfg.CLUST_SPLIT_OUT) )

exec_cmnd( pipe.gen_biom_summarize_table( Cfg.FINAL_BIOM, Cfg.OTU_BIOM_SUMMARY) )

exec_cmnd( pipe.gen_sort_otu_table(Cfg.FINAL_BIOM, pipe.map_file, 'TreatmentGroup') )

taxa_levels = ["Phylum", "Class", "Order", "Family", "Genus"]
for taxa in taxa_levels:
    exec_cmnd( pipe.gen_betterplots( Cfg.SORTED_BIOM, pipe.map_file, taxa ))

depth = int( Cfg.DEPTH_SCALER * pipe.lookup_max_depth_from_biom_summry( Cfg.OTU_BIOM_SUMMARY ) )
all_tgs = pipe.lookup_tgs_from_map_file( pipe.map_file )

if len(pipe.samples) > Cfg.MIN_NUM_SAMPLES_FOR_CD:
    exec_cmnd( pipe.gen_core_diversity_analysis( Cfg.SORTED_BIOM, pipe.map_file, all_tgs, depth ))
else:
    log.info('Due to there being only {0} samples listed core diversity analysis cannot be performed\n'
             .format(len(pipe.samples)))
#exec_cmnd( pipe.gen_otu_heatmap_cmd (Cfg.SORTED_BIOM) )
do_end_operations()
exit(0)
