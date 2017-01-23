#!/usr/bin/env python

import os, logging

syscall = lambda cmd: (os.popen(cmd).read()).rstrip("\n")

def load_config_to_dict( file_name, debug=False ):
    if file_name is False:
        return False
    d = dict()
    if debug:
        d['DEBUG'] = 'YES'
    else:
        d['DEBUG'] = 'NO'        
    with open ( file_exists (file_name) ) as f:
        for line in f:
            if not line.strip():     # ignore blank lines 
                continue
            line = line.rstrip()
            if line.startswith('#'): # ignore comments
                continue
            [k,v]=line.split(',')
            if (k == '' or v == '') and debug:
                print >> sys.stderr, ("There's a missing key / val in "+file_name)
                print >> sys.stderr, ("Key :"+k)
                print >> sys.stderr, ("Val :"+v)
            d[k]=v
    return d

def file_exists( fname ):
    log = logging.getLogger('Base') 
    if not os.path.isfile( fname ):
        log.error("File does not exist. I cannot proceed here." + fname)
        raise IOError ( "No such file: "  + fname)
        return False
    return fname
