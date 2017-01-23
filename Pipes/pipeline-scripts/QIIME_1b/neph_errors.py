
#ERRORS
NO_CONFIG_FILE = 'NEPHELE ERROR: Could not find config file'
AVERAGE_LENGTH_TOO_LOW = 'NEPHELE ERROR: Average length is too low, unable to continue. Please adjust your parameters to allow for better overlap of PE reads or use the QIIME PE pipeline.'
SUMMARY_SEQS_ERROR = 'NEPHELE ERROR: The Output of summary.seqs seems to be wrong'
NO_SAMPLES_IN_MAPPING_FILE = 'NEPHELE ERROR: Unable to proceed, no samples in mapping file.'
NO_TREATMENT_GROUP = 'NEPHELE ERROR: No TreatmentGroup column found in:'
BAD_FILE_TYPE = 'NEPHELE ERROR: Bad file format or type. Please check this file for accuracy and resubmit your job:'
NO_FILE_ERROR = 'NEPHELE ERROR: Cannot find file. Please check files and resubmit job. Missing file:'
NO_DEPTH = 'NEPHELE ERROR: No depth value was found. Cannot compute depth for core diversity.'
BAD_JOINING = 'NEPHELE ERROR: Joining failed because too few reeds overlapped. Please adjust join parameters or re-evaluate data.'
TOO_FEW_READS_TRIMMING = 'NEPHELE ERROR: Too few reads to proceed. Please adjust trimming parameters and / or review data.'
NO_BIOM_FILE = 'NEPHELE ERROR: There is no biom summary file. Please check data and re-evaluate job parameters.'
NO_BARCODE_FILE = 'NEPHELE ERROR: There is no barcode file. Check file formats before re-running job.'
NO_OTUS = 'NEPHELE ERROR: There are no OTUs in your alignment file. Typically, this is due to poor quality data or poor read joining.'
NO_SAMPLES_AFTER_FILTER = 'NEPHELE ERROR: All samples removed due to cutoff value supplied. Re-evaluete data quality and job parameters.'
NO_REF_ALIGN_FILE = 'NEPHELE ERROR: Missing results of OTU picking. Check outs/log file and re-evaluate data.'
NO_HMP_DATABASE = 'NEPHELE ERROR: Missing HMP database for BIOM file retrieval. Please check your HMP settings.'

#WARNINGS
NOT_ENOUGH_SAMPLES_CD = 'NEPHELE WARNING: There are not enough samples, or not enough unique metadata categoires, to complete core diversity analysis.'
NO_HEATMAP_FOR_SINGLE = 'NEPHELE WARNING: Unable to run make_otu_heatmap on a single sample. Skipping.'
PICRUST_GG_WARN = 'NEPHELE WARNING: Using PICRUSt requires the reference database used is Greengenes 13_8_99.'