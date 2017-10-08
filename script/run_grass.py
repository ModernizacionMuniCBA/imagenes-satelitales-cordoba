#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from subprocess import run
import argparse
import glob

parser = argparse.ArgumentParser(
        description='Ejecuta GRASS en un container de Docker',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--input-dir', '-i', nargs='?', default='data/',
        help='Ruta donde están almacenadas las imágenes')

args = parser.parse_args()

curdir = os.path.dirname(os.path.realpath(__file__))
datadir = os.path.realpath(args.input_dir)
datadir_dst = os.path.join('/', args.input_dir)

files = glob.glob(os.path.join(args.input_dir, '*', '*', '*', '*', '*.TIF'))
if not files:
    print('No hay archivos .TIF en {}'.format(args.input_dir))
some_tif_file = files[0]

cmd = 'docker run -it --rm ' \
      '-v {scriptdir_src}:/script ' \
      '-v {datadir_src}:{datadir_dst} ' \
      'dymaxionlabs/grass -text -c /{tif_file} /tmp/db'.format(
              scriptdir_src=curdir,
              datadir_src=datadir,
              datadir_dst=datadir_dst,
              tif_file=some_tif_file)

run(cmd, shell=True)
