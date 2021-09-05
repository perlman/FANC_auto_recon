#!/usr/bin/env python3

# Originally published in https://www.lee.hms.harvard.edu/phelps-hildebrand-graham-et-al-2021
# and made available in that paper's repository located at:
# https://github.com/htem/GridTape_VNC_paper/tree/main/template_registration_pipeline/register_EM_dataset_to_template
# Development of this script is continuing here, not in the GridTape_VNC_paper repository


# TODO
# - Implement an interactive __main__ function where users can manually input
#    the coordinates of a single point they want to warp.

import os
import subprocess
import numpy as np

import transformix  # https://github.com/jasper-tms/pytransformix


template_plane_of_symmetry_x_voxel = 329
template_plane_of_symmetry_x_microns = 329 * 0.400


def warp_points_FANC_to_template(points,
                                 input_units='nanometers',
                                 output_units='microns',
                                 reflect=False):
    """
    Transform point coordinates from FANC to the corresponding point
    location in the 2018 Janelia Female VNC Template (JRC2018_VNC_FEMALE).

    Formally, this transforms coordinates from FANCv3 (the version of
    alignment used on CATMAID for manual tracing) to the template space,
    but FANCv4 (the version of alignment used on Neuroglancer for
    proofreading segmentation) is only slightly different from FANCv3,
    such that if you call this function on point coordinates from
    FANCv4, you'll still end up in essentially the correct location
    within the VNC template.

    Parameters
    ---------
    points (numpy.ndarray) :
        An Nx3 numpy array representing x,y,z point coordinates in FANC

    input_units (str) :
        The units of the points you provided as an input. Set to 'nm',
        'nanometer', or 'nanometers' to indicate nanometers;
        'um', 'µm', 'micron', or 'microns' to indicate microns; or
        'pixels' or 'voxels' to indicate pixel indices within the
        full-resolution FANC image volume, which has a pixel size of
        (4.3, 4.3, 45) nm.
        Default is nanometers.

    output_units (str) :
        The units you want points returned to you in. Same set of
        options as for `input_units`, except that the pixel size of the
        output space, JRC2018_VNC_FEMALE, is (0.4, 0.4, 0.4) µm.
        Default is microns.

    reflect (bool) :
        Whether to reflect the point coordinates across the midplane of
        the JRC2018_VNC_FEMALE template before returning them. This
        reflection moves points' x coordinates from the left to the
        right side of the VNC template or vice versa, but does not
        affect their y coordinates (anterior-posterior axis) or z
        coordinates (dorsal-ventral axis).
        Default is False.

    Returns
    -------
    An Nx3 numpy array representing x,y,z point coordinates in
    JRC2018_VNC_FEMALE, in units specified by `output_units`.
    """

    points = np.array(points, dtype=np.float64)
    if len(points.shape) == 1:
        result = warp_points_FANC_to_template(np.expand_dims(points, 0),
                                              input_units=input_units,
                                              output_units=output_units,
                                              reflect=reflect)
        if result is None:
            return result
        else:
            return result[0]

    if input_units in ['nm', 'nanometer', 'nanometers']:
        input_units = 'nanometers'
    elif input_units in ['um', 'µm', 'micron', 'microns']:
        input_units = 'microns'
    elif input_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        input_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for input_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")
    if output_units in ['nm', 'nanometer', 'nanometers']:
        output_units = 'nanometers'
    elif output_units in ['um', 'µm', 'micron', 'microns']:
        output_units = 'microns'
    elif output_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        output_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for output_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")

    if input_units == 'nanometers' and (points < 1000).all():
        resp = input("input_units is set to 'nanometers' but you provided "
                     'points with small values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None
    if input_units == 'microns' and (points > 1000).any():
        resp = input("input_units is set to 'microns' but you provided "
                     'points with large values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None

    # Convert points to nm so that the math below works
    if input_units == 'microns':
        points *= 1000
    elif input_units == 'voxels':
        points *= (4.3, 4.3, 45)

    # This block of math looks mysterious but is explained in detail at
    # https://github.com/htem/GridTape_VNC_paper/blob/main/template_registration_pipeline/register_EM_dataset_to_template/README.md
    points -= (533.2, 533.2, 945)  # (1.24, 1.24, 2.1) vox at (430, 430, 450)nm/vox
    points /= (430, 430, 450)
    points *= (300, 300, 400)
    points[:, 2] = 435*400 - points[:, 2]  # z flipping a stack with 436 slices

    points /= 1000  # Convert nm to microns as required for this transform
    transform_params = os.path.join(
        os.path.dirname(__file__),
        'transform_parameters',
        'TransformParameters.FixedFANC.txt'
    )
    # Do the transform. This requires input in microns and gives output in microns
    points = transformix.transform_points(points, transform_params)

    if not reflect:  # The z flip above caused a reflection, so un-reflect
        points[:, 0] = template_plane_of_symmetry_x_microns * 2 - points[:, 0]

    if output_units == 'nanometers':
        points *= 1000  # Convert microns to nm
    elif output_units == 'voxels':
        points /= 0.4  # Convert microns to JRC2018_FEMALE_VNC voxels

    return points


def warp_points_template_to_FANC(points,
                                 input_units='microns',
                                 output_units='nanometers',
                                 reflect=False):
    """
    Transform point coordinates from the 2018 Janelia Female VNC Template
    (JRC2018_VNC_FEMALE) to the corresponding point location in FANC.

    Formally, this transforms coordinates from the template space to
    FANCv3 (the version of alignment used on CATMAID for manual tracing)
    but FANCv4 (the version of alignment used on Neuroglancer for
    proofreading segmentation) is only slightly different from FANCv3,
    such that if you call this function and then input the results into
    neuroglancer, you'll still end up in essentially the correct
    location within FANC.

    Parameters
    ---------
    points (numpy.ndarray) :
        An Nx3 numpy array representing x,y,z point coordinates in the
        2018 Janelia Female VNC Template, JRC2018_VNC_FEMALE.

    input_units (str) :
        The units of the points you provided as an input. Set to 'nm',
        'nanometer', or 'nanometers' to indicate nanometers; 'um', 'µm',
        'micron', or 'microns' to indicate microns; or 'pixels' or
        'voxels' to indicate pixel indices within the JRC2018_VNC_FEMALE
        image volume, which has a pixel size of (0.4, 0.4, 0.4) µm.
        Default is microns.

    output_units (str) :
        The units you want points returned to you in. Same set of
        options as for `input_units`, except that the pixel size of the
        output space, FANC, is (4.3, 4.3, 45) nm.
        Default is nanometers.

    reflect (bool) :
        Whether to reflect the point coordinates across the midplane of
        the JRC2018_VNC_FEMALE template before warping them into
        FANC-space. This reflection moves points' x coordinates from the
        left to the right side of the VNC template or vice versa, but
        does not affect their y coordinates (anterior-posterior axis) or
        z coordinates (dorsal-ventral axis).
        Default is False.

    Returns
    -------
    An Nx3 numpy array representing x,y,z point coordinates in FANC, in
    units specified by `output_units`.
    """

    points = np.array(points)
    if len(points.shape) == 1:
        result = warp_points_template_to_FANC(np.expand_dims(points, 0),
                                             input_units=input_units,
                                             output_units=output_units,
                                             reflect=reflect)
        if result is None:
            return result
        else:
            return result[0]

    if input_units in ['nm', 'nanometer', 'nanometers']:
        input_units = 'nanometers'
    elif input_units in ['um', 'µm', 'micron', 'microns']:
        input_units = 'microns'
    elif input_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        input_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for input_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")
    if output_units in ['nm', 'nanometer', 'nanometers']:
        output_units = 'nanometers'
    elif output_units in ['um', 'µm', 'micron', 'microns']:
        output_units = 'microns'
    elif output_units in ['pixel', 'pixels', 'voxel', 'voxels']:
        output_units = 'voxels'
    else:
        raise ValueError("Unrecognized value provided for output_units. Set it"
                         " to 'nanometers', 'microns', or 'pixels'.")

    if input_units == 'nanometers' and (points < 1000).all():
        resp = input("input_units is set to 'nanometers' but you provided "
                     'points with small values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None
    if input_units == 'microns' and (points > 1000).any():
        resp = input("input_units is set to 'microns' but you provided "
                     'points with large values. You likely forgot to set '
                     'input_units correctly. Continue [y] or exit [enter]? ')
        if resp.lower() != 'y':
            return None

    # Convert to microns as required for this transform
    if input_units == 'nanometers':
        points /= 1000  # Convert nm to microns
    elif input_units == 'voxels':
        points *= (4.3, 4.3, 45) / 1000  # Convert voxels to microns

    if not reflect:  # The z flip below will cause a reflection, so un-reflect
        points[:, 0] = template_plane_of_symmetry_x_microns * 2 - points[:, 0]

    transform_params = os.path.join(
        os.path.dirname(__file__),
        'transform_parameters',
        'TransformParameters.FixedTemplate.Bspline.txt'
    )
    # Do the transform. This requires input in microns and gives output in microns
    points = transformix.transform_points(points, transform_params)

    points *= 1000  # Convert microns to nm so that the math below works
    # This block of math looks mysterious but is explained in detail at
    # https://github.com/htem/GridTape_VNC_paper/blob/main/template_registration_pipeline/register_EM_dataset_to_template/README.md
    points[:, 2] = 435*400 - points[:, 2]  # z flipping a stack with 436 slices
    points /= (300, 300, 400)
    points *= (430, 430, 450)
    points += (533.2, 533.2, 945)  # (1.24, 1.24, 2.1) vox at (430, 430, 450)nm/vox

    if output_units == 'microns':
        points /= 1000  # Convert nm to microns
    elif output_units == 'voxels':
        points /= (4.3, 4.3, 45)  # Convert nm to FANC voxels
    return points


if __name__ == "__main__":
    pass
