#!/usr/bin/env python3

# Warp mesh files from JRC2018_VNC template space to FANC space
# Currently only works with stl files, need to write support for obj

import sys
import os

import stl  # pip install numpy-stl

import navis
import flybrains


def show_help():
    print('Run via: ./warp_mesh_to_FANC.py some_mesh.stl folder_to_put_output_in/')


def main():
    # Argument validation
    if len(sys.argv) < 3:
        show_help()
        return
    try:
        input_filename = sys.argv[1]
        if not os.path.exists(input_filename):
            raise FileNotFoundError(input_filename)

        if not input_filename.endswith('.stl'):
            raise NotImplementedError('Currently I only know how to open .stl format meshes')

        output_folder = sys.argv[2]
        if not os.path.exists(output_folder):
            raise FileNotFoundError(output_folder)
    except:
        show_help()
        raise


    # Load
    mesh = stl.mesh.Mesh.from_file(input_filename)
    # Do the warping
    mesh.v0 = navis.xform_brain(mesh.v0, source='JRCVNC2018U', target='FANC')
    mesh.v1 = navis.xform_brain(mesh.v1, source='JRCVNC2018U', target='FANC')
    mesh.v2 = navis.xform_brain(mesh.v2, source='JRCVNC2018U', target='FANC')
    # Save
    mesh.save(output_folder + '/' + os.path.basename(input_filename))


if __name__ == "__main__":
    main()
