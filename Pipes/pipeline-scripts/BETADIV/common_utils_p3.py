#!/usr/bin/python3
import os
import logging
import subprocess

def load_inputs_as_dict( config_fname ):
    if os.path.isfile( config_fname ):
        if config_fname.endswith( '.json' ):
            with open( config_fname ) as json_file:
                input_dict = json.load(json_file)
        elif config_fname.endswith( '.csv' ):
            input_dict = read_mm_csv(config_fname)
        else:
            print('Unable to handle file:{0}, must have .csv or .json ext.'.format(config_fname))
            exit(1)
        return input_dict

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
                    print("There's something wrong with the config file {0} on at:")
                    print("\t" + line)
                d[line_as_list[0]] = line_as_list[1]
    return d

def mothurize ( func_name, args ):
    return 'mothur "#' + func_name + '(' + ','.join(args) + ')"'

def redir_out( cmd, out_fname ):
    return cmd + " > " + out_fname

def setup_logger( log_name ):
    formatter = logging.Formatter(fmt='[ %(asctime)s - %(levelname)s ] %(message)s\n')
    fh = logging.FileHandler('logfile.txt')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    return logger

def exec_cmnd( cmds, log ):
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
    if ext == '.csv' or ext == '.txt':
        return fname
    elif ext == '.xlsx':
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
        unzip('-j', fname)
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
