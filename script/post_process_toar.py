#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Realiza el último paso de procesamiento de las bandas post-ToA:

1. Cambia tipo de datos de Float64 a UInt16, con un rango de 1 a 10000,
   y 0 para nodata.
2. (sólo Landsat 7) Rellena gaps en imágenes con SLC-off por falla del SLC

"""
import subprocess
import os
import glob

def process(path, suffix='POST', **kwargs):
    if suffix in path:
        return
    print('Processing {}'.format(os.path.basename(path)))
    out_path = append_suffix_fname(path, suffix)
    translate(path, out_path, **kwargs)
    fill_gaps(out_path, **kwargs)
    return out_path

def translate(in_path, out_path, dry_run=False):
    cmd = 'gdal_translate -q -ot UInt16 -of GTiff -scale 0 1 1 10000 ' \
          '-a_nodata 0 {src} -co compress=lzw {dst}'.format(
                  src=in_path, dst=out_path)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)
        print('Converted {}'.format(os.path.basename(in_path)))
    return out_path

def append_suffix_fname(fname, suffix):
    name, ext = os.path.splitext(fname)
    return '{name}_{suffix}{ext}'.format(name=name, suffix=suffix, ext=ext)

def fill_gaps(in_path, dry_run=False):
    # Sólo rellena gaps si es una imagen del Landsat 7
    if 'LE07' not in in_path:
        return in_path
    cmd = 'gdal_fillnodata.py -q {src}'.format(src=in_path)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)
        print('Filled gaps on {} '.format(os.path.basename(in_path)))
    return in_path

def each_file(input_dir, pattern):
    pat = os.path.join(args.input_dir, '**', args.pattern)
    for root, _, files in os.walk(args.input_dir):
        if files:
            for path in glob.glob(os.path.join(root, args.pattern)):
                yield path


if __name__ == '__main__':
    import argparse
    import multiprocessing
    from functools import partial

    parser = argparse.ArgumentParser(
            description='Post-procesa imágenes ToA de Landsat',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input-dir', '-i', nargs='?', default='data/',
            help='Ruta donde están almacenadas las imágenes')
    parser.add_argument('--pattern', nargs='?', default='*_TOAR_*.TIF',
            help='Patrón de los archivos a ser procesados')
    parser.add_argument('--output-suffix', nargs='?', default='POST',
            help='Sufijo de los archivos procesados')
    parser.add_argument('--dry-run', action='store_true',
            help='Imprime en pantalla los comandos, pero no los ejecuta')

    args = parser.parse_args()

    count = multiprocessing.cpu_count()

    with multiprocessing.Pool(count) as pool:
        files = list(each_file(args.input_dir, args.pattern))
        worker = partial(process, suffix=args.output_suffix, dry_run=args.dry_run)
        pool.map(worker, files)
