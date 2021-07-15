# sbatch??

# libraries 1
import numpy as np
import sys
import os
import pandas as pd
from tqdm import tqdm
import argparse

from cloudvolume import CloudVolume, view, Bbox
import fill_voids
from taskqueue import TaskQueue, queueable
from functools import partial

# libraries 2
sys.path.append(os.path.abspath("../segmentation"))
# to import rootID_lookup and authentication_utils like below
import rootID_lookup as IDlook
import authentication_utils as auth

parser = argparse.ArgumentParser(description='get segIDs of parent neurons from csv files') 
parser.add_argument('-c', '--choose', help='specify the numer of pixels randomly chosen to get segID of parent neuron. default is all surroundinx pixels', default=0, type=int)
parser.add_argument('-l', '--lease', help='lease_seconds for TaskQueue.poll. specify in seconds. default is 600sec', default=600, type=int)
args = parser.parse_args()

choose=args.choose
lease=args.lease

np.random.seed(123)
# queuepath = '/n/groups/htem/users/skuroda/nuclei_tasks'
queuepath = '../Output/nuclei_tasks'
# queuepath = '/n/groups/htem/users/skuroda/nuclei_output2'
outputpath = '../Output/'
size_xy = 160 # 160/(2**2)??
# 128x128x160 is small
# read csv
df = pd.read_csv('../Output/info_cellbody.csv', header=0)

# cv setting
seg = CloudVolume(auth.get_cv_path('FANC_production_segmentation')['url'], use_https=True, agglomerate=False, cache=True, progress=False)

# functions listed below


def vol_shift(input): # Although np.roll is fast, this is very slow since this overuse RAM
    # x plane
    x_p = np.roll(input, 1, axis=0)
    x_p[0,:,:] = 0
    x_n = np.roll(input, -1, axis=0)
    x_n[-1,:,:] = 0
    # y plane
    y_p = np.roll(input, 1, axis=1)
    y_p[:,0,:] = 0
    y_n = np.roll(input, -1, axis=1)
    y_n[:,-1,:] = 0
    # z plane
    z_p = np.roll(input, 1, axis=2)
    z_p[:,:,0] = 0
    z_n = np.roll(input, -1, axis=2)
    z_n[:,:,-1] = 0

    sum = x_p + x_n + y_p + y_n + z_p + z_n
    result = sum - input*6

    return result


# global variable is pt, segid, sizexy, choose



@queueable
def task_cellbody2neuron(i):
  cord_mip0 = df.iloc[i,0:3] #xyz coordinates
  cord_mip2 = cord_mip0.values # change coordination from mip0 to mip2
  cord_mip2[0]  = (cord_mip0.values[0] /(2**2))
  cord_mip2[1]  = (cord_mip0.values[1] /(2**2))
  cord_mip2 = cord_mip2.astype('int64')
  id = df.iloc[i,3] #segid

  if id == 0:
    A = np.append(cord_mip0.values, id).astype('int64')
    B = np.zeros(3, dtype = 'int64')
    output = np.append(A, B) #xyz, id, 0,0,0
  else:
    seg_nuc = seg.download_point(pt=cord_mip2, segids=id, size=[size_xy, size_xy, 160], coord_resolution=[17.2, 17.2, 45.0])
    # lowest resolution of seg is [17.2, 17.2, 45.0]
    vol_temp = seg_nuc[:,:,:]
    vol_temp[vol_temp>0] = 1 # change segID assigned to each cell body into 1
    vol = np.squeeze(vol_temp)

    filled = fill_voids.fill(vol, in_place=False) # fill the empty space with one 
    # ignore warning

    shifted = vol_shift(filled) # shift the volume
    shifted = shifted.astype('float32')
    shifted[shifted>0] = 1
    shifted[shifted<0] = 0

    location_one = np.argwhere(shifted == 1)
    len(location_one)

    if len(location_one):
      origin = seg_nuc.bounds.minpt # 3072,5248,1792
      parent_coordinates_mip2 = np.add(np.array(location_one), origin)
      parent_coordinates = parent_coordinates_mip2
      parent_coordinates[:,0]  = (parent_coordinates_mip2[:,0] * 2**2)
      parent_coordinates[:,1]  = (parent_coordinates_mip2[:,1] * 2**2)
      parent_coordinates = parent_coordinates.astype('int64')

      #random selection?
      if choose == 0:
        location_random = parent_coordinates
      else:
        index = np.random.choice(parent_coordinates.shape[0], size=choose, replace=False)
        location_random = parent_coordinates[index]

      # Lets get IDs using cell_body_coordinates
      parent_IDs = IDlook.segIDs_from_pts_cv(pts=location_random, cv=seg) #mip0

      # save
      uniqueID, count = np.unique(parent_IDs, return_counts=True)
      unsorted_max_indices = np.argpartition(-count, 4)[:4]
      topIDs = uniqueID[unsorted_max_indices] # gives me top5 IDs
      topIDs2 = topIDs[~(topIDs == id)] # I hope this keeps order
      topIDs3 = topIDs2[~(topIDs2 == 0)] # no zero
      A = np.append(cord_mip0.values, id).astype('int64')
      B = topIDs3.astype('int64')[0:3]
      output = np.append(A, B) #top3
      
    else:
      A = np.append(cord_mip0.values, id).astype('int64')
      B = np.zeros(3, dtype = 'int64')
      output = np.append(A, B) #xyz, id, 0,0,0
      
    seg.cache.flush()

  output_df = pd.DataFrame(columns=["x", "y", "z", "segIDs", "Parent1", "Parent2", "Parent3"])
  output_df.loc[0] = output
  name = str(i)
  output_df.to_csv(outputpath + 'cellbody_and_neuron_%s.csv' % name, index=False)


# task queue
# global variable is lease
 

def create_task_queue():
    tq = TaskQueue('fq://' + queuepath)
    tq.insert(( partial(task_cellbody2neuron, i) for i in range(len(df)) )) # NEW SCHOOL?
    # tq.execute()
    print('Done adding {} tasks to queue at {}'.format(len(df), queuepath))




def run_tasks_from_queue():
    tq = TaskQueue('fq://' + queuepath)
    print('Working on tasks from filequeue "{}"'.format(queuepath))
    tq.poll(
        verbose=True, # prints progress
        lease_seconds=int(lease),
        tally=True # makes tq.completed work, logs 1 byte per completed task
    )
    print('Done')


#execute
create_task_queue()
run_tasks_from_queue()
# finish?