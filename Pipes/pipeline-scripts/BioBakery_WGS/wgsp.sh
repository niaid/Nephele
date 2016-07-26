#!/bin/bash
source /home/ubuntu/anadama_env/bin/activate
anadama pipeline anadama_workflows.pipelines:WGSPipeline -f 'raw_seq_files: glob:*.fastq' -o 'decontaminate.threads: 32' -o 'metaphlan2.nproc: 32'  -A anadama_workflows.pipelines:VisualizationPipeline -f 'sample_metadata: map.txt'
