# Nephele's Pipelines

The pipeline-scripts directory contains all files and code that run the individual Nephele pipelines. The config and python files in this directory are for handling the AWS components of Nephele.

## Usage example
These pipelines are intended for processing on Amazon EC2 instances when files are submitted through Nephele's web interface. However, it is possible to bypass the web interface and interact with the pipelines directly. In order to do this, you will need access to Amazon Web Services and a working knowledge of how to interact with AWS components, either through the console or from the command line utilities.

To run a mothur MiSeq pipeline, do the following:

1. Launch an EC2 instance on AWS, based on the public AMI `ami-c1f1f2d7`. Ideally, your instance should have at least 100GB local or EBS-attached storage. For example, launch a c3.4xlarge instance with a 150GB EBS volume attached, following default AWS instructions for instance setup
2. Log on to the machine as 'root' (or else use the user name 'ubuntu', for example)
3. Copy the pipeline source code to the instance. You can either transfer directly from this repository, or download and then upload to the instance (e.g., using `scp Nephele-master.zip root@IP_ADDR:/var/www/vfs/`
4. Unzip the repository on the instance (`unzip /var/www/vfs/Nephele-master.zip`)
5. As in step 3, copy your sequence data archive file (named MiSeq.zip) and your mapping file (named map.txt) to the instance and place them in the following directory: /var/www/vfs/Nephele-master/Pipes/pipeline-scripts/MOTHUR_MiSeq. You can use a sample files MiSeq.zip and map.txt, which are accessible from https://s3.amazonaws.com/nephele-docs/Test-Files/Mothur-MiSeq/ [filename], where [filename] refers to MiSeq.zip and map.txt, respectively.
6. Run the pipeline using the following command from within the MOTHUR_MiSeq directory: `neph_mothur.py config_default.csv` (Note: You can make modifications to the config_default.csv files to change parameters, specify different input files, etc.)
7. You can track the output by tracking the log file: `tail -f logfile.txt`
8. Outputs will exist within the MOTHUR_MiSeq directory. You can find details on making sense of these outputs in the "Results Interpretation" section of [Nephele's User Guide](https://nephele.niaid.nih.gov/#guide)
