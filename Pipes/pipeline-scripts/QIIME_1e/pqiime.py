#!/usr/bin/env python
import logging
import sys
import cfg

from neph_pipes_utils import Config, gen_ID_Treatment_map, setup_logger
from common_utils import load_config_to_dict

configs = load_config_to_dict( sys.argv[1] )
log = setup_logger( configs['LOG_FILE'] )

conf = Config( configs )
conf.update_otus_params_file_for_ITS()
conf.make_mothur_sffinfo().exec_cmnd_and_log()
conf.make_process_sff_cmd().exec_cmnd_and_log()

conf.gen_join_paired_end_cmd().exec_cmnd_and_log()

conf.ensure_output_exists( conf.get_join_paired_end_outputs() )

conf.gen_per_sample_single_map_file()
conf.gen_convert_fastaqual_fastq_cmd().exec_cmnd_and_log()
conf.gen_validate_mapping_cmd().exec_cmnd_and_log() 
conf.gen_split_lib_cmd().exec_cmnd_and_log()
conf.gen_split_lib_fastq_cmd().exec_cmnd_and_log()

conf.ensure_output_exists( conf.get_split_lib_out() )

conf.gen_denoise_wrapper_cmd().exec_cmnd_and_log()
conf.gen_inflate_denoiser_output_cmd().exec_cmnd_and_log()
conf.gen_open_reference_otus_cmd().exec_cmnd_and_log()
conf.gen_open_reference_otus_ITS_cmd().exec_cmnd_and_log()
conf.gen_pick_de_novo_otus_cmd().exec_cmnd_and_log()
conf.gen_closed_reference_otus_cmd().exec_cmnd_and_log()

# CHIMERA STUFF STARTS HERE...
conf.make_mothur_chimera_cmd().exec_cmnd_and_log()
conf.gen_filter_fasta_cmd().exec_cmnd_and_log()
conf.gen_make_otu_table_cmd().exec_cmnd_and_log()
conf.gen_parallel_align_seqs_pynast_cmd().exec_cmnd_and_log()
conf.gen_filter_alignment_cmd().exec_cmnd_and_log()
conf.gen_make_phylogeny_cmd().exec_cmnd_and_log()
conf.write_chimera_count_to_file()
# ... AND ENDS HERE.

conf.gen_biom_summarize_table_cmd().exec_cmnd_and_log()
conf.gen_compare_to_HMP_cmd().exec_cmnd_and_log()
conf.ensure_output_exists( conf.lookup_biom_file() )
depth = conf.calc_subsample_from_biom_file()
conf.gen_filter_samples_from_otu_table_cmd( depth ).exec_cmnd_and_log()
conf.mv_biom_file().exec_cmnd_and_log()
conf.gen_sort_otu_table_cmd().exec_cmnd_and_log()
conf.summarize_taxa().exec_cmnd_and_log()
conf.gen_plot_taxa_summary_cmd().exec_cmnd_and_log()
conf.gen_make_otu_heatmap_cmd().exec_cmnd_and_log()

# conf.ensure_user_input_depth_lt_mean_depth( depth )

conf.gen_alpha_rarefaction_cmd().exec_cmnd_and_log() # only if too few sampl.exec_cmnd_and_log()
conf.gen_core_diversity_cmd( depth ).exec_cmnd_and_log()
#switched this over to the ITS version
conf.gen_core_diversity_ITS_cmd( depth ).exec_cmnd_and_log()
conf.rm_alpha_rare_dir_if_already_run_core_div()
conf.gen_jacknifed_beta_div( depth ).exec_cmnd_and_log()
conf.make_bootstrapped_tree_unweighted_cmd().exec_cmnd_and_log()
conf.make_bootstrapped_tree_weighted_cmd().exec_cmnd_and_log()

# exec_cmnd_and_log( conf.gen_otu_heatmap_cmd() ) < this is getting ditched in Qiime 2.0 anyway

conf.make_mothur_shared_cmd().exec_cmnd_and_log()
conf.make_mothur_metastats_cmd().exec_cmnd_and_log()

conf.make_mothur_lefse_cmd().exec_cmnd_and_log()
conf.gen_compute_core_microbiome_cmd().exec_cmnd_and_log()

conf.notify_if_core_div_overridden()
conf.do_exit_operations()

exit(0)
