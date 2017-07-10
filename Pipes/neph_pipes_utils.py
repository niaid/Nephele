#!/usr/bin/env python
import warnings
import os
import re
import json
import glob
import sys
from subprocess import call
import zipfile
import tarfile
from collections import namedtuple
import subprocess
import shlex
import logging
import multiprocessing
import csv
from sh import mkdir, rm, mv, gunzip, guess_fq_score_type, wget, unzip, cp
import neph_errors
import xlrd
import cfg
from common_utils import *

File_to_link_name = namedtuple('File_to_link_name', 'fname lname')

# trimo = java.bake('-jar', '/usr/share/Trimmomatic-0.36/trimmomatic-0.36.jar')

def setup_logger(file_name):
    # setting up logging with two files,
    # one logging at level info (logfile.txt)
    # one logging at level debug (warnings)
    formatter = logging.Formatter(fmt='[%(levelname)s ] %(message)s\n')

    fh = logging.FileHandler(file_name)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    logger = logging.getLogger('Base')
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    return logger

def lookup_job_id():
    log = logging.getLogger('Base')
    if os.path.isfile('env.json'):
        with open('env.json') as data_file:
            data = json.load(data_file)
            if 'jobId' in data.keys():
                return data['jobId']
            else:
                log.error('No jobId could be found in env.json \n' + data)

def push_results_to_aws():
    j_id = lookup_job_id()
    log = logging.getLogger('Base')
    if j_id is None:
        log.info("I'm not going to push any results, because I have no env.json file")
        return None

    for f in cfg.FILES_TO_CP_TO_S3:
        dest = cfg.S3_BASE_BUCKET + j_id + '/out/'+ j_id +'_' + f
        log.info('Copying ' + f + ' to ' + dest)
        return '/usr/local/bin/aws s3 cp ' + f + ' ' + dest
            #cfg.aws_cp_s3(f, dest)


def ignore_mac_osx_files(files):
    ret = list()
    for f in files:
        if '__MACOSX' not in f:
            ret.append(f)
    return ret

def unzip_and_junk_path(fname):
    files_unzipped = list()
    with zipfile.ZipFile(fname) as zf:
        files_unzipped = [os.path.basename(f) for f in ignore_mac_osx_files(zf.namelist())]
        unzip('-jo', fname)     # -o is overwrite
    return files_unzipped

def unzip_input_file(fname):
    if zipfile.is_zipfile(fname):
        files = unzip_and_junk_path(fname)
    for f in files:
        if f.endswith('.gz'):
            gunzip('-f', f)

def ensure_file_is_csv(fname):
    fname_no_ext, ext = os.path.splitext(fname)
    if ext.lower() == '.csv' or ext.lower() == '.txt' or ext.lower() == '.mapping':
        return fname
    elif ext.lower() == '.xlsx' or ext.lower() == '.xls':
        csv_fname = fname_no_ext + '.csv'
        wb = xlrd.open_workbook(fname)
        sheet = wb.sheet_by_index(0)
        with open(csv_fname, 'w') as f:
            c = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_NONE)
            for rownum in range(sheet.nrows):
                c.writerow(sheet.row_values(rownum))
        return csv_fname
    else:
        exit(1)

def fix_EOL_char(fname):
    log = logging.getLogger('Base')
    log.info('checking EOL on ' + fname)
    if not os.path.isfile(fname):
        log.error(neph_errors.NO_FILE_ERROR)
        log.error(" " + fname)
    if fname.endswith('.sff') or fname.endswith('.qual'):
        return fname
    with open(fname, 'rU') as infile:
        text = infile.read()  # Automatic("Universal read") conversion of newlines to "\n"
    with open(fname, 'w') as outfile:
        outfile.write(text)
    return fname

def get_mem():
    return int(syscall("cat /proc/meminfo | grep MemTotal | awk '{ print $2 }'"))

def exec_cmnd(cmds, log):
    if cmds is None:
        return
    if isinstance(cmds, str):
        l = list()
        l.append(cmds)
        cmds = l
    while len(cmds) > 0:
        cmd = cmds.pop()
        log.info(cmd)
        try:
            if cmd.startswith('mothur'): # this might not be needed
                os.system(cmd)
            else:
                args = shlex.split(cmd)
                e = subprocess.check_output(args, stderr=subprocess.STDOUT)
                if len(e) > 0:
                    print(e)
        except subprocess.CalledProcessError as cpe:
            out_bytes = cpe.output       # Output generated before error

def strip_zip_ext(fname):
    r = fname.replace('.gz', '')
    s = r.replace('.zip', '')
    return s
    # ext_name = os.path.splitext(fname)[1]
    # zip_exts = ['.zip', '.gz']
    # if ext_name in zip_exts:
    #     return os.path.splitext(ext_name)[0]
    # else:
    #     return fname


def mothurize(func_name, args):
    return 'mothur "#' + func_name + '(' + ','.join(args) + ')"'

# def convert_qual_scores_to_phred64(sample):
#     if type(sample).__name__ == 'Sample':
#   mv(sample.fwd_fq_file, sample.fwd_fq_file + '.orig')
#   mv(sample.rev_fq_file, sample.rev_fq_file + '.orig')
#         trimo('PE', '-phred33', sample.fwd_fq_file + '.orig', sample.rev_fq_file + '.orig',
#               sample.fwd_fq_file, sample.fwd_fq_file + '.err',
#               sample.rev_fq_file, sample.rev_fq_file + '.err',
#               'TOPHRED64')
#     elif type(sample).__name__ == 'Sample_SE_mplex':
#         mv(sample.fwd_fq_file, sample.fwd_fq_file + '.orig')
#   trimo('SE', '-phred33', sample.fwd_fq_file + '.orig',
#               sample.fwd_fq_file, sample.fwd_fq_file + '.err',
#         'TOPHRED64')


def ensure_gt_1_cat_in_C_opts(fname, putative_cats):
    import pandas
    df = pandas.read_csv(fname, sep='\t')
    l = list()
    for cat in putative_cats:
        if len(df[cat].unique()) > 1:
            l.append(cat)
    return l

def get_C_opt_from_file(map_file):
    # first C_OPT is going to always be TreatmentGroup
    # this is always going to be in a col named TreatmentGroup
    # there may be other cols after TG, which we care about as c options
    # take all these cols, and comma delim them and present them as additional c_opts
    # Description is always the last col, and we always ignor it for this
    # ie we need everything between TG(col 6) and the last col -1
    # MCP-1137 fix for core diversity options
    # log = logging.getLogger('Base')
    c_opts = list()
    with open(map_file) as f:
        for line in f:
            line_as_list = line.strip().split("\t")
            if line.startswith('#SampleID'):     # we only care about the header
                line = line.rstrip()
                line_as_list = line.split("\t")
                if 'ReversePrimer' in line_as_list:
                    line_as_list.remove("ReversePrimer")
                try: pos = line_as_list.index('TreatmentGroup')
                except:
                    # log.error(neph_errors.NO_TREATMENT_GROUP)
                    #log.error('There is no column named "TreatmentGroup"')
                    return 'TreatmentGroup'
                total = len(line_as_list)
                pos_des = line_as_list.index('Description')
                for elt in line_as_list[pos:pos_des]:
                    c_opts.append(elt)
    if len(c_opts) > 0:
        return ','.join(ensure_gt_1_cat_in_C_opts(map_file, c_opts))

class Config:
    # strings, named tuples, bools, ints, files, arrays of files, URLs
    bool_fields = ['COMP_WITH_DACC', 'REVERSE_COMPLEMENT', 'CHIMERA',
                   'CORE_DIVERSITY_ANALYSES', 'BOOTSTRAPPED_TREE',
                   'INTERACTIVE_OTU_HEATMAP', 'DIFFERENTIAL_OTU_ENRICHMENT',
                   'BC_IS_FWD', 'FUNCTIONAL_ENRICHMENT', 'DEBUG', 'IS_DEMULTIPLEX',
                   'CORE_MICROBIOME', 'PICRUST']
    # 'DISABLE_BARCODE_CORRECTION'
    int_fields = ['Q_PARAM', 'N_PARAM', 'BC_LEN', 'MIN_SEQ_LENGTH', 'MAX_AMBIGUOS',
                  'MAX_HOMOPOLYMER', 'MAX_PRIMER_MISMATCH', 'MAX_SEQ_LENGTH',
                  'MIN_QUAL_SCORE', 'QUALITY_SCORE_WINDOW', 'MAX_BAD_RUN_LENGTH',
                  'MIN_OVERLAP', 'PERC_MAX_DIFF', 'NEAREST_N_SAMPLES']

    float_fields = ['FRACTION_OF_MAXIMUM_SAMPLE_SIZE', 'MAX_BARCODE_ERRORS']

    file_fields = ['REF_FASTA_FILE', 'REF_TAXONOMY_FILE', 'TREE_FILE',
                   'OTUS_PARAMS_FILE', 'LOG_FILE', 'FWD_FQ_FILE', 'REV_FQ_FILE',
                   'BC_FILE', 'FASTQ_FILE', 'FASTA_FILE', 'QUAL_FILE']

    str_fields = ['AMI_ID', 'PIPELINENAME', 'EMAIL', 'USECODE', 'INSTANCETYPE',
                  'TEST_FILES', 'HMP_DATABASE', 'REGION_DACC']

    VALID_INPUT_TYPE = ['MISEQ_MULTIPLEX', 'MISEQ_PAIR-END', 'FASTQ_SINGLE-END',
                        'RAW_SFF_FILE', 'FASTA_QUAL_FILES']

    VALID_ANALYSIS_TYPE = ['DE_NOVO', 'OPEN_REFERENCE', 'CLOSED_REFERENCE',
                           'OPEN_REFERENCE_ITS']


    VALID_ERROR_CORR_PRIM_FORMATS = ['HAMMING_8', 'GOLAY_12', 'VARIABLE_LENGTH']

    # list of pipe types that run gen_paired_end
    runs_gen_paired_end = ['MISEQ_MULTIPLEX', 'MISEQ_PAIR-END']

    false_arr = ['NO', 'N', 'FALSE']
    true_arr = ['YES', 'Y', 'TRUE']

    samples = list()
    bc_file = None

    def __init__(self, kwargs):
        self.log = logging.getLogger('Base')
        self.warnings_log = logging.getLogger('warnings')
        self.cmds = list()
        mkdir('-p', cfg.COLLATED_OUT_DIR)
        for key in ['MAP_FILE', 'RAW_FILE_FULL', 'ANALYSIS_TYPE', 'PICRUST',
                    'INPUT_TYPE', 'DATABASE', 'ERROR_CORR_PRIM_FORMATS',
                    'MIN_SEQ_LENGTH', 'MAX_AMBIGUOS', 'MAX_HOMOPOLYMER',
                    'MAX_PRIMER_MISMATCH', 'MAX_BARCODE_ERRORS', 'QUALITY_SCORE_WINDOW',
                    'MAX_SEQ_LENGTH', 'MIN_QUAL_SCORE', 'FASTA_FILE', 'CORE_MICROBIOME',
                    'BODY_SITE', 'COMP_WITH_DACC', 'REVERSE_COMPLEMENT', 'CHIMERA',
                    'CORE_DIVERSITY_ANALYSES', 'BOOTSTRAPPED_TREE',
                    'INTERACTIVE_OTU_HEATMAP', 'DIFFERENTIAL_OTU_ENRICHMENT',
                    'BC_IS_FWD', 'FUNCTIONAL_ENRICHMENT', 'IS_DEMULTIPLEX',
                    'Q_PARAM', 'N_PARAM', 'BC_LEN', 'MAX_BAD_RUN_LENGTH',
                    'MIN_OVERLAP', 'PERC_MAX_DIFF', 'FRACTION_OF_MAXIMUM_SAMPLE_SIZE',
                    'REF_FASTA_FILE', 'REF_TAXONOMY_FILE', 'TREE_FILE',
                    'OTUS_PARAMS_FILE', 'LOG_FILE', 'FWD_FQ_FILE', 'REV_FQ_FILE',
                    'BC_FILE', 'FASTQ_FILE', 'QUAL_FILE', 'HMP_DATABASE',
                    'NEAREST_N_SAMPLES', 'REGION_DACC']:
            if key not in kwargs:
                continue
            value = kwargs[key]
            if value == '':
                self.log.debug('{0} is being left unassigned'.format(key))
            elif key.upper() == 'MAP_FILE':
                if os.path.isfile(value):
                    self.map_file = ensure_file_is_csv(value)
                else:
                    self.log.error(neph_errors.NO_FILE_ERROR)
            elif key.upper() == 'RAW_FILE_FULL':
                if os.path.isfile(value):
                    filename, file_extension = os.path.splitext(value)
                    if file_extension.upper() == '.SFF':
                        self.raw_file_full = value
                    elif file_extension.upper() == '.ZIP':
                        if zipfile.is_zipfile(value):
                            unzip_input_file(value)
                        self.raw_file_full = strip_zip_ext(value)
            elif key.upper() in self.bool_fields:
                if value.upper() in self.true_arr:
                    setattr(self, key.lower(), True)
                elif value.upper() in self.false_arr:
                    setattr(self, key.lower(), False)
                else:
                    raise Exception('"{0}" can only be assigned YES or NO, "{1}"'\
                                    'is not permitted.'.format(key, value))
            elif key in self.int_fields:
                try:
                    setattr(self, key.lower(), int(value))
                except ValueError as v:
                    self.log.error("{0} can only be an Integer, {1} is not permitted."\
                                   "\nValueError.".format(key, value))
                except:
                    self.log.error('Unexpected error. "{0}:{1}"\n{3}'.
                                   format(key, value, sys.exc_info()[0]))
                    raise
            elif key.upper() in self.str_fields:
                setattr(self, key.lower(), value)
                if value == '':
                    warnings.debug('Warning: setting "{0}" to nothing'.format(key))
            elif key.upper() == 'INPUT_TYPE':
                if value.upper() in self.VALID_INPUT_TYPE:
                    setattr(self, 'pipe_name', value.upper())
                else:
                    raise ValueError('{0} can only be one of the following:{1}. "{2}"'\
                                     'not permitted.'.format(
                                         key, ','.join(self.VALID_INPUT_TYPE), value))
            elif key.upper() == 'ANALYSIS_TYPE':
                if value.upper() in self.VALID_ANALYSIS_TYPE:
                    setattr(self, key.lower(), value)
                else:
                    raise ValueError('{0} can only be one of the following:{1}. "{2}"'\
                                     'not permitted.'
                                     .format(key,
                                             ','.join(self.VALID_ANALYSIS_TYPE), value))
            elif key.upper() == 'BODY_SITE':
                self.body_site = value
            elif key.upper() == 'REGION_DACC':
                self.region_dacc = value
            elif key.upper() == 'NEAREST_N_SAMPLES':
                self.nearest_n_samples = value
            elif key.upper() == 'HMP_DATABASE':
                self.hmp_database = value
            elif key.upper() == 'DATABASE':
                if value not in cfg.HMP_REF_TAXONOMY_FILE.keys():
                    self.log.error('Only values Greengenes_94, Greengenes_97,'
                                   'Greengenes_99, SILVA_97, SILVA_99, ITS_97, ITS_99.'
                                   'Not: {0}'.format(value))
                    self.do_exit_operations()
                    exit(1)
                else:
                    self.database = value
                    self.ref_fasta_file = cfg.HMP_REF_FASTA_FILE[self.database]
                    self.ref_taxonomy_file = cfg.HMP_REF_TAXONOMY_FILE[self.database]
                if self.analysis_type != 'OPEN_REFERENCE_ITS':
                    # do not use Tree files for ITS pipes.
                    self.tree_file = cfg.HMP_TREE_FILE[value]
            elif key.upper() == 'MAP_FILE':
                if os.path.isfile(value):
                    self.map_file = ensure_file_is_csv(value)
                else:
                    self.log.error(neph_errors.NO_FILE_ERROR)
            elif key.upper() == 'ERROR_CORR_PRIM_FORMATS':
                if value == "Barcode length from mapping file":
                    setattr(self, 'barcode_type', str(get_bc_len_from_map_file(self.map_file)))
                elif value.upper() in self.VALID_ERROR_CORR_PRIM_FORMATS:
                    setattr(self, 'barcode_type', value)
                else:
                    raise ValueError('{0} can only be one of the following:{1}. "{2}" not permitted.'\
                                     .format(key, ','.join(self.VALID_ERROR_CORR_PRIM_FORMATS), value))
            elif key.upper() == 'READS_ZIP':
                if os.path.isfile(value):
                    unzip_input_file(value)
            elif key.upper() in self.file_fields:
                if os.path.isfile(value):
                    filename, file_extension = os.path.splitext(value)
                    if file_extension.upper() == '.ZIP':
                        if zipfile.is_zipfile(value):
                            unzip_input_file(value)
                            setattr(self, key.lower(), strip_zip_ext(value))
                    else:
                        setattr(self, key.lower(), value)
                # if not os.path.isfile(value):
                #     value = strip_zip_ext(value)

                # if not os.path.isfile(value):
                #     self.log.error(neph_errors.NO_FILE_ERROR)
                #     self.log.error('{0} does not exist.'.format(value))
                #     self.do_exit_operations()
                #     exit(1)
                # if ' ' in value:
                #     os.rename(value, value.replace(' ', '-'))
                #     value = value.replace(' ', '-')
                # if tarfile.is_tarfile(value):
                #     untarred_files = list()
                #     with tarfile.open(value, "r") as tar_f:
                #         untarred_files = tar_f.getnames()
                #         print('setting ' + key.lower() + 'to' + untarred_files)
                #         setattr(self, key.lower(), untarred_files)
                #     tar('xf', value)
                #     if len(untarred_files) > 0:
                #         for f in untarred_files:
                #             gunzip('--force', f)
                #     else:
                #         setattr(self, key.lower(), fix_EOL_char(value))

            elif key.upper() in self.float_fields:
                if key.upper() == 'FRACTION_OF_MAXIMUM_SAMPLE_SIZE':
                    if float(value) >= 1:
                        self.fraction = False
                        self.sample_depth = int(Decimal(value))
                    elif float(value) < 1 and float(value) > 0:
                        self.fraction = float(value)
                        self.sample_depth = False
                    else:
                        self.fraction = 0.1
                        self.sample_depth = False

                elif key.upper() == 'MAX_BARCODE_ERRORS':
                    self.max_barcode_errors = float(value)
            elif 'DEBUG' in kwargs and kwargs['DEBUG'] == 'YES':
                warnings.debug('Warning, ignoring field {0}({1})'.format(key, value))

        # THIS IS POST / HARD WIRED / DEFAULTS
        # place for files
        if not hasattr(self, 'picrust'):
            self.picrust = False
        if self.analysis_type == 'OPEN_REFERENCE_ITS':
            self.picrust = False
        if self.picrust:
            self.log.info(neph_errors.PICRUST_GG_WARN)
            self.database = 'Greengenes_99'
            self.ref_fasta_file = cfg.HMP_REF_FASTA_FILE[self.database]
            self.ref_taxonomy_file = cfg.HMP_REF_TAXONOMY_FILE[self.database]
            self.tree_file = cfg.HMP_TREE_FILE[self.database]
        if self.analysis_type == 'CLOSED_REFERENCE' or self.analysis_type == 'OPEN_REFERENCE_ITS':
            self.chimera = False
        elif not hasattr(self, 'chimera'):
            self.chimera = True
        elif self.chimera == '' or self.chimera is None:
            self.chimera = True

        if not hasattr(self, 'is_demultiplex'):
            self.is_demultiplex = False

        self.samples = self.load_map_file()

        self.has_overide_core_div = False
        if self.pipe_name == 'MISEQ_PAIR-END':
            self.has_barcode = True
        else:
            self.has_barcode = False
        if not hasattr(self, 'otus_params_file'):
            self.otus_params_file = cfg.DEFAULT_OTU_PARAMS_FNAME
        if not hasattr(self, 'log_file'):
            self.log_file = cfg.LOG_FILE
        for sw in cfg.QIIME_SW_VERS:
            self.log.info('Software Versions: ' +sw)
        self.do_run_core_div = True # init to true
        #self.log.info("\n" + self.__repr__())
        self.log.info('Pipeline started')


    # def assign_file(self, key, fname):
    #     if os.path.isfile(strip_zip_ext(fname)):
    #         fix_EOL_char(strip_zip_ext(fname))
    #         setattr(self, key.lower(), strip_zip_ext(str(fname)))
    #         # even if it's not set, I'm setting to default
    #     elif key.upper() == 'OTUS_PARAMS_FILE' and fname == '':
    #         self.otus_params_file = cfg.DEFAULT_OTU_PARAMS_FNAME
    #     elif key.upper() == 'LOG_FILE':
    #         self.log_file = fname
    #     elif key.upper() == 'FWD_FQ_FILE' and fname.endswith == '.gz':
    #         self.fwd_fq_file = fix_EOL_char(strip_zip_ext(fname))
    #     elif key.upper() == 'REV_FQ_FILE' and fname.endswith == '.gz':
    #         self.rev_fq_file = fix_EOL_char(strip_zip_ext(fname))
    #     else:
    #         raise IOError

    def gen_compare_to_HMP_cmd(self):
        if self.comp_with_dacc:
            self.cmds.append('./betadiv.py '\
                              + " --user_seqs=" + cfg.SPLIT_LIB_OUT_DIR+'/seqs.fna'\
                              + " --body_site=" + self.body_site\
                              + " --map_file=" + self.map_file\
                              + " --hmp_database=" + self.hmp_database\
                              + " --nearest_n_samples=" + str(self.nearest_n_samples)\
                              + " --region_dacc=" + self.region_dacc)
        return self
    def gen_phyloseq_images_cmd(self):
        taxa_levels = ["Phylum", "Class", "Order", "Family", "Genus"]
        if self.database.upper() in ["GREENGENES_99", "GREENGENES_97"]:
            taxa_levels = ["Phylum", "Class", "Order", "Family", "Genus", "Species"]
        for taxa in taxa_levels:
            self.cmds.append('Rscript betterplots.R '\
                               + " " + self.lookup_biom_file()\
                               + " " + self.map_file\
                               + " " + taxa\
                               + " NO")
        return self

    def update_otus_params_file_for_ITS(self):
        if self.analysis_type == 'OPEN_REFERENCE_ITS':
            with open(self.otus_params_file, 'a') as f_out:
                print('assign_taxonomy:id_to_taxonomy_fp {0}'
                      .format(self.ref_taxonomy_file), file=f_out)
                print('assign_taxonomy:reference_seqs_fp {0}'
                      .format(self.ref_fasta_file), file=f_out)

    def exec_cmnd_and_log(self):
        all_commands = self.cmds
        while len(all_commands) > 0:
            cmd = all_commands.pop(0)
            if cmd is False:
                continue
            self.log.info("Trying : " + cmd)
            try:
                if cmd.startswith('mothur'):
                    os.system(cmd)
                else:
                    args = shlex.split(cmd)
                    e = subprocess.check_output(args, stderr=subprocess.STDOUT)
                    if len(e) > 0:
                        self.log.warn(e)
            except subprocess.CalledProcessError as cpe:
                out_bytes = cpe.output       # Output generated before error
                self.log.exception(out_bytes)
                self.cmds = list()
                self.do_exit_operations()
                exit(1)         # emit error
        self.cmds = list()

    def do_exit_operations(self):
        for f_to_l in self.gather_all_files_to_link():
            if f_to_l is not None:
                self.try_to_link(f_to_l.fname, f_to_l.lname).exec_cmnd_and_log()
        self.zip_whole_dir().exec_cmnd_and_log()
        self.zip_results().exec_cmnd_and_log()
        # exec_cmnd_and_log('/usr/bin/python push_to_aws.py')
        # push_results_to_aws()
        # self.shutdown()


    def gen_shutdown_cmnd(self):
        self.cmds = ['sudo shutdown -h now']
        return self

    def shutdown(self):
        # testing : Am I launched by Nephele Website?
        # if I am I'll really shutdown, otherwise I'll carry on to next test.
        if lookup_job_id() is not None:
            self.gen_shutdown_cmnd().exec_cmnd_and_log()
        else:
            self.log.info('Pretending to shut down now...')

    def try_to_link(self, fname, link_name):
        if os.path.lexists(fname):
            if not fname.startswith('/'):
                fname = '../'+fname
            self.cmds = ['ln -s -f ' + fname + ' ' + link_name]
        return self

    def zip_whole_dir(self):
        everything = glob.glob('*')
        self.cmds = [cfg.ZIP_RECURS_QUIET + cfg.EVERYTHING_ZIP_FILE_NAME + " ".join(everything)]
        return self

    def zip_results(self):
        results = cfg.all_results
        log = logging.getLogger('Base')
        results.append(os.path.split(self.get_log_name())[1])
        self.cmds = [cfg.ZIP_RECURS_QUIET + ' ' + cfg.ALL_RESULTS_ZIP_FILE_NAME + " ".join(results)]
        return self

    def get_log_name(self):
        handler = self.log.handlers[0]
        return handler.baseFilename

    def gather_all_files_to_link(self):
        #       files_to_link.extend(self.get_taxa_out())
        files_to_link = list()
        files_to_link.extend(self.link_seqs_fasta())
        files_to_link.extend(self.link_otu_biom_file())
        files_to_link.extend(self.link_tre_file())
        files_to_link.extend(self.link_samples_being_ignored())
        files_to_link.extend(self.link_jackknifed_pdfs())
        files_to_link.extend(self.link_metastats_files())
        files_to_link.extend(self.link_no_pynast_failures_biom_summaray())
        files_to_link.extend(self.link_no_pynast_failures_lefse())
        files_to_link.extend(self.link_config_run_params())
        files_to_link.extend(self.get_heatmap_outs())
        files_to_link.extend(self.link_logfile())
        files_to_link.extend(self.get_core_microbiome_dirs())
        files_to_link.extend(self.get_chimera_out())
        files_to_link.extend(self.get_alpha_out())
        files_to_link.extend(self.get_phyloseq_images())
        files_to_link.extend(self.get_mapping_file())
        files_to_link.extend(self.get_runtime_file())
        files_to_link.extend(self.get_picrust_data())
        return files_to_link

    def get_runtime_file(self):
        return [File_to_link_name(fname='runtime.txt', lname=cfg.COLLATED_OUT_DIR)]

    def get_mapping_file(self):
        return [File_to_link_name(fname=self.map_file, lname=cfg.COLLATED_OUT_DIR)]

    def get_chimera_out(self):
        return [File_to_link_name(fname=cfg.CHIMERA_FILE, lname=cfg.COLLATED_OUT_DIR)]

    def get_taxa_out(self):
        return [File_to_link_name(fname=cfg.TAXA_PLOTS_OUT_DIR, lname=cfg.COLLATED_OUT_DIR)]

    def get_alpha_out(self):
        return [File_to_link_name(fname=cfg.ALPHA_RAREFACTION_OUT_DIR, lname=cfg.COLLATED_OUT_DIR)]

    def get_heatmap_outs(self):
        return [File_to_link_name(fname=cfg.HEATMAP_OUT_DIR + '/heatmap.svg',
                                  lname=cfg.COLLATED_OUT_DIR)]

    def link_seqs_fasta(self):
        return [File_to_link_name(fname=cfg.SPLIT_LIB_OUT_DIR+'/seqs.fna',
                                  lname=cfg.COLLATED_OUT_DIR
                                  +'/reads_used_for_analysis.fasta')]

    def link_config_run_params(self):
        return [File_to_link_name(fname='config.csv',
                                  lname=cfg.COLLATED_OUT_DIR
                                  +'/job_parameters_run_settings.csv')]

    def link_logfile(self):
        return [File_to_link_name(fname=self.get_log_name(),
                                  lname=cfg.COLLATED_OUT_DIR)]

    def link_otu_biom_file(self):
        l = list()
        l.append(File_to_link_name(
            fname=cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax_no_pynast_failures.biom',
            lname=cfg.COLLATED_OUT_DIR + '/OTU_table.biom'))
        l.append(File_to_link_name(fname=cfg.PICK_OTUS_OUT_DIR + '/otu_table.biom',
                                   lname=cfg.COLLATED_OUT_DIR + '/OTU_table.biom'))
        return l

    def link_tre_file(self):
        tre_file = self.get_tre_file()
        if tre_file.startswith('/usr'):
            return [File_to_link_name(fname=tre_file, lname=cfg.COLLATED_OUT_DIR + '/tree.tre')]
        else:
            return [File_to_link_name(fname=tre_file, lname=cfg.COLLATED_OUT_DIR + '/tree.tre')]

    def link_jackknifed_pdfs(self):
        l = list()
        weighted_jk = cfg.JACKKNIFED_OUT_DIR \
                      + '/weighted_unifrac/upgma_cmp/jackknife_named_nodes_weighted.pdf'
        unweighted_jk = cfg.JACKKNIFED_OUT_DIR \
                        + '/unweighted_unifrac/upgma_cmp/jackknife_named_nodes_unweighted.pdf'
        l.append(File_to_link_name(fname=weighted_jk, lname=cfg.COLLATED_OUT_DIR))
        l.append(File_to_link_name(fname=unweighted_jk, lname=cfg.COLLATED_OUT_DIR))
        return l

    def link_samples_being_ignored(self):
        return [File_to_link_name(fname=cfg.PICK_OTUS_OUT_DIR
                                  +'/samples_being_ignored.txt',
                                  lname=cfg.COLLATED_OUT_DIR)]

    def link_no_pynast_failures_biom_summaray(self):
        return [File_to_link_name(fname=self.lookup_biom_file() +'.summary.txt',
                                  lname=cfg.COLLATED_OUT_DIR + '/otu_table.summary.txt')]

    def link_no_pynast_failures_lefse(self):
        return [File_to_link_name(fname=cfg.PICK_OTUS_OUT_DIR + '/otu_table.dummy.lefse',
                                  lname=cfg.COLLATED_OUT_DIR + '/otu_table.lefse')]

    def get_core_microbiome_dirs(self):
        l = list()
        if self.core_microbiome:
            files = glob.glob(cfg.COMPUTE_CORE_MICROBIOME_OUT_DIR + '*')
            for f in files:
                l.append(File_to_link_name(fname=f, lname=cfg.COLLATED_OUT_DIR))
        return l

    def get_phyloseq_images(self):
        l = list()
        files = glob.glob(cfg.PHYLOSEQ_IMAGES_DIR + '*')
        for f in files:
            l.append(File_to_link_name(fname=f, lname=cfg.COLLATED_OUT_DIR))
        return l

    def get_picrust_data(self):
        l = list()
        if self.picrust:
            files = glob.glob(cfg.PICRUST_DIR + '*')
            for f in files:
                l.append(File_to_link_name(fname=f, lname=cfg.COLLATED_OUT_DIR))
        return l

    def link_metastats_files(self):
        l = list()
        if hasattr(self, 'differential_otu_enrichment'):
            ms_files = glob.glob(cfg.PICK_OTUS_OUT_DIR + '/*metastats')
            for f in ms_files:
                l.append(File_to_link_name(fname=f, lname=cfg.COLLATED_OUT_DIR))
        return l

    def write_chimera_count_to_file(self):
        if self.lookup_accnos_file():
            (num_lines, _) = cfg.line_count(self.lookup_accnos_file()).split()
            self.log.info(num_lines + ' chimeras found.')
            with open(cfg.CHIMERA_FILE, 'w') as f_out:
                print(num_lines + ' chimeras found.\n', file=f_out)

    def get_join_paired_end_outputs(self):
        outs = list()
        if self.pipe_name == 'MISEQ_PAIR-END':
            for sample in self.samples:
                outs.append(sample.sample_id + '/fastqjoin.join.fastq')
        elif self.pipe_name == 'MISEQ_MULTIPLEX':
            otus = [cfg.JOINED_OUTS_OUT_DIR + '/fastqjoin.join.fastq']
        return outs

    def ensure_output_exists(self, fnames):
        if fnames is False:
            return
        if isinstance(fnames, str):
            l = list()
            l.append(fnames)
            fnames = l
        for fname in fnames:
            if os.path.isfile(fname) and os.stat(fname).st_size != 0:
                self.log.info("Output file {0} exists as expected. Can proceed"\
                              "to next step".format(fname))
            else:
                self.log.error(neph_errors.NO_FILE_ERROR)
                self.log.error("{0} does not exist.".format(fname))
                if fname.endswith("fastqjoin.join.fastq"):
                    self.log.error(neph_errors.BAD_JOINING)
                elif fname.endswith("seqs.fna"): # split lib out
                    self.log.error(neph_errors.TOO_FEW_READS_TRIMMING)
                elif fname.endswith(self.lookup_biom_file() + '.summary.txt'):
                    self.log.error(neph_errors.NO_BIOM_FILE)
                self.do_exit_operations()
                exit(1)

    def is_OK_SE_fq_mapping_file(self, fname):
        with open(fname) as f:
            r = csv.DictReader(f, delimiter='\t')
            if '#SampleID' in r.fieldnames\
               and 'BarcodeSequence' in r.fieldnames\
               and 'LinkerPrimerSequence' in r.fieldnames\
               and 'TreatmentGroup' in r.fieldnames\
               and 'Description' in r.fieldnames:
                return True
            else:
                return False

    def load_SE_fq_mapping_file(self, fname):
        with open(fname) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if row['HMPbodysubsite'] == body_site:
                    relevant_samples.append(row['#SampleID'])

    def load_map_file(self):
        Sample = namedtuple('Sample', ['sample_id',
                                       'BarcodeSequence',
                                       'LinkerPrimerSequence',
                                       'fwd_fq_file',
                                       'rev_fq_file',
                                       'TreatmentGroup',
                                       'Description'])
        Sample_no_fwd_rev = namedtuple('Sample_no_fwd_rev', ['sample_id',
                                                             'BarcodeSequence',
                                                             'LinkerPrimerSequence',
                                                             'TreatmentGroup',
                                                             'Description'])
        Sample_SE_mplex = namedtuple('Sample_SE_mplex',
                                     ['sample_id',
                                      'fwd_fq_file',
                                      'TreatmentGroup',
                                      'Description'])
        l = list()

        with open(file_exists(self.map_file), 'r') as f:
            for line in nonblank_lines(f):
                line = line.strip()
                if line.startswith('#'):
                    continue
                if self.pipe_name == 'MISEQ_MULTIPLEX':
                    line_as_list = line.split("\t")
                    # 0 SampleID  # 1 BarcodeSequence  # 2 LinkerPrimerSequence
                    # 4 ForwardFastqFile # 5 ReverseFastqFile # 6 TreatmentGroup # 7 Description
                    treatmentgroup = ','.join(line_as_list[5:-1])

                    s = Sample(sample_id=line_as_list[0],\
                               BarcodeSequence=line_as_list[1],\
                               LinkerPrimerSequence=line_as_list[2],\
                               fwd_fq_file=file_exists(line_as_list[3]),\
                               rev_fq_file=file_exists(line_as_list[4]),\
                               TreatmentGroup=treatmentgroup,\
                               Description=line_as_list[-1])
                    l.append(s)

                elif self.pipe_name == 'MISEQ_PAIR-END':
                    line_as_list = line.split("\t")
                    pos_s_id = 0
                    pos_bc_seq = 1
                    pos_linker_primer_seq = 2
                    pos_fwd_fq = 3
                    pos_rev_fq = 4
                    pos_treat_group = 5
                    treatmentgroup = ','.join(line_as_list[pos_treat_group:-1])
                    s = Sample(sample_id=line_as_list[pos_s_id],\
                               BarcodeSequence=line_as_list[pos_bc_seq],\
                               LinkerPrimerSequence=line_as_list[pos_linker_primer_seq],\
                               fwd_fq_file=file_exists(line_as_list[pos_fwd_fq]),\
                               rev_fq_file=file_exists(line_as_list[pos_rev_fq]),\
                               TreatmentGroup=treatmentgroup,\
                               Description=line_as_list[-1])
                    l.append(s)
                elif self.pipe_name == 'FASTQ_SINGLE-END' or self.pipe_name == 'FASTA_QUAL_FILES':
                    line_as_list = line.split("\t")
                    if not self.is_demultiplex:
                        #SampleID BarcodeSequence LinkerPrimerSequence	TreatmentGroup	Description
#                       (SAMPLE_ID, BC_SEQ, LINKER_PRIMER_SEQ, TREATMENT, DESCRIPTION) = line.split("\t")
                        s = Sample_no_fwd_rev(sample_id=line_as_list[0],\
                                              BarcodeSequence=line_as_list[1],\
                                              LinkerPrimerSequence=line_as_list[2],\
                                              TreatmentGroup=line_as_list[3],\
                                              Description=line_as_list[-1])
                        l.append(s)
                    else:       # is_demultiplex
                        #SampleID BarcodeSequence LinkerPrimerSequence ForwardFastqFile	TreatmentGroup Description
#                       (S_ID, BC_SEQ, LINKER_PRIMER_SEQ, FWD_FQ_FILE, TRTMNT, DESC) = line.split("\t")
                        s = Sample_SE_mplex(sample_id=line_as_list[0],
                                            fwd_fq_file=line_as_list[3],
                                            TreatmentGroup=line_as_list[4],
                                            Description=line_as_list[-1])
                        l.append(s)

                elif self.pipe_name == 'RAW_SFF_FILE':
                    line_as_list = line.split("\t")
                    pos_s_id = 0
                    pos_bc_seq = 1
                    pos_linker_primer_seq = 2
                    pos_treat_group = 3
                    treatmentgroup = ','.join(line_as_list[pos_treat_group:-1])
                    s = Sample_no_fwd_rev(sample_id=line_as_list[pos_s_id],\
                                          BarcodeSequence=line_as_list[pos_bc_seq],\
                                          LinkerPrimerSequence=line_as_list[
                                              pos_linker_primer_seq],\
                                          TreatmentGroup=treatmentgroup,\
                                          Description=line_as_list[-1])
                    l.append(s)

        return l

    def log_no_run_bc_missing_file(self, file_name, step_name):
        self.log.error(neph_errors.NO_BARCODE_FILE)
        #self.log.error('Unable to execute {0} ends because file {1} does not exist.'
        #              .format(step_name, file_name))

    def gen_join_paired_end_cmd(self):
        if self.pipe_name in ['MISEQ_MULTIPLEX', 'MISEQ_PAIR-END']:
            if self.pipe_name == 'MISEQ_PAIR-END':
                for sample in self.samples:
                    if not os.path.isfile(sample.fwd_fq_file):
                        self.log_no_run_bc_missing_file(sample.fwd_fq_file, 'join_pair_ends.py')
                    elif not os.path.isfile(sample.rev_fq_file):
                        self.log_no_run_bc_missing_file(sample.fwd_fq_file, 'join_pair_ends.py')
                    else:
                        self.cmds.append(join_paired_endify(sample.fwd_fq_file,
                                                            sample.rev_fq_file,
                                                            sample.sample_id,
                                                            str(self.perc_max_diff),
                                                            str(self.min_overlap)))
            else:
                if not os.path.isfile(self.fwd_fq_file):
                    self.log_no_run_bc_missing_file(self.fwd_fq_file, 'join_pair_ends.py')
                elif not os.path.isfile(self.rev_fq_file):
                    self.log_no_run_bc_missing_file(self.fwd_fq_file, 'join_pair_ends.py')
                else:
                    command = "join_paired_ends.py "\
                              + " --output_dir=" + cfg.JOINED_OUTS_OUT_DIR\
                              + " --forward_reads_fp=" + self.fwd_fq_file\
                              + " --reverse_reads_fp=" + self.rev_fq_file\
                              + " --perc_max_diff=" + str(self.perc_max_diff)\
                              + " --min_overlap=" + str(self.min_overlap)
                    if self.bc_file is not None:
                        command += " --index_reads_fp=" + file_exists(self.bc_file)
                    self.cmds.append(command)
        return self

    def gen_filter_samples_from_otu_table_cmd(self, depth):
        if self.pipe_name == 'MISEQ_PAIR-END' or self.pipe_name == 'FASTQ_SINGLE-END':
            self.cmds.append('filter_samples_from_otu_table.py '\
                              + " --input_fp=" + self.lookup_biom_file()\
                              + " --output_fp=" + self.lookup_biom_file() + '.new'\
                              + " --min_count=" + str(depth))
        return self

    def mv_biom_file(self):
        if self.pipe_name == 'MISEQ_PAIR-END' or self.pipe_name == 'FASTQ_SINGLE-END':
            if os.path.isfile(self.lookup_biom_file()) \
               and os.path.isfile(self.lookup_biom_file() + '.new'):
                self.cmds.append('mv ' + self.lookup_biom_file() + ' '\
                                 + self.lookup_biom_file() + '.orig')
                self.cmds.append('mv ' + self.lookup_biom_file() + '.new '\
                                 + self.lookup_biom_file())
        return self

    def gen_per_sample_single_map_file(self):
        if self.pipe_name == 'MISEQ_PAIR-END':
            for sample in self.samples:
                dname = sample.sample_id
                if not os.path.isdir(dname):
                    self.log_no_run_bc_missing_file(dname, 'No output directory')
                else:
                    head = ['#SampleID', 'BarcodeSequence', 'LinkerPrimerSequence',
                            'ForwardFastqFile', 'ReverseFastqFile', 'TreatmentGroup',
                            'Description']
                    line = [sample.sample_id, sample.BarcodeSequence,
                            sample.LinkerPrimerSequence, \
                            sample.fwd_fq_file, sample.rev_fq_file, \
                            sample.TreatmentGroup, sample.Description]
                    with open(dname + '/' + 'map.txt', 'w') as f_out:
                        print("\t".join(head), file=f_out)
                        print("\t".join(line), file=f_out)

    def gen_validate_mapping_cmd(self):
        if self.pipe_name == 'MISEQ_PAIR-END':
            for sample in self.samples:
                if not os.path.isfile(sample.sample_id + '/' + 'map.txt'):
                    self.log_no_run_bc_missing_file(sample.sample_id + '/' + 'map.txt',
                                                    'validate_mapping_file.py')
                else:
                    self.cmds.append('validate_mapping_file.py '\
                                     + ' --mapping_fp=' + sample.sample_id + '/'
                                     + 'map.txt'\
                                     + ' --output_dir=' + sample.sample_id)
        else:
            if not os.path.isfile(self.map_file):
                self.log_no_run_bc_missing_file(self.map_file, 'validate_mapping_file.py')
            else:
                self.cmds = ['validate_mapping_file.py --mapping_fp=' + self.map_file]
        return self

    def gen_convert_fastaqual_fastq_cmd(self):
        if self.pipe_name == 'FASTQ_SINGLE-END' and not self.is_demultiplex:
            if not os.path.isfile(self.fastq_file):
                self.log_no_run_bc_missing_file(self.fastq_file, 'convert_fastaqual_fastq.py')
            else:
                self.cmds = ['convert_fastaqual_fastq.py '\
                              + ' --fasta_file_path=' + self.fastq_file\
                              + ' --conversion_type=fastq_to_fastaqual']
        return self

    def gen_split_lib_cmd(self):
        # In QIIME(a b and c) ie, 454, FASTA FASTQ
        # in all above cases, we want to do ERR correct primer format
        # using the -b arg on split_libs.
        # we have three choices here, ie
        # -b BARCODE_TYPE, barcode type, hamming_8, golay_12, variable_length
        #                    (will disable any barcode correction if
        #                     variable_length set), or a number representing the
        #                     length of the barcode, such as -b 4.  [default:
        #                     golay_12]
        # that means pick one. And, is in config as ERROR_CORR_PRIM_FORMATS
        # note that for MiSeq single and Multi, you don't use err correct prim formats.
        # barcode correction can be disabled with the -c option
        # -w            # ????
        # split_libraries.py -o sl_out
        # -b variable_length

        ret = None
        if(self.pipe_name == 'FASTQ_SINGLE-END' and not self.is_demultiplex)\
           or self.pipe_name == 'RAW_SFF_FILE' or self.pipe_name == 'FASTA_QUAL_FILES':
            ret = "split_libraries.py "
            ret += ' --dir_prefix=' + cfg.SPLIT_LIB_OUT_DIR
            ret += ' --barcode_type=' + self.barcode_type
            ret += ' --min_seq_length=' + str(self.min_seq_length)
            ret += ' --max_ambig=' + str(self.max_ambiguos)
            ret += ' --max_homopolymer=' + str(self.max_homopolymer)
            ret += ' --max_primer_mismatch=' + str(self.max_primer_mismatch)
            ret += ' --max_barcode_errors=' + str(self.max_barcode_errors)
            ret += ' --disable_bc_correction'
            ret += ' --qual_score_window=' + str(self.quality_score_window)
            ret += ' --max_seq_length=' + str(self.max_seq_length)
            ret += ' --min_qual_score=' + str(self.min_qual_score)
            ret += ' --map=' + file_exists(self.map_file)

        if self.pipe_name == 'FASTQ_SINGLE-END' and not self.is_demultiplex:
            ret += ' --fasta=' + re.sub(r"\.fastq", ".fna",
                                        file_exists(self.fastq_file), flags=re.IGNORECASE)
            ret += ' --qual=' + re.sub(r"\.fastq", ".qual",
                                       file_exists(self.fastq_file), flags=re.IGNORECASE)
        elif self.pipe_name == 'FASTA_QUAL_FILES':
            ret += ' --fasta=' + file_exists(self.fasta_file)
            ret += ' --qual=' + file_exists(self.qual_file)
        elif self.pipe_name == 'RAW_SFF_FILE':
            ret += ' --fasta=' + self.fasta_file
            ret += ' --qual=' + self.qual_file
        if ret is not None:
            self.cmds = [ret]
        return self

    def get_split_lib_out(self):
        return cfg.SPLIT_LIB_OUT_DIR + '/seqs.fna'

    def gen_denoise_wrapper_cmd(self):
        if self.pipe_name == 'RAW_SFF_FILE':
            self.cmds = ['denoise_wrapper.py '\
                          + ' --num_cpus=' + str(multiprocessing.cpu_count())\
                          + ' --output_dir=' + cfg.DENOISE_OUT_DIR\
                          + ' --map_fname=' + self.map_file \
                          + ' --input_file=' + cfg.PROCESS_SFF_OUT_DIR + '/'
                         +re.sub(r"\.sff", ".txt",
                                 self.raw_file_full, flags=re.IGNORECASE)\
                          + ' --fasta_file=' + cfg.SPLIT_LIB_OUT_DIR + '/seqs.fna'\
                          + ' --force_overwrite']
        return self

    def gen_inflate_denoiser_output_cmd(self):
        if self.pipe_name == 'RAW_SFF_FILE':
            self.cmds = ['inflate_denoiser_output.py '\
                          + ' --centroid_fps=' + cfg.DENOISE_OUT_DIR + '/centroids.fasta '\
                          + ' --singleton_fps=' + cfg.DENOISE_OUT_DIR + '/singletons.fasta '\
                          + ' --fasta_fps=' + cfg.SPLIT_LIB_OUT_DIR + '/seqs.fna '\
                          + ' --denoiser_map_fps=' + cfg.DENOISE_OUT_DIR + '/denoiser_mapping.txt '\
                          + ' --output_fasta_fp=final.fasta']
        return self

    def gen_split_lib_fastq_cmd(self):
        #
        # IF SINGLE-END and if new IS_DEMUXED checkbox IS clicked,
        # do this command(in lieu split_lib.py) See ian's example
        # eg:
        # split_libraries_fastq.py
        # --output_dir=split_lib_out
        # --barcode_type=not-barcoded
        # --mapping_fps=BS_mapping_small.txt
        # --sequence_read_fps=HG15X0002_S2_L001_R1_001.fastq,HG15X0005_S5_L001_R1_001.fastq,HG15X0008_S8_L001_R1_001.fastq,HG15X0010_S10_L001_R1_001.fastq
        # --sample_ids=HG15X0002,HG15X0005,HG15X0008,HG15X0010

        # Sample_SE_mplex = namedtuple('Sample_SE_mplex',
        #                              'sample_id fwd_fq_file TreatmentGroup Description')

        if self.pipe_name == 'FASTQ_SINGLE-END' and self.is_demultiplex:
            inputs = list()
            sample_ids = list()
            phred_offset = guess_fq_score_type(self.samples[0].fwd_fq_file)
            for sample in self.samples:
                inputs.append(sample.fwd_fq_file)
                sample_ids.append(sample.sample_id)
            s = 'split_libraries_fastq.py '\
                + ' --output_dir=' + cfg.SPLIT_LIB_OUT_DIR \
                + ' --barcode_type=not-barcoded'\
                + ' --mapping_fps=' + self.map_file \
                + ' --phred_offset=' + phred_offset.stdout.decode('utf-8') \
                + ' -i ' + ','.join(inputs) \
                + ' --sample_ids=' + ','.join(sample_ids)
            self.cmds = [s]
        if self.pipe_name == 'MISEQ_PAIR-END':
            inputs = list()
            maps = list()
            sample_ids = list()
            phred_offset = guess_fq_score_type(self.samples[0].fwd_fq_file)
            for sample in self.samples:
                inputs.append(sample.sample_id + '/fastqjoin.join.fastq')
                maps.append(sample.sample_id + '/map.txt')
                sample_ids.append(sample.sample_id)

#had to add pherd_offeset=33 for this dataset setting not sure if its an issue with the data type or all ITS...
#this does fix my dataset I'm using but this should be an automatic check.
#             + ' --phred_offset=33' \
            s = 'split_libraries_fastq.py '\
                + ' --output_dir=' + cfg.SPLIT_LIB_OUT_DIR \
                + ' --sequence_read_fps=' + ','.join(inputs) \
                + ' --phred_quality_threshold=' + str(self.q_param) \
                + ' --sequence_max_n=' + str(self.n_param) \
                + ' --mapping_fps=' + ','.join(maps) \
                + ' --phred_offset=' + phred_offset.stdout.decode('utf-8') \
                + ' --barcode_type=not-barcoded ' \
                + ' --sample_ids=' + ','.join(sample_ids) \
                + ' --max_bad_run_length=' + str(self.max_bad_run_length)
            self.cmds = [s]
        elif self.pipe_name == 'MISEQ_MULTIPLEX':
            split_lib_cmd = "split_libraries_fastq.py "\
                            + " --sequence_read_fps=" + cfg.JOINED_OUTS_OUT_DIR + '/fastqjoin.join.fastq'\
                            + " --output_dir=" + cfg.SPLIT_LIB_OUT_DIR \
                            + " --phred_quality_threshold=" + str(self.q_param) \
                            + " --mapping_fps=" + file_exists(self.map_file)\
                            + ' --max_bad_run_length=' + str(self.max_bad_run_length)

            if self.bc_file is not None:
                split_lib_cmd += ' --barcode_type='+ str(self.bc_len)\
                                 + ' --barcode_read_fps=' + file_exists(cfg.JOINED_OUTS_OUT_DIR + '/fastqjoin.join_barcodes.fastq')
                if not self.bc_is_fwd:
                    split_lib_cmd += ' --rev_comp_mapping_barcodes'
            else:
                split_lib_cmd += '--barcode_type not-barcoded ' \
                                 + ' --sequence_max_n=' + str(self.n_param)\
                                 + ' --sample_ids=' + cfg.JOINED_OUTS_OUT_DIR + '/fastqjoin.join_barcodes.fastq',
            self.cmds = [split_lib_cmd]
        return self

    def get_input_seqs(self):
        if self.pipe_name == 'RAW_SFF_FILE':
            return file_exists('final.fasta')
        else:
            return file_exists(cfg.SPLIT_LIB_OUT_DIR + '/seqs.fna')

    def gen_closed_reference_otus_cmd(self):
        if self.analysis_type == 'CLOSED_REFERENCE':
            line = "\npick_otus:otu_picking_method sortmerna\n"
            with open(self.otus_params_file, 'a') as params:
                params.write(line)
                params.close()
            self.cmds = ["pick_closed_reference_otus.py "\
                         + " -i " + self.get_input_seqs() \
                         + " --output_dir=" + cfg.PICK_OTUS_OUT_DIR \
                         + ' --reference_fp=' + file_exists(self.ref_fasta_file)\
                         + ' --taxonomy_fp=' + file_exists(self.ref_taxonomy_file)\
                         + ' --parameter_fp=' + file_exists(self.otus_params_file)\
                         + ' --force']
        return self

    def gen_pick_de_novo_otus_cmd(self):
        if self.analysis_type == 'DE_NOVO':
            line = "\npick_otus:otu_picking_method usearch61_ref\npick_otus:enable_rev_strand_match True\n"
            with open(self.otus_params_file, 'a') as params:
                params.write(line)
                params.close()
            self.cmds = ["pick_de_novo_otus.py " \
                         + " --input_fp=" + self.get_input_seqs() \
                         + " --output_dir=" + cfg.PICK_OTUS_OUT_DIR \
                         + " --force " \
                         + " --parameter_fp=" + file_exists(self.otus_params_file)\
                         + " --jobs_to_start="+ str(int(multiprocessing.cpu_count() / 4)) \
                         + " --parallel"]
        return self
#hard coding db for now
    def gen_open_reference_otus_ITS_cmd(self):
        if self.analysis_type == 'OPEN_REFERENCE_ITS':
            self.cmds = ['pick_open_reference_otus.py '\
                         + ' -i ' +  self.get_input_seqs() \
                         + ' -o ' + cfg.PICK_OTUS_OUT_DIR \
                         + ' -r ' + file_exists(self.ref_fasta_file) \
                         + ' -m sortmerna_sumaclust' \
                         + ' --parameter_fp=' + file_exists(self.otus_params_file)\
                         + ' --force' \
                         + ' --suppress_align_and_tree']
        return self

    def gen_open_reference_otus_cmd(self):
        if self.analysis_type == 'OPEN_REFERENCE':
            self.cmds = ['pick_open_reference_otus.py '\
                          + ' -i ' +  self.get_input_seqs() \
                          + ' -o ' + cfg.PICK_OTUS_OUT_DIR \
                          + ' -r ' + file_exists(self.ref_fasta_file)\
                          + ' --otu_picking_method sortmerna_sumaclust ' \
                          + ' --parameter_fp=' + file_exists(self.otus_params_file)\
                          + ' --force']
        return self

    def gen_jacknifed_beta_div(self, depth):
        if self.core_diversity_analyses \
           and not self.has_overide_core_div \
           and self.analysis_type != 'OPEN_REFERENCE_ITS':
            self.cmds = ['jackknifed_beta_diversity.py '\
                          + ' --otu_table_fp=' + self.lookup_biom_file() \
                          + ' --output_dir=' + cfg.JACKKNIFED_OUT_DIR \
                          + ' --seqs_per_sample=' + str(depth) \
                          + ' --mapping_fp=' + self.map_file \
                          + ' --tree_fp=' + self.get_tre_file() \
                          + ' --force ']
        return self


    def make_bootstrapped_tree_weighted_cmd(self):
        if self.core_diversity_analyses \
           and not self.has_overide_core_div \
           and self.analysis_type != 'OPEN_REFERENCE_ITS':
            d_name = cfg.JACKKNIFED_OUT_DIR + '/weighted_unifrac/upgma_cmp/'
            if os.path.isfile(d_name + 'master_tree.tre') \
               and os.path.isfile(d_name + 'jackknife_support.txt'):
                self.cmds = ['make_bootstrapped_tree.py '\
                              + ' --master_tree=' + d_name + 'master_tree.tre' \
                              + ' --support=' + d_name + 'jackknife_support.txt' \
                              + ' --output_file=' + d_name + 'jackknife_named_nodes_weighted.pdf']
        return self


    def make_bootstrapped_tree_unweighted_cmd(self):
        if self.core_diversity_analyses \
           and not self.has_overide_core_div \
           and self.analysis_type != 'OPEN_REFERENCE_ITS':
            d_name = cfg.JACKKNIFED_OUT_DIR + '/unweighted_unifrac/upgma_cmp/'
            if os.path.isfile(d_name + 'master_tree.tre') \
               and os.path.isfile(d_name + 'jackknife_support.txt'):
                self.cmds = ['make_bootstrapped_tree.py '\
                              + ' --master_tree=' + d_name + 'master_tree.tre' \
                              + ' --support=' + d_name + 'jackknife_support.txt' \
                              + ' --output_file=' + d_name + 'jackknife_named_nodes_unweighted.pdf']
        return self

    def lookup_good_counts_bad_samples(self, biom_smmry_fname):
        # DEFAULT CASE returns 20% of the Median(as deff'd in summry file)
        # EVERYTHING Below this is part of bad_samples

        # this function also might set the depth if the depth has been
        # specd as a fraction(using the biom files's Max_count * fraction)
        counts_region_started = False
        median_count = 0
        good_counts = list()
        bad_samples = list()
        min_count_threshold = 0
        min_count = 0

        with open(biom_smmry_fname, 'r') as f_in:
            for line in nonblank_lines(f_in):
                line = line.strip()
                if line.startswith('Min:'):
                    (_, min_count) = line.split(": ")
                if line.startswith('Median:'):
                    (_, median_count) = line.split(": ")
                elif line.startswith('Counts/sample detail:'):
                    # don't know what median count until now,
                    # now able to work out min_count_thresh
                    counts_region_started = True
                    if self.fraction: # this is a front end Form param
                        self.sample_depth = int(float(median_count) * float(self.fraction))
                        if int(float(min_count)) > self.sample_depth:
                            self.sample_depth = int(float(min_count) - 1)
                    # else they have typed in an int, and we are not working with fractions.
                elif counts_region_started:
                    (sample, count) = line.split(": ")
                    if int(float(count)) > self.sample_depth:
                        good_counts.append(int(float(count)))
                    else:
                        bad_samples.append(sample)
        return good_counts, bad_samples

    def rm_samples_map_file(self, bad_samples):
        mv(self.map_file, self.map_file + '.orig')
        f_out = open(self.map_file, 'w')
        # we don't want to end up having an empty map file so...
        num_lines = 0
        with open(self.map_file + '.orig') as f_in:
            for line in nonblank_lines(f_in):
                line_ok = True
                line_as_list = line.split("\t")
                for bad in bad_samples:
                    if bad == line_as_list[0]:
                        line_ok = False
                if line_ok or num_lines == 0:
                    num_lines += 1
                    print(line, file=f_out)
        f_out.close()
        if num_lines == 1:
            self.log.error(neph_errors.NO_OTUS)
            #self.log.error('You have no OTUS in your data, cannot proceed. Exiting.')
            self.do_exit_operations()
            exit(1)


    def calc_subsample_from_biom_file(self):
        # this should be in pqiime...
        biom_smmry_fname = self.lookup_biom_file() + '.summary.txt'
        self.ensure_output_exists(biom_smmry_fname)

        good_counts, bad_samples = self.lookup_good_counts_bad_samples(biom_smmry_fname)
        self.rm_samples_map_file(bad_samples)
        # need to reload the samples after we remake the map file!
        self.samples = self.load_map_file()

        if len(bad_samples) > 0:
            self.log.info("\n\nPLEASE NOTE!: Based on your cutoff we are ignoring samples:"\
                         + ','.join(bad_samples) + '\n\n')

        with open(cfg.PICK_OTUS_OUT_DIR + '/samples_being_ignored.txt', 'w') as f_out:
            print("\n".join(bad_samples), file=f_out)

        if len(good_counts) >= cfg.MIN_NUM_SAMPLES_FOR_CORE_DIV:
            rm('-r', '-f', cfg.TAXA_PLOTS_OUT_DIR) # we're going to gen this in core div
        else:
            self.do_run_core_div = False
        return self.sample_depth

    def gen_biom_summarize_table_cmd(self):
        self.cmds = ['biom summarize-table '\
                      + ' -i ' + self.lookup_biom_file() \
                      + ' -o ' + self.lookup_biom_file() + '.summary.txt ']
        return self

    def count_num_samples(self):
        count = 0
        with open(self.map_file) as f_in:
            for line in nonblank_lines(f_in):
                line = line.strip()
                if not line.startswith('#'):
                    count += 1
        return count

    def notify_if_core_div_overridden(self):
        if self.has_overide_core_div:
            self.log.info(neph_errors.NOT_ENOUGH_SAMPLES_CD)
            #self.log.info("\n!!!!! PLEASE NOTE !!!!!\n")
            #self.log.info("You have asked for core diversity analysis; however there are too few \
            #samples to allow this to occur. Core diversity analysis has NOT been run.")

    def rm_alpha_rare_dir_if_already_run_core_div(self):
        if self.do_run_core_div:
            rm('-r', '-f', cfg.ALPHA_RAREFACTION_OUT_DIR)

    def gen_alpha_rarefaction_cmd(self):
        if self.analysis_type != "OPEN_REFERENCE_ITS":
            if not self.do_run_core_div:
                self.cmds = ["alpha_rarefaction.py "\
                              + " --otu_table_fp=" + self.lookup_biom_file() \
                              + " --output_dir=" + cfg.ALPHA_RAREFACTION_OUT_DIR \
                              + " --tree_fp=" + self.get_tre_file() \
                              + " --mapping_fp=" + self.map_file\
                              + ' --parameter_fp=' + self.otus_params_file]
        return self

    def gen_compute_core_microbiome_cmd(self):
        if self.core_microbiome:
            uniq_treatment_groups = dict()
            for s in self.samples:
                tg = s.TreatmentGroup.split(',') # there's potentially lots of TGs, just want 1st col
                uniq_treatment_groups[tg[0]] = True
            for tg in uniq_treatment_groups.keys():
                self.cmds.append("compute_core_microbiome.py "\
                                 + " --input_fp=" + self.lookup_biom_file() \
                                 + " --output_dir=" + cfg.COMPUTE_CORE_MICROBIOME_OUT_DIR + '_' + tg
                                 + " --valid_states=TreatmentGroup:" + tg
                                 + " --mapping_fp="+ self.map_file)
        return self

    def gen_core_diversity_ITS_cmd(self, depth):
        if self.core_diversity_analyses and self.analysis_type == 'OPEN_REFERENCE_ITS':
            if depth == -1:
                self.log.error(neph_errors.NO_SAMPLES_AFTER_FILTER)
                #self.log.error('All samples assigned as bad according to cutoff supplied. Exiting.')
                self.do_exit_operations()
                exit(1)
            elif not self.do_run_core_div:
                self.log.info(neph_errors.NOT_ENOUGH_SAMPLES_CD)
                #self.log.info("Unable to run core diversity. There are too few samples with enough "\
                #              +"depth to be able to be able to do core diversity analysis.")
                self.has_overide_core_div = True
            else:
                self.cmds = ["core_diversity_analyses.py " \
                              + ' --output_dir=' + cfg.CORE_DIVERSITY_OUT_DIR \
                              + ' --input_biom_fp=' + self.lookup_biom_file() \
                              + ' --mapping_fp=' + self.map_file \
                              + ' --sampling_depth=' + str(depth) \
                              + ' --categories=' + get_C_opt_from_file(self.map_file)\
                              + ' --nonphylogenetic_diversity' \
                              + ' --parameter_fp=' + self.otus_params_file]
        return self

    def check_if_runing_core_diversity(self):
        if self.do_run_core_div is False:
            return self
        if len(get_C_opt_from_file(self.map_file)) == 0:
            self.do_run_core_div = False
        return self

    def gen_core_diversity_cmd(self, depth):
        if self.core_diversity_analyses and self.analysis_type != 'OPEN_REFERENCE_ITS':
            if depth == -1:
                self.log.error(neph_errors.NO_SAMPLES_AFTER_FILTER)
                #self.log.error('All samples assigned as bad according to cutoff supplied. Exiting.')
                self.do_exit_operations()
                exit(1)
            elif not self.do_run_core_div:
                self.log.info(neph_errors.NOT_ENOUGH_SAMPLES_CD)
                #self.log.info("Unable to run core diversity. There are too few samples with enough "\
                #              +"depth to be able to be able to do core diversity analysis.")
                self.has_overide_core_div = True
            else:
                if self.database == "Greengenes_97" or self.database == "Greengenes_99":
                    with open(self.otus_params_file, 'a') as params:
                        params.write('summarize_taxa:level 2,3,4,5,6,7\n')
                        params.close()
                self.cmds = ["core_diversity_analyses.py " \
                              + ' --output_dir=' + cfg.CORE_DIVERSITY_OUT_DIR \
                              + ' --input_biom_fp=' + self.lookup_biom_file() \
                              + ' --mapping_fp=' + self.map_file \
                              + ' --sampling_depth=' + str(depth) \
                              + ' --categories=' + get_C_opt_from_file(self.map_file)\
                              + ' --tree_fp=' + self.get_tre_file()\
                              + ' --parameter_fp=' + self.otus_params_file]
        return self

    def get_tre_file(self):
        if self.analysis_type == 'CLOSED_REFERENCE':
            return self.tree_file
        else:
            return cfg.PICK_OTUS_OUT_DIR + '/rep_set.tre'

    def lookup_biom_file(self):
        biom_file = ''
        if self.analysis_type == 'OPEN_REFERENCE':
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax_no_pynast_failures.biom'
        elif self.analysis_type == 'OPEN_REFERENCE_ITS':
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax.biom'
        else:
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table.biom'
        return biom_file

    def lookup_biom_file_table(self):
        biom_file = ''
        if self.analysis_type == 'OPEN_REFERENCE':
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax_no_pynast_failures.txt'
        elif self.analysis_type == 'OPEN_REFERENCE_ITS':
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax.txt'
        else:
            biom_file = cfg.PICK_OTUS_OUT_DIR + '/otu_table.txt'
        return biom_file

    def lookup_mothur_shared_file(self):
        if self.analysis_type == 'OPEN_REFERENCE':
            return cfg.PICK_OTUS_OUT_DIR + '/otu_table_mc2_w_tax_no_pynast_failures.shared'
        else:
            return cfg.PICK_OTUS_OUT_DIR + '/otu_table.shared'

    def lookup_rep_set_fa_file(self):
        if self.analysis_type == 'OPEN_REFERENCE' or\
           self.analysis_type == 'OPEN_REFERENCE_ITS':
            return cfg.PICK_OTUS_OUT_DIR + '/rep_set.fna'
        elif self.analysis_type == 'DE_NOVO':
            if self.pipe_name == 'RAW_SFF_FILE':
                return cfg.PICK_OTUS_OUT_DIR + '/rep_set/final_rep_set.fasta'
            else:
                return cfg.PICK_OTUS_OUT_DIR + '/rep_set/seqs_rep_set.fasta'
        else:
            self.log.error(neph_errors.NO_REF_ALIGN_FILE)
            self.log.error("Analysis type:" + self.analysis_type)
            # emit error
            self.do_exit_operations()
            exit(1)

    def gen_make_otu_heatmap_cmd(self):
        if self.count_num_samples() == 1:
            self.log.warn(neph_errors.NO_HEATMAP_FOR_SINGLE)
            #self.log.warn("Unable to run make_otu_heatmap on a single sample. Skipping.")
        elif self.interactive_otu_heatmap:
            mkdir('-p', cfg.HEATMAP_OUT_DIR)
            self.cmds = ['make_otu_heatmap.py '\
                          + ' --imagetype=svg'\
                          + ' --otu_table_fp=taxa_plots/otussorted_otu_table_L4.biom'\
                          + ' --output_fp=' + cfg.HEATMAP_OUT_DIR + '/heatmap.svg']
        return self

    def gen_plot_taxa_summary_cmd(self):
        if self.count_num_samples() == 1:
            self.cmds = ["plot_taxa_summary.py "\
                          + ' --chart_type=bar' \
                          + ' --counts_fname=' + ','.join(glob.glob(cfg.TAXA_PLOTS_OUT_DIR + "/*txt"))\
                          + ' --dir_path=' + cfg.TAXA_SUMMRY_PLOTS_OUT_DIR]
        else:
            self.cmds = ["plot_taxa_summary.py "\
                          + ' --counts_fname=' + ','.join(glob.glob(cfg.TAXA_PLOTS_OUT_DIR + "/*txt"))\
                          + ' --dir_path=' + cfg.TAXA_SUMMRY_PLOTS_OUT_DIR]
        return self

    def gen_sort_otu_table_cmd(self):
        self.cmds = ["sort_otu_table.py "\
                      +" --input_otu_table=" + self.lookup_biom_file()\
                      +" --output_fp=" + cfg.PICK_OTUS_OUT_DIR + "sorted_otu_table.biom"]
        return self

    def summarize_taxa(self):
        self.cmds = ["summarize_taxa.py "\
                      + " --otu_table_fp=" + cfg.PICK_OTUS_OUT_DIR + "sorted_otu_table.biom"\
                      + " --output_dir=" + cfg.TAXA_PLOTS_OUT_DIR]
        return self


    def make_process_sff_cmd(self):
        if self.pipe_name == 'RAW_SFF_FILE':
            if os.path.isfile(self.raw_file_full):
                self.cmds = ['process_sff.py '
                             + ' --make_flowgram'
                             + ' --input_dir=' + self.raw_file_full
                             + ' --output_dir=' + cfg.PROCESS_SFF_OUT_DIR]
                self.fasta_file = cfg.PROCESS_SFF_OUT_DIR + '/'\
                                  + re.sub(r"\.sff", ".fna", self.raw_file_full, flags=re.IGNORECASE)
                self.qual_file = cfg.PROCESS_SFF_OUT_DIR + '/'\
                                 + re.sub(r"\.sff", ".qual", self.raw_file_full, flags=re.IGNORECASE)
            else:
                self.log.error(neph_errors.NO_FILE_ERROR)
                self.log.error('{0} does not exist.'.format(self.raw_file_full))
                self.do_exit_operations()
        return self

    def make_mothur_sffinfo(self):
        if self.pipe_name == 'RAW_SFF_FILE':
            if not os.path.isfile(self.raw_file_full):
                self.log.error(neph_errors.NO_FILE_ERROR)
                self.log.error('{0} does not exist.'.format(self.raw_file_full))
                self.do_exit_operations()
            else:
                self.cmds = [mothurize('sffinfo',
                                       ['sff=' + self.raw_file_full,
                                        'trim=f',
                                        'flow=T',
                                        'sfftxt=T'])]
        return self

    def make_mothur_metastats_cmd(self):
        if hasattr(self, 'differential_otu_enrichment') and self.analysis_type != 'OPEN_REFERENCE_ITS':
            mothur_map_file = gen_ID_Treatment_map(self.map_file)
            self.cmds = [mothurize('metastats',
                                   ['shared=' + file_exists(
                                       self.lookup_mothur_shared_file()),
                                    'design=' + file_exists(mothur_map_file),
                                    'processors=' + str(multiprocessing.cpu_count())])]

        return self

    def make_mothur_lefse_cmd(self):
        if hasattr(self, 'differential_otu_enrichment') and self.analysis_type != 'OPEN_REFERENCE_ITS':
            mothur_map_file = gen_ID_Treatment_map(self.map_file)
            self.cmds = [mothurize('make.lefse',
                                   ['shared='
                                    +file_exists(self.lookup_mothur_shared_file()),
                                    'design=' + file_exists(mothur_map_file)])]
        return self

    def make_mothur_unique_seqs_cmd(self):
        """want to gen a count table file, need to gen the *.names file first
        then run make_mothur_count_seqs_cmd()
        """
        if self.chimera:
            self.cmds = [mothurize('unique.seqs',
                                   ['fasta=' + file_exists(self.lookup_rep_set_fa_file())])]
        return self

    def make_mothur_count_seqs_cmd(self):
        """this gets called after make_mothur_unique_seqs_cmd
        gens the count file"""
        if self.chimera:
            self.cmds = [mothurize('count.seqs',
                                   ['name='+cfg.PICK_OTUS_OUT_DIR+'/rep_set.names'])]
        return self

    def make_mothur_vsearch_chimera_cmd(self):
        """gens something like the below:
        mothur
        "#chimera.vsearch(
        seed=clear,
        fasta=otus/rep_set.unique.fna,
        count=otus/rep_set.count_table,
        dereplicate=t, processors=32)"
        """
        if self.chimera:
            self.cmds = [mothurize('chimera.vsearch',
                                   ['seed=clear',
                                    'fasta=otus/rep_set.unique.fna',
                                    'count=otus/rep_set.count_table',
                                    'dereplicate=t',
                                    'processors='+ str(multiprocessing.cpu_count())])]
        return self

    def lookup_accnos_file(self):
        fname = ''
        if self.analysis_type == 'DE_NOVO':
            if self.pipe_name == 'RAW_SFF_FILE':
                fname = cfg.PICK_OTUS_OUT_DIR + '/rep_set/final_rep_set.uchime.accnos'
            else:
                fname = cfg.PICK_OTUS_OUT_DIR + '/rep_set/seqs_rep_set.ref.uchime.accnos'
        elif self.analysis_type == 'OPEN_REFERENCE':
            fname = cfg.PICK_OTUS_OUT_DIR + '/rep_set.ref.uchime.accnos'
        if os.path.isfile(fname):
            return fname
        else:
            return False

        # otus/rep_set.ref.uchime.chimeras(IN CLOSED 1.9.1)
        # otus/rep_set.ref.uchime.accnos

    def gen_filter_fasta_cmd(self):
        # THIS TRIMS AWAY CHIMERIC STUFF USING THE ACCNOS file(generated @ make_mothur_chimera_cmd
        if self.chimera and self.lookup_accnos_file():
            self.cmds = ['filter_fasta.py '\
                          + ' --input_fasta_fp=' + self.lookup_rep_set_fa_file()\
                          + ' --output_fasta_fp=' + cfg.PICK_OTUS_OUT_DIR + '/rep_set_non_chimeric.fasta '\
                          + ' --seq_id_fp=' + self.lookup_accnos_file() \
                          + ' --negate']
        return self

    def replace_biom_with_clean_biom(self):
        if os.path.exists(cfg.PICK_OTUS_OUT_DIR + '/otu_table_clean.biom'):
            mv(self.lookup_biom_file(), self.lookup_biom_file() + '.orig')
            cp(cfg.PICK_OTUS_OUT_DIR + '/otu_table_clean.biom',
               self.lookup_biom_file())

    def gen_make_otu_table_cmd(self):
        """The taxonomy file can be called a number of things.
        There's two files: the taxonomy and the map file.
        There are three types of assignments of OTUs:
        OPEN, CLOSED,(and DE NOVO which is ~both)
        If the have OPEN the taxonomy file is named
        /uclust_assigned_taxonomy/rep_set_tax_assignments.txt
        if it's DE NOVO it's named:
        /uclust_assigned_taxonomy/seqs_rep_set_tax_assignments.txt
        if it's CLOSED it doesn;t need to be specified

        Example:
        make_otu_table.py
        --otu_map_fp open_otus/final_otu_map_mc2.txt
        --output_biom_fp open_otus/otu_table_clean.biom
        --exclude_otus_fp open_otus/rep_set.uchime.accnos
        --taxonomy open_otus/uclust_assigned_taxonomy/rep_set_tax_assignments.txt
        ^^^ this --taxonomy implies we're either running OPEN or DE NOVO

        The reason we're running this is to generate a cleaned up biom file.
        specifically otu_table_clean.biom
        this file is then treated as the main OTU file for the rest of the pipe.
        the original biom file is kept for gen_biom_summarize_table_cmd
        """
        # work out if the tax file is needed
        if self.analysis_type == 'OPEN_REFERENCE':
            tax_file = cfg.PICK_OTUS_OUT_DIR + \
                           '/uclust_assigned_taxonomy/rep_set_tax_assignments.txt'
        elif self.analysis_type == 'DE_NOVO':
            tax_file = cfg.PICK_OTUS_OUT_DIR +\
                       '/uclust_assigned_taxonomy/seqs_rep_set_tax_assignments.txt'
        else:
            tax_file = None

        if self.chimera and self.lookup_accnos_file() and os.path.isfile(self.lookup_biom_file()):
            ret = 'make_otu_table.py '\
                + ' --exclude_otus_fp=' + self.lookup_accnos_file() \
                + ' --output_biom_fp=' + cfg.PICK_OTUS_OUT_DIR + '/otu_table_clean.biom'\
                + ' --otu_map_fp=' + cfg.PICK_OTUS_OUT_DIR + '/final_otu_map_mc2.txt'
            if tax_file is not None:
                ret += ' --taxonomy ' + tax_file
            self.cmds = [ret]
        return self

    def gen_parallel_align_seqs_pynast_cmd(self):
        if self.chimera and os.path.isfile(cfg.PICK_OTUS_OUT_DIR + '/rep_set_non_chimeric.fasta'):
            self.cmds = ['parallel_align_seqs_pynast.py '\
                          + ' --input_fasta_fp=' + cfg.PICK_OTUS_OUT_DIR + '/rep_set_non_chimeric.fasta '\
                          + ' --output_dir=' + cfg.PYNAST_ALIGNED_SEQS_OUT_DIR \
                          + ' --jobs_to_start=' + str(multiprocessing.cpu_count()) \
                          + ' --poll_directly']
        return self

    def gen_align_seqs_pynast_cmd(self):
        if self.chimera and os.path.isfile(cfg.PICK_OTUS_OUT_DIR + '/rep_set_non_chimeric.fasta'):
            self.cmds = ['align_seqs.py '\
                          + ' --input_fasta_fp=' + cfg.PICK_OTUS_OUT_DIR + '/rep_set_non_chimeric.fasta '\
                          + ' --output_dir=' + cfg.PYNAST_ALIGNED_SEQS_OUT_DIR]
        return self

    def gen_filter_alignment_cmd(self):
        if self.chimera and os.path.isfile(cfg.PYNAST_ALIGNED_SEQS_OUT_DIR + '/rep_set_non_chimeric_aligned.fasta '):
            self.cmds = ['filter_alignment.py '\
                          + ' --output_dir='  + cfg.PYNAST_ALIGNED_SEQS_OUT_DIR \
                          + ' --input_fasta_file=' + cfg.PYNAST_ALIGNED_SEQS_OUT_DIR + '/rep_set_non_chimeric_aligned.fasta ']
        return self

    def gen_make_phylogeny_cmd(self):
        if self.chimera and os.path.isfile(cfg.PYNAST_ALIGNED_SEQS_OUT_DIR + '/rep_set_non_chimeric_aligned_pfiltered.fasta'):
            self.cmds = ['make_phylogeny.py '\
                          + '--input_fp=' + cfg.PYNAST_ALIGNED_SEQS_OUT_DIR + '/rep_set_non_chimeric_aligned_pfiltered.fasta'\
                          +' --result_fp=' + self.get_tre_file()]
        return self

    def make_mothur_shared_cmd(self):
        if self.analysis_type != 'OPEN_REFERENCE_ITS':
            self.cmds = [mothurize('make.shared',
                                   ['biom=' + file_exists(self.lookup_biom_file())])]
        return self

    def biom_convert_to_table(self):
        self.cmds = ['biom convert '\
                     + ' --table-type="OTU table" '\
                     + ' -i ' + file_exists(self.lookup_biom_file())\
                     + ' -o ' + self.lookup_biom_file_table()\
                     + ' --to-tsv --header-key taxonomy']
        return self

    def biom_convert_to_biom(self):
        self.cmds = ['biom convert '\
                     + ' --table-type="OTU table" '\
                     + ' -i ' + self.lookup_biom_file_table()\
                     + ' -o ' + file_exists(self.lookup_biom_file())\
                     + ' --to-json --process-obs-metadata taxonomy']
        return self

    def get_reference_DBs(self):
        fname = self.database + '.tgz'
        remote_fname = 'https://s3.amazonaws.com/nephele-ref-dbs/' + fname
        if not os.path.isfile(fname):
            wget(remote_fname)
            archive = tarfile.open(fname, 'r:gz')
            archive.extractall('.')
            rm(fname)
    def mv_biom_file_low_freq_otus(self):
        mv(self.lookup_biom_file(), cfg.PICK_OTUS_OUT_DIR + '/otu_table_with_low_abund.biom')
        mv(cfg.PICK_OTUS_OUT_DIR + '/otu_table_no_low_abundance.biom',
           self.lookup_biom_file())

    def gen_filter_otus_cmd(self):
        """Want to remove v low freq OTUs.
        then we want to change over and use this newly created OTU table from
        here on.
        gens something like:
        filter_otus_from_otu_table.py
        -i otu_table.biom
        -o otu_table_no_low_abundance.biom  < biom file to use from now on.
        --min_count_fraction 0.00005
        """
        self.cmds = ['filter_otus_from_otu_table.py '\
                     + ' --min_count_fraction 0.00005 '\
                     + ' -i ' + self.lookup_biom_file()\
                     + ' -o ' + cfg.PICK_OTUS_OUT_DIR + '/otu_table_no_low_abundance.biom']
        return self

    def modify_otu_params_file(self):
        """this modifies the otu_params file to create something like:

        summarize_taxa:absolute_abundance True
        alpha_diversity:metrics observed_species,chao1,PD_whole_tree,shannon
        make_distance_boxplots:num_permutations 0
        pick_otus:sortmerna_db SILVA_97/otus_16S
        pick_otus.py:pick_otus_reference_seqs_fp SILVA_97/otus_16S.fasta
        assign_taxonomy:id_to_taxonomy_fp SILVA_97/majority_taxonomy_7_levels.txt
        assign_taxonomy:reference_seqs_fp SILVA_97/otus_16S.fasta
        assign_taxonomy:assignment_method sortmerna
        assign_taxonomy:sortmerna_db SILVA_97/otus_16S
        """

        # if self.analysis_type == "OPEN_REFERENCE" or\
        #    self.analysis_type == "OPEN_REFERENCE_ITS" or\
        #    self.analysis_type == 'DE_NOVO':
        new_lines = [
            'pick_otus:sortmerna_db ' + cfg.SORTMERNA_DB_NAME[self.database],
            'pick_otus.py:pick_otus_reference_seqs_fp '\
            + cfg.HMP_REF_FASTA_FILE[self.database],
            'assign_taxonomy:id_to_taxonomy_fp '\
            + cfg.HMP_REF_TAXONOMY_FILE[self.database],
            'assign_taxonomy:reference_seqs_fp '\
            + cfg.HMP_REF_FASTA_FILE[self.database],
            'assign_taxonomy:assignment_method sortmerna ',
            'assign_taxonomy:sortmerna_db ' + cfg.SORTMERNA_DB_NAME[self.database]]
        with open(self.otus_params_file, 'a') as params:
            params.write("\n".join(new_lines))

    def gen_closed_reference_picrust(self):
        if self.picrust:
            if self.analysis_type == "OPEN_REFERENCE" or self.analysis_type == "DE_NOVO":
                line = "\npick_otus:otu_picking_method sortmerna\n"
                with open('picrust_params.txt', 'w') as params:
                    params.write(line)
                    params.close()
                self.cmds = ["pick_closed_reference_otus.py "\
                  + " -i " + self.get_input_seqs() \
                  + " --output_dir=otus_picrust" \
                  + ' --reference_fp=' + file_exists(self.ref_fasta_file)\
                  + ' --taxonomy_fp=' + file_exists(self.ref_taxonomy_file)\
                  + ' --parameter_fp=picrust_params.txt'\
                  + ' --force']
            # elif self.analysis_type == "DE_NOVO":
            #     self.cmds = ["pick_closed_reference_otus.py "\
            #                   + " -i " + self.get_input_seqs() \
            #                   + " --output_dir=otus_picrust" \
            #                   + ' --reference_fp=' + file_exists(self.ref_fasta_file)\
            #                   + ' --taxonomy_fp=' + file_exists(self.ref_taxonomy_file)\
            #                   + ' --parameter_fp=' + file_exists(self.otus_params_file)\
            #                   + ' --force']
            else:
                cp("-r", cfg.PICK_OTUS_OUT_DIR, "otus_picrust")
        return self

    def gen_norm_by_copy_num(self):
        if self.picrust:
            mkdir('-p', cfg.PICRUST_DIR)
            self.cmds = ['normalize_by_copy_number.py'\
                + ' -i otus_picrust/otu_table.biom'\
                + ' -o ' + cfg.PICRUST_DIR + '/normalized_otus.biom']
        return self

    def gen_predict_metagenomes(self):
        if self.picrust:
            self.cmds = ['predict_metagenomes.py '\
                + ' -i ' + cfg.PICRUST_DIR + '/normalized_otus.biom'\
                + ' -o ' + cfg.PICRUST_DIR + '/metagenome_predictions.biom']
        return self

    def gen_cat_by_function_lvl_2(self):
        if self.picrust:
            self.cmds = ['categorize_by_function.py '\
                + ' -i ' + cfg.PICRUST_DIR + '/metagenome_predictions.biom'\
                + ' -c "KEGG_Pathways" '\
                + ' -l 2' \
                + ' -o ' + cfg.PICRUST_DIR + '/predicted_metagenomes.L2.biom']
        return self

    def gen_cat_by_function_lvl_3(self):
        if self.picrust:
            self.cmds = ['categorize_by_function.py '\
                + ' -i ' + cfg.PICRUST_DIR + '/metagenome_predictions.biom'\
                + ' -c "KEGG_Pathways" '\
                + ' -l 3' \
                + ' -o ' + cfg.PICRUST_DIR + '/predicted_metagenomes.L3.biom']
        return self

    def gen_summarize_taxa_through_plots_lvl_2(self):
        if self.picrust:
            self.cmds = ['summarize_taxa_through_plots.py '\
                         + ' -i ' + cfg.PICRUST_DIR + '/predicted_metagenomes.L2.biom'\
                         + ' -o ' + cfg.PICRUST_DIR + '/picrust_at_lvl2'\
                         + ' -p ' + 'qiime_params_picrust2.txt']
        return self

    def gen_summarize_taxa_through_plots_lvl_3(self):
        if self.picrust:
            self.cmds = ['summarize_taxa_through_plots.py '\
                         + ' -i ' + cfg.PICRUST_DIR + '/predicted_metagenomes.L3.biom'\
                         + ' -o ' + cfg.PICRUST_DIR + '/picrust_at_lvl3'\
                         + ' -p ' + 'qiime_params_picrust3.txt']
        return self

    def __str__(self):
        return ''

    def __repr__(self):
        s = ''
        for var in vars(self):
            s += var + ' : ' + str(getattr(self, var)) + "\n"
            return s

def nonblank_lines(f):
    for l in f:
        line = l.rstrip()
        if line:
            yield line

def get_bc_len_from_map_file(fname):
    with open(file_exists(fname), 'r') as f_in:
        for line in nonblank_lines(f_in):
            line = line.strip()
            if not line.startswith('#'):
                if "\t" not in line:
                    raise IOError("Your mapping file looks wrong, line contains no tabs: " + line)
                else:
                    l = line.split("\t")
                    if len(l) < 2:
                        raise IOError("Your mapping file looks wrong, too few cols: " + line)
                    else:
                        return len(l[1])

def gen_ID_Treatment_map(fname):
    # name of file output:
    fname_out = fname + '.ID_Treatment'
    # if the file already exists, just return it
    if os.path.isfile(fname_out):
        return fname_out
    log = logging.getLogger('Base')
    samples = list()
    Sample = namedtuple('Sample', 'SampleID TreatmentGroup')
    with open(file_exists(fname), 'r') as f_in:
        location_of_treatment_col = 6 # defaulting to 6
        for line in nonblank_lines(f_in):
            line = line.strip()
            l = line.split("\t")
            if line.startswith('#'):
                if 'TreatmentGroup' not in l:
                    log.error(neph_errors.NO_TREATMENT_GROUP)
                    #log.info("There's no TreatmentGroup in the Headline of the Mapping file!")
                    #do_exit_operations()
                else:
                    location_of_treatment_col = l.index('TreatmentGroup')
            else:
                samples.append(Sample(SampleID=l[0],
                                      TreatmentGroup=l[location_of_treatment_col]))
    with open(fname_out, 'w') as f_out:
        print("\t".join(['#SampleID', 'TreatmentGroup']), file=f_out)
        for sample in samples:
            print("\t".join([sample.SampleID, sample.TreatmentGroup]), file=f_out)

    return fname_out

def join_paired_endify(fwd_fq_file, rev_fq_file, out_dir, perc_max_diff, min_overlap):
    # + " -p 25 " \
    # + " -j 10 " \
    command = "join_paired_ends.py "\
              + " --output_dir=" + out_dir \
              + " --forward_reads_fp=" + file_exists(fwd_fq_file)\
              + " --reverse_reads_fp=" + file_exists(rev_fq_file)\
              + " --perc_max_diff=" + perc_max_diff \
              + " --min_overlap=" + min_overlap

    return command

def guarantee_file_exists(fname):
    if not os.path.isfile(fname):
        call(['touch', fname])
    return fname


    # def ensure_user_input_depth_lt_mean_depth(self, depth):
    #     mean = None
    #     if os.path.isfile(self.lookup_biom_file() +'.summary.txt'):
    #         with open(self.lookup_biom_file() +'.summary.txt') as f:
    #             for line in nonblank_lines(f):
    #                 if line.startswith(' Mean: '):
    #                     line = line.strip()
    #                    (_, mean) = line.split(': ')
    #     else:
    #         logging.error('No biom file was generated. Cannot proceed.')
    #         # emit error
    #         self.do_exit_operations()
    #     if mean is None:
    #         logging.error('No mean value was found, problem with the biom file'\
    #                       + self.lookup_biom_file() +'.summary.txt')
    #         # emit error
    #         self.do_exit_operations()
    #     elif int(depth) > int(float(mean)):
    #         logging.error('The Fraction of Maximum Sample Size(' + str(depth)\
    #                       + ') entered is greater than the mean number ' + str(mean)\
    #                       + ' of reads per sample. Please adjust this value and resubmit.')
    #         # emit error
    #         self.do_exit_operations()
    #     else:
    #         logging.info('Mean depth was calculated as:' + str(mean) + '. This value is greater than depth entered ' + str(depth) + ', can proceed.')
