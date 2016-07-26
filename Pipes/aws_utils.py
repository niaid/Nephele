#!/usr/bin/python
#
# aws_utils.py
#

import json, time, os, getpass, socket, smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sh import mkdir, ls, cp, glob
import cfg
from common_utils import file_exists, syscall

def generate_start_test_file( files, remote_work_dir_name, run_script_name ):
    # this has to run on a remote machine, so I can't use python directly.
    # instead write out (Bash) instuctions to a file, chmod a+x the file, and exec.
    file_getter = ''
    for f in files:
        file_getter += 'if [[ ! -e ' + os.path.basename(f) + ' ]]; then \n'
        file_getter += 'wget --quiet '+ f + "\nfi\n"
    generate_start_file( remote_work_dir_name, run_script_name, file_getter )
    

def generate_start_file( remote_work_dir_name, run_script_name, prepend_this=None ):
    with open('start.sh', 'w') as f:
        print >>f, 'cd ' + remote_work_dir_name
        if prepend_this is not None:
            print >>f, prepend_this
        print >>f, 'unzip -o scripts_bundle.zip'
        # print >>f, 'count=`ls -1 *.tgz 2>/dev/null | wc -l`'
        # print >>f, 'if [ $count != 0 ]; then for f in *.tgz; do tar xzf $f; done fi'
        # print >>f, 'count=`ls -1 *.gz 2>/dev/null | wc -l`'
        # print >>f, 'if [ $count != 0 ]; then for f in *.gz; do gunzip $f; done fi'
        # print >>f, 'count=`ls -1 *.tar 2>/dev/null | wc -l`'
        # print >>f, 'if [ $count != 0 ]; then for f in *.tar; do tar xf $f; done fi'
        # print >>f, 'count=`ls -1 *.zip 2>/dev/null | wc -l`'
        # print >>f, 'if [ $count != 0 ]; then for f in *.zip; do unzip -oq $f; done fi'
        # print >>f, 'ln -s ../qiime_software/sh-1.11/sh.py .'
        print >>f, 'chmod a+x ' + run_script_name
        print >>f, '/bin/bash ./' + run_script_name
        print >>f, 'touch Pipeline_done.txt'

def swap_quote_for_underscore( s ):
    if isinstance(s, basestring) :
        s = s.replace("\"", "_")
        s = s.replace("\'", "_")
    return s
    
def get_aws_machine_as_json( instance_id ):
    # this is for looking up DNS / IPconf
    print 'looking up machine ' + instance_id
    return json.loads( syscall('aws ec2 describe-instances --instance-id '+instance_id) )

def get_aws_machine_status_as_json( instance_id ):
    # for status OK etc
    return json.loads( syscall('aws ec2 describe-instance-status --instance-id '+instance_id) )

def add_instance_type_to_cmnd(cmnd, instance_type):
    if instance_type is None:
        return cmnd
    return cmnd + ' --instance-type ' + instance_type

def gen_run_instances_cmd(ami_id, user):
    if not(user and isinstance(user, User) and user.key_name is not None):
        print 'Bad User at ' + user
        exit(1)
    return 'aws ec2 run-instances --image-id ' + ami_id \
        + ' --key-name ' + user.key_name

def gen_date_str():
    return time.strftime( "%H" ) + '_' +time.strftime( "%M" ) + '_' + time.strftime( "%S" )


def gen_login_str( uname, url ):
    return str(uname) + '@' + url # ami_LOGIN is defaulted to ubuntu

def print_config( config ):
    # not sure why this might be needed
    for k,v in config.items():
        config[k]=config[k].translate( None, "\'\"" )
        print k+','+v

        
class User:
    def __init__(self, key_name, pem_file_loc, uname=None ):
        self.key_name = key_name
        self.pem_file_loc = pem_file_loc
        if uname is None:
            self.uname = 'ubuntu'
        else:
            self.uname = uname
        
class AWS_machine:
    def __repr__(self):
        return ' '.join( [self.url, self.ami_id, self.instance_id] )

    @classmethod
    def start_new_machine(cls, ami_id, aws_type, user, deploy_dir, remote_work_dir):
        print "\n\nstarting new machine " + ami_id
        aws_machine_as_json = start_instance( ami_id, user, aws_type )
        return cls(aws_machine_as_json, user, deploy_dir, remote_work_dir)

    def __init__(self, aws_machine_as_json, user, deploy_dir, remote_work_dir):
        self.url = aws_machine_as_json['Reservations'][0]['Instances'][0]['PublicDnsName']
        self.ami_id = aws_machine_as_json['Reservations'][0]['Instances'][0]['ImageId']
        self.instance_id = aws_machine_as_json['Reservations'][0]['Instances'][0]['InstanceId']
        self.user = user
        self.tag_machine()
        self.remote_work_dir = remote_work_dir
        self.deploy_dir = deploy_dir
        if not self.deploy_dir.endswith('/'):
            self.deploy_dir +'/'
        
    def tag_machine( self ):
        tag = self.user.key_name + '_' + gen_date_str()
        syscall( 'aws ec2 create-tags --resources ' + self.instance_id + ' --tags Key=Name,Value=' +  tag)
    def terminate( self ):
        print 'RUNNING TERM ON ' + self.instance_id
        syscall( 'aws ec2 terminate-instances --instance-ids ' + self.instance_id)
        
    def do_test_on( self, user, pipe_dir, config, config_fname ):
        if not pipe_dir.endswith('/'):
            pipe_dir = pipe_dir + '/'

        # config might already be a json obj
        test_files = list()
        if isinstance(config['TEST_FILES'], basestring):
            test_files = config['TEST_FILES'].split(';')
        else:
            test_files = config['TEST_FILES']
            
        generate_start_test_file(test_files, self.remote_work_dir, cfg.RUN_SCRIPT )
        self.execute_remote_cmd( 'mkdir -p ' + self.remote_work_dir)
        self.scp_to_remote( './start.sh', self.remote_work_dir )
        self.scp_to_remote( self.deploy_dir + '/'+ pipe_dir + cfg.SCRIPTS_BUNDLE_ZIP_FILE_NAME, self.remote_work_dir )
        if config_fname.endswith('json'):
            self.scp_to_remote( config_fname, self.remote_work_dir + '/config.json')
        else:
            self.scp_to_remote( config_fname, self.remote_work_dir + '/config.csv')
        
        self.execute_remote_cmd( 'chmod a+x ' + self.remote_work_dir + '/start.sh ')
        self.execute_remote_cmd( 'nohup /bin/bash ' + self.remote_work_dir + '/start.sh &')
        while True:
            if self.pipeline_done( self.remote_work_dir + '/Pipeline_done.txt' ):
                break
            sleep(60)
            
    def cp_remote_work_dir_local(self, config):
        test_out_dir = 'Test_' + config['INPUT_TYPE'] + '_' + gen_date_str()
        mkdir(test_out_dir)
        self.scp_to_local( self.remote_work_dir + '/' + cfg.ALL_RESULTS_ZIP_FILE_NAME, test_out_dir )
        self.scp_to_local( self.remote_work_dir + '/' + config['LOG_FILE'], test_out_dir )

    def rm_remote_work_dir( self ):
        self.execute_remote_cmd( 'rm -rf ' + self.remote_work_dir )

    def execute_remote_cmd ( self, cmd ):
        remote_cmd = 'ssh -o "StrictHostKeyChecking no"' \
                     + ' -i ' + self.user.pem_file_loc \
                     + ' ' + gen_login_str( self.user.uname, self.url ) \
                     + ' ' + cmd

        # call( cmd, shell=True ) 
        # print (cmd)
        print remote_cmd
        
        return syscall(remote_cmd)
    
    def rsync_to_remote ( self, thing_to_copy, place_to_copy_to):
        cmd='rsync -avzLu -e "ssh -i ' + self.user.pem_file_loc + '" ' \
            + thing_to_copy +' '\
            + gen_login_str( self.user.uname, self.url ) \
            + ':~/' + place_to_copy_to
        call( cmd, shell=True ) 
        print (cmd)

    def scp_to_local ( self, remote_file_name, local_dir):
        cmd = 'scp -r -i ' + self.user.pem_file_loc + ' '\
              + gen_login_str( self.user.uname , self.url ) \
              + ':' + remote_file_name \
              + ' ' + local_dir
        syscall(cmd)
        print (cmd )
    
    def scp_to_remote ( self, thing_to_copy, place_to_copy_to ):
        cmd = 'scp -r -i ' + self.user.pem_file_loc + ' '\
              + thing_to_copy + ' '\
              + gen_login_str( self.user.uname , self.url ) \
              + ':' + place_to_copy_to
        syscall(cmd)
        print (cmd )
    def pipeline_done( self , done_file):
        return self.execute_remote_cmd('ls ' + done_file) == done_file
        
# def execute_remote_cmd_as_sudo ( config, cmd ):
#     # THIS IS NOT WORKING #
#     cmd_with_black_magic = '"echo '+ cmd + ' | base64 -d | sudo bash"'
#     remote_cmd = 'ssh -o "StrictHostKeyChecking no" -i ' + config['PEM_FILE'] + ' ' + gen_login_str(config['AMI_LOGIN'],config['URL'])+ ' ' + cmd_with_black_magic
#     print remote_cmd
#     syscall(remote_cmd)

def is_valid_config( config ):
    if config is False:
        return config
    if 'AMI_ID' in config.keys() and 'INPUT_TYPE' in config.keys() and 'TEST_FILES' in config.keys():
       # and 'LOG_FILE' in config.keys():
        return config
    else:
        print 'Ensure your config file contains AMI, INPUT_TYPE, and TEST_FILES entries.  \n{0}\n is '\
            'not a valid config.'.format(config)
        exit(1)

def start_instance( ami_id, user, instance_type, machine_type=None ):        
    if machine_type is None:
        machine_type = cfg.DEFAULT_AWS_TYPE

    cmd = add_instance_type_to_cmnd( gen_run_instances_cmd(ami_id, user), instance_type)
    json_obj = json.loads( syscall( cmd ) )
    instance_id = json_obj['Instances'][0]['InstanceId']
    print("EC2 starting! Starting to wait on status...")

    status_json = get_aws_machine_status_as_json ( instance_id )
    while True:
        if len(status_json['InstanceStatuses']) > 0:
            if status_json['InstanceStatuses'][0]['InstanceStatus']['Status'] == 'ok':
                break
            else:
                print ('Waiting on status to become OK...')
                time.sleep(10)
                status_json = get_aws_machine_status_as_json( instance_id )
        else:
            print ('Still trying to get status.')
            time.sleep(10)
            status_json = get_aws_machine_status_as_json( instance_id )
            
    return get_aws_machine_as_json(instance_id)

def exec_sys(cmd):
    #print >> sys.stderr, "Executing:",cmd
    if 0!=os.system(cmd):
        print >> sys.stderr, "ERROR when executing:",cmd
        sys.exit(777)

def totimestamp(dt, epoch=datetime(1970,1,1)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6 

def send_mail_new( rcpts, subject, body ):
    sender = getpass.getuser() + '@' + socket.gethostname()
    print sender
    msg = MIMEText( body )
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ','.join(rcpts)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender, rcpts, msg.as_string())
    s.quit()
        
def send_mail( f_from, f_to, f_subject, f_text):
    w=int(time.time())
    r=random.randint(0,9999)
    fn='/tmp/'+str(w)+str(r)+'.mail'
    #print fn
    fh = open( fn, 'w' )
    print >> fh,'From: '+f_from
    print >> fh,'Subject: '+f_subject
    print >> fh, "\n" + f_text
    fh.close()
    cmd='/usr/sbin/sendmail '+f_to+' <'+fn
    #print cmd
    w=syscall(cmd)
    if( '' != w):
        print w
    os.remove(fn)

   # another version
   #cmd="echo \""+f_text+"\" | /usr/sbin/sendmail "+f_to
   #cmd="echo \""+f_text+"\" | sendmail "+f_to
   #print cmd
   #w=syscall(cmd)
   #print w


def describe_instances(): #########################
    # this is only used by amzn_running_instances AFAIK
    # need to path aws because... dev server doesn't seem to know where it is :/
    w=syscall('/usr/local/bin/aws ec2 describe-instances')
    m=json.loads(w)

    now = datetime.utcnow()
    lhs,rhs=str(now).split('.')
    dt=datetime.strptime(lhs,'%Y-%m-%d %H:%M:%S')
    t_now=totimestamp(dt)

    all=''
    for i in m['Reservations']:
        if i['Instances'][0]['PublicDnsName'] == '':
            continue
        if i['Instances'][0]['PublicDnsName'] is not None:
            lhs, rhs = i['Instances'][0]['LaunchTime'].split('.')
            dt=datetime.strptime(lhs,'%Y-%m-%dT%H:%M:%S')
            t_launch=totimestamp(dt)
            t_run=int(t_now-t_launch)/3600

            if (i['Instances'][0]['InstanceType'].find('micro')<0) and (t_run>25):
                s = " ".join( [ i['Instances'][0]['PublicDnsName'], 
                                i['Instances'][0]['InstanceId'], 
                                i['Instances'][0]['ImageId'], 
                                #i['Instances'][0]['KeyName'], 
                                i['Instances'][0]['InstanceType'],
                                i['Instances'][0]['LaunchTime'],
                                i['Instances'][0]['State']['Name'],
                                i['Instances'][0]['Tags'][0]['Value'], 
                                'for', str(t_run), 'hours' ])
                all=all+s+"\r\n"
    return all
