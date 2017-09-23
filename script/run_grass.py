#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from subprocess import run
import argparse

parser = argparse.ArgumentParser(
        description='Ejecuta GRASS en un container de Docker',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--input-dir', '-i', nargs='?', default='data/',
        help='Ruta donde están almacenadas las imágenes')

args = parser.parse_args()

curdir = os.path.dirname(os.path.realpath(__file__))
datadir = os.path.realpath(args.input_dir)
datadir_dst = os.path.join('/data', args.input_dir)

cmd = 'docker run -it --rm ' \
      '-v {scriptdir_src}:/script ' \
      '-v {datadir_src}:{datadir_dst} ' \
      'dymaxionlabs/grass -text -c epsg:32620 /tmp/db'.format(
              scriptdir_src=curdir,
              datadir_src=datadir,
              datadir_dst=datadir_dst)

run(cmd, shell=True)
