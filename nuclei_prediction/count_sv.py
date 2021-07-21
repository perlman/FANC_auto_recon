import numpy as np
import pandas as pd
from cloudvolume import CloudVolume, view, Bbox
import argparse
from taskqueue import TaskQueue, queueable, LocalTaskQueue
from functools import partial
import sys
import os
import csv

sys.path.append(os.path.abspath("../segmentation"))
import authentication_utils as auth

def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError("{0} does not exist".format(f))
    return f

parser = argparse.ArgumentParser(description='get segIDs of cell bodies and save into csv files') 
parser.add_argument('-i', '--index', help='provide index to read', type=validate_file)
parser.add_argument('-p', '--parallel', help='number of cpu cores for parallel processing. default is 12', default=12, type=int)
args = parser.parse_args()

myinput=args.index
parallel_cpu=args.parallel

df = pd.read_csv('~/info_cellbody_20210721.csv', header=0)
segcv = CloudVolume(auth.get_cv_path('FANC_production_segmentation')['url'], use_https=True, agglomerate=False, cache=True, autocrop=True, bounded=False)

outputpath = '/n/groups/htem/users/skuroda/ncount'


@queueable
def task_get_sv(i):
    try:
        sv = segcv.get_leaves(root_id=df.iloc[i,3], mip=2, bbox=segcv.mip_volume_size(0))
        svl = len(sv)
        arr = np.append(i, svl)
        np.savetxt(outputpath + '/' + 'ncount_{}.csv'.format(str(i)), arr, delimiter=',', fmt='%d')
    except Exception as e:
        with open(outputpath + '/' + '{}.log'.format(str(i)), 'w') as logfile:
            print(e, file=logfile)



def run_local():
    tq = LocalTaskQueue(parallel=parallel_cpu)
    if myinput is not None:
        with open(myinput) as fd:      
            txtdf = np.loadtxt(fd, delimiter=',', dtype='int64')
            tq.insert( partial(task_get_sv, txtdf[i]) for i in range(len(txtdf)) )
    else:
        tq.insert(( partial(task_get_sv, i) for i in range(len(df))))

    tq.execute(progress=True)
    print('Done')