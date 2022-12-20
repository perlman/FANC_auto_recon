#!/usr/bin/env python3

import collections
from concurrent import futures

import numpy as np
import pandas as pd
import requests
import tqdm
import cloudvolume

from . import auth

default_svid_lookup_url = 'https://services.itanna.io/app/transform-service/query/dataset/fanc_v4/s/2/values_array_string_response/'


def segIDs_from_pts_service(pts,
                            return_roots=True,
                            timestamp=None,
                            service_url=default_svid_lookup_url):
    """
    Return the rootIDs (if return_roots=True) or supervoxelIDs (if
    return_roots=False) corresponding to a given set of points.

    --- Arguments ---
    pts: Nx3 numpy array or pandas Series
      Points to query, in xyz order and in mip0 coordinates.
    return_roots: bool (default True)
      If true, will look up rootIDs from supervoxelIDs. Otherwise, supervoxel
      ids will be returned.
    timestamp: None or datetime
      Only relevant if return_roots=True.
      If None, look up the current rootID corresponding to the point location.
      Otherwise, look up the rootID for the point location at the given time in
      the past.

    --- Returns ---
    If return_roots=True, a numpy array of rootIDs as uint64
    If return_roots=False, a list of supervoxelIDs as int
    """

    # Reshape from list entries if dataframe column (Series) is passed
    if pts.shape != (3,):
        if len(pts.shape) == 1:
            pts = np.concatenate(pts).reshape(-1, 3)

    pts = np.array(pts, dtype=np.uint32)
    ndims = len(pts.shape)
    if ndims == 1:
        pts = pts.reshape([-1, 3])
    r = requests.post(service_url, json={
        'x': list(pts[:, 0].astype(str)),
        'y': list(pts[:, 1].astype(str)),
        'z': list(pts[:, 2].astype(str))
    })
    try:
        r = r.json()['values'][0]
        sv_ids = [int(i) for i in r]

        if return_roots:
            return auth.get_cloudvolume().get_roots(sv_ids, timestamp=timestamp)
        else:
            return sv_ids
    except:
        return None



# The code below implements a slower version of segIDs_from_pts_service that
# you should never need to run as long as the service is operational. If the
# service goes down, try using segIDs_from_pts_cv instead
class GSPointLoader(object):
    """Build up a list of points, then load them batched by chunk.
    This code is based on an implementation by
    `Peter Li<https://gist.github.com/chinasaur/5429ef3e0a60aa7a1c38801b0cbfe9bb>_.
    """

    def __init__(self, cloud_volume):
        """Initialize with zero points.
        See add_points to queue some.
        Parameters
        ----------
        cloud_volume :  cloudvolume.CloudVolume (SET AGGLOMERATE = FALSE for the cloudvolume object.)
        """

        CVtype = cloudvolume.frontends.precomputed.CloudVolumePrecomputed
        if not isinstance(cloud_volume, CVtype):
            raise TypeError('Expected CloudVolume, got "{}"'.format(type(cloud_volume)))

        self._volume = cloud_volume
        self._image_res = np.array([4.3, 4.3, 45])
        self._chunk_map = collections.defaultdict(set)
        self._points = None

    def add_points(self, points):
        """Add more points to be loaded.
        Parameters
        ----------
        points:     iterable of XYZ iterables
                    E.g. Nx3 ndarray.  Assumed to be in absolute units relative
                    to volume.scale['resolution'].
        """
        pts_array = np.zeros([len(points), 3])
        for i in range(len(pts_array)):
            pts_array[i, :] = points[i]

        points = pts_array

        if isinstance(self._points, type(None)):
            self._points = points
        else:
            self._points = np.concatenate(self._points, points)

        resolution = np.array(self._volume.scale['resolution']) / self._image_res
        chunk_size = np.array(self._volume.scale['chunk_sizes'])
        chunk_starts = (points // resolution).astype(int) // chunk_size * chunk_size
        for point, chunk_start in zip(points, chunk_starts):
            self._chunk_map[tuple(chunk_start)].add(tuple(point))

    def _load_chunk(self, chunk_start, chunk_end):
        # (No validation that this is a valid chunk_start.)
        return self._volume[chunk_start[0]:chunk_end[0],
               chunk_start[1]:chunk_end[1],
               chunk_start[2]:chunk_end[2]]

    def _load_points(self, chunk_map_key):
        chunk_start = np.array(chunk_map_key)
        points = np.array(list(self._chunk_map[chunk_map_key]))

        resolution = np.array(self._volume.scale['resolution']) / self._image_res
        indices = (points // resolution).astype(int) - chunk_start

        # We don't really need to load the whole chunk here:
        # Instead, we subset the chunk to the part that contains our points
        # This should at the very least save memory
        mn, mx = indices.min(axis=0), indices.max(axis=0)

        chunk_end = chunk_start + mx + 1
        chunk_start += mn
        indices -= mn

        chunk = self._load_chunk(chunk_start, chunk_end)
        return points, chunk[indices[:, 0], indices[:, 1], indices[:, 2]]

    def load_all(self, max_workers=4, return_sorted=True, progress=True):
        """Load all points in current list, batching by storage chunk.
        Parameters
        ----------
        max_workers :   int, optional
                        The max number of workers for parallel chunk requests.
        return_sorted : bool, optional
                        If True, will order the returned data to match the order
                        of the points as they were added.
        progress :      bool, optional
                        Whether to show progress bar.
        Returns
        -------
        points :        np.ndarray
        data :          np.ndarray
                        Parallel Numpy arrays of the requested points from all
                        cumulative calls to add_points, and the corresponding
                        data loaded from volume.
        """
        progress_state = self._volume.progress
        self._volume.progress = False
        pbar = tqdm.tqdm(total=len(self._chunk_map),
                         desc='Segmentation IDs',
                         disable=not progress)
        with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            point_futures = [ex.submit(self._load_points, k) for k in self._chunk_map]
            for f in futures.as_completed(point_futures):
                pbar.update(1)
        self._volume.progress = progress_state
        pbar.close()

        results = [f.result() for f in point_futures]

        if return_sorted:
            points_dict = dict(zip([tuple(p) for result in results for p in result[0]],
                                   [i for result in results for i in result[1]]))

            data = np.array([points_dict[tuple(p)] for p in self._points])
            points = self._points
        else:
            points = np.concatenate([result[0] for result in results])
            data = np.concatenate([result[1] for result in results])

        return points, data


def segIDs_from_pts_cv(pts,
                       n=100000,
                       max_tries=3,
                       return_roots=True,
                       max_workers=4,
                       progress=True,
                       timestamp=None):
    """
    Query cloudvolume object for root or supervoxel IDs.

    This method is slower than segIDs_from_pts_service, but does not depend on
    the supervoxel ID lookup service created by Eric Perlman and hosted on
    services.itanna.io. As such, this function might be useful if that service
    is not available for some reason.

    This function may not actually work as-is (it threw errors when tested in
    December 2022) but presumably it's close to working, because it did work in
    the past, so we can try to revive it if the need arises.

    --- Arguments ---
    pts: Nx3 numpy array or pandas Series
      Points to query, in xyz order and in mip0 coordinates.
    n: int (default 100,000)
      number of coordinates to query in a single batch. Default is 100000,
      which seems to prevent server errors.
    max_tries: int (default 3)
      number of attempts per batch. Usually if it fails 3 times, something is
      wrong and more attempts won't work.
    return_roots: bool (detault True)
      If true, will look up root ids from supervoxel ids. Otherwise, supervoxel
      ids will be returned.

    --- Returns ---
    root IDs or supervoxel IDs for queried coordinates as int64
    """

    cv = auth.get_cloudvolume()
    if hasattr(cv, 'agglomerate'):
        cv.agglomerate = False

    # Reshape from list entries if dataframe column is passed
    if isinstance(pts, pd.Series):
        pts = pts.reset_index(drop=True)
        pts = np.concatenate(pts).reshape(-1, 3)

    sv_ids = []
    failed = []
    bins = np.array_split(np.arange(0, len(pts)), np.ceil(len(pts) / 10000))

    for i in bins:
        pt_loader = GSPointLoader(cv)
        pt_loader.add_points(pts[i])
        try:
            chunk_ids = pt_loader.load_all(max_workers=max_workers, progress=progress)[1].reshape(len(pts[i]), )
            sv_ids.append(chunk_ids)
        except:
            print('Failed, retrying')
            fail_check = 1
            while fail_check < max_tries:
                try:
                    chunk_ids = pt_loader.load_all(max_workers=max_workers, progress=progress)[1].reshape(len(pts[i]), )
                    sv_ids.append(chunk_ids)
                    fail_check = max_tries + 1
                except:
                    print('Fail: {}'.format(fail_check))
                    fail_check += 1

            if fail_check == max_tries:
                failed.append(i)

    sv_id_full = np.concatenate(sv_ids)

    if return_roots:
        root_ids = cv.get_roots(sv_id_full, timestamp=timestamp)
        return root_ids
    else:
        return sv_id_full
