#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Realiza el último paso de procesamiento de las bandas post-ToA:

1. Cambia tipo de datos de Float64 a UInt8, con un rango de 1 a 255,
   y 0 para nodata.  La banda térmica la pasa a UInt16 sin reescalar.
2. (sólo Landsat 7) Rellena gaps en imágenes con SLC-off por falla del SLC
3. Recorta todas las bandas con el bounding box de un Shapefile

Ejemplo de estructura de directorio:

```
processed_data/
    2009/
        LANDSAT_5-TM/
            2009_LANDSAT_5-TM_metadata.json
            2009_LANDSAT_5-TM_B1.tif
            2009_LANDSAT_5-TM_B2.tif
            2009_LANDSAT_5-TM_B3.tif
            ...
        LANDSAT_7-ETM/
            2009_LANDSAT_7-ETM_metadata.json
            2009_LANDSAT_7-ETM_B1.tif
            2009_LANDSAT_7-ETM_B2.tif
            2009_LANDSAT_7-ETM_B3.tif
            ...
    2010/
        ...
```

En cada directorio se escribe un archivo `metadata.json` que contiene
información sobre la escena utilizada.

"""
import glob
import os
import shutil
import subprocess
import json
from datetime import datetime

metadata_fname = 'metadata.json'

def process(out_dir, shp_path, in_path, tag_name=None, dry_run=False):
    out_path = get_output_path(in_path, out_dir, tag_name=tag_name)

    # Crea directorio (si no existe)
    if not dry_run:
        out_dirname = os.path.dirname(out_path)
        os.makedirs(out_dirname, exist_ok=True)

    # Procesa imagen
    translate(in_path, out_path, dry_run=dry_run)
    fill_gaps(out_path, dry_run=dry_run)
    cut_image(out_path, shp_path, dry_run=dry_run)

    if not dry_run:
        print('{} written'.format(out_path))

    return out_path

def is_thermal_band(path):
    return ('LANDSAT_8' in path and any(b in path for b in ('B10', 'B11'))) or \
           (('LANDSAT_5' in path or 'LANDSAT_7' in path) and 'B6' in path)

def translate(in_path, out_path, dry_run=False):
    """Convierte el raster a un GeoTIFF comprimido de UInt16"""

    cmd = 'gdal_translate -q -of GTiff ' \
          '-a_nodata 0 {extra_opts} {src} -co compress=lzw {dst}'

    # Sólo reescala de 0..1 a 1..255 si no es banda térmica.
    # Las bandas térmicas están en grados Kelvin.
    if is_thermal_band(in_path):
        opts = '-ot UInt16'
    else:
        opts = '-ot Byte -scale 0 1 1 255'

    cmd = cmd.format(src=in_path, dst=out_path, extra_opts=opts)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)

    return out_path

def get_output_path(in_path, out_dir, tag_name=None):
    """Construye la ruta destino de cada banda"""
    dirname, in_fname = os.path.split(in_path)
    satsensor, year = dirname.split('/')[1:3]
    _, band_num = in_fname.split('_B')
    out_fname = '{year}_{sat}_B{num}'.format(
            year=year, sat=satsensor, num=band_num)
    if tag_name:
        out_fname = '{}_{}'.format(tag_name, out_fname)
    return os.path.join(out_dir, year, satsensor, out_fname)

def fill_gaps(in_path, dry_run=False):
    """Rellenar gaps causados por la falla del SLC del Landsat 7"""
    # Sólo rellena gaps si es una imagen del Landsat 7
    if 'LANDSAT_7-ETM' not in in_path:
        return in_path
    cmd = 'gdal_fillnodata.py -q {src}'.format(src=in_path)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)
    return in_path

def cut_image(in_path, shp_path, dry_run=False):
    """Corta la imagen usando el shapefile como máscara"""
    tmp_path = in_path + '.tmp'
    cmd = 'gdalwarp -q -cutline {shp} -co compress=lzw -overwrite -crop_to_cutline ' \
          '{src} {dst}'.format(shp=shp_path, src=in_path, dst=tmp_path)
    if dry_run:
        print(cmd)
        print('mv {} {}'.format(tmp_path, in_path))
    else:
        subprocess.run(cmd, shell=True)
        shutil.move(tmp_path, in_path)
    return in_path

def all_scene_files(input_dir, pattern):
    pat = os.path.join(input_dir, '**', pattern)
    for root, _, files in os.walk(input_dir):
        if files:
            for path in glob.glob(os.path.join(root, pattern)):
                yield path

def copy_metadata_files(input_dir, output_dir, tag_name=None, dry_run=False):
    for root, _, files in os.walk(input_dir):
        if metadata_fname in files:
            src = os.path.join(root, metadata_fname)

            satsensor, year = root.split('/')[1:3]
            dst_dirname = os.path.join(output_dir, year, satsensor)

            if dry_run:
                print('mkdir -p {}'.format(dst_dirname))
            else:
                os.makedirs(dst_dirname, exist_ok=True)

            dst_fname = '{year}_{sat}_{fname}'.format(
                year=year, sat=satsensor, fname=metadata_fname)
            if tag_name:
                dst_fname = '{}_{}'.format(tag_name, dst_fname)
            dst = os.path.join(dst_dirname, dst_fname)

            if dry_run:
                print('cp {} {}'.format(src, dst))
            else:
                shutil.copyfile(src, dst)


if __name__ == '__main__':
    import argparse
    import multiprocessing
    from functools import partial

    parser = argparse.ArgumentParser(
            description='Post-procesa imágenes ToA de Landsat',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('shape_file', metavar='SHAPE_FILE')
    parser.add_argument('--tag-name', '-t', nargs='?',
            help='Nombre del conjunto de imágenes')
    parser.add_argument('--input-dir', '-i', nargs='?', default='data/',
            help='Ruta donde están almacenadas las imágenes (ToA)')
    parser.add_argument('--output-dir', '-o', nargs='?', default='processed_data/',
            help='Ruta donde se guardarán las imágenes procesadas')
    parser.add_argument('--pattern', nargs='?', default='*_TOAR_*.TIF',
            help='Patrón de los archivos a ser procesados')
    parser.add_argument('--dry-run', action='store_true',
            help='Imprime en pantalla los comandos, pero no los ejecuta')

    args = parser.parse_args()

    if args.tag_name:
        args.output_dir = os.path.join(args.output_dir, args.tag_name)

    count = multiprocessing.cpu_count()
    with multiprocessing.Pool(count) as pool:
        files = list(all_scene_files(args.input_dir, args.pattern))
        worker = partial(process,
                args.output_dir,
                args.shape_file,
                tag_name=args.tag_name,
                dry_run=args.dry_run)
        pool.map(worker, files)

    copy_metadata_files(args.input_dir, args.output_dir,
        tag_name=args.tag_name, dry_run=args.dry_run)
