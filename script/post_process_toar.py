#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Realiza el último paso de procesamiento de las bandas post-ToA:

1. Cambia tipo de datos de Float64 a UInt16, con un rango de 1 a 10000,
   y 0 para nodata.
2. (sólo Landsat 7) Rellena gaps en imágenes con SLC-off por falla del SLC
3. Recorta todas las bandas con el bounding box de un Shapefile

Ejemplo de estructura de directorio:

```
processed_data/
    2009/
        LANDSAT_5-TM/
            2009_LANDSAT_5-TM_B1.tif
            2009_LANDSAT_5-TM_B2.tif
            2009_LANDSAT_5-TM_B3.tif
            ...
        LANDSAT_7-ETM/
            2009_LANDSAT_7-ETM_B1.tif
            2009_LANDSAT_7-ETM_B2.tif
            2009_LANDSAT_7-ETM_B3.tif
            ...
        metadata.json
    2010/
        ...
```

`metadata.json` contiene información sobre los productos o escenas que se
utilizaron para la generación de las bandas procesadas.

```
{ created_at: ,
  git_commit: ,
  datasets: [
    { id: 'LANDSAT_5',
      sensor_id: 'TM',
      scene_ids: ['LT52290822009303CUB00'] },
    { id: 'LANDSAT_7',
      sensor_id: 'ETM',
      scene_ids: ['LE72290822013002CUB00'] },
  ] }
```
"""
from pyproj import Proj, transform
import fiona
import glob
import os
import rasterio
import rasterio.tools.mask
import subprocess

def process(out_dir, features, in_path, tag_name=None, dry_run=False):
    out_path = get_output_path(in_path, out_dir, tag_name=tag_name)

    # Crea directorio (si no existe)
    out_dirname = os.path.dirname(out_path)
    os.makedirs(out_dirname, exist_ok=True)

    # Procesa imagen
    translate(in_path, out_path, dry_run=dry_run)
    fill_gaps(out_path, dry_run=dry_run)
    cut_image(out_path, out_path, features, dry_run=dry_run)

    print('{} written'.format(out_path))

    return out_path

def translate(in_path, out_path, dry_run=False):
    cmd = 'gdal_translate -q -ot UInt16 -of GTiff -scale 0 1 1 10000 ' \
          '-a_nodata 0 {src} -co compress=lzw {dst}'.format(
                  src=in_path, dst=out_path)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)
    return out_path

def get_output_path(in_path, out_dir, tag_name=None):
    dirname, in_fname = os.path.split(in_path)
    satsensor, year = dirname.split('/')[1:3]
    _, band_num = in_fname.split('_B')
    out_fname = '{year}_{sat}_B{num}'.format(
            year=year, sat=satsensor, num=band_num)
    if tag_name:
        out_fname = '{}_{}'.format(tag_name, out_fname)
    return os.path.join(out_dir, year, satsensor, out_fname)

def fill_gaps(in_path, dry_run=False):
    # Sólo rellena gaps si es una imagen del Landsat 7
    if 'LE07' not in in_path:
        return in_path
    cmd = 'gdal_fillnodata.py -q {src}'.format(src=in_path)
    if dry_run:
        print(cmd)
    else:
        subprocess.run(cmd, shell=True)
    return in_path

def cut_image(in_path, out_path, features, dry_run=False):
    """Corta la imagen usando +features+ como máscara"""
    if dry_run:
        return
    with rasterio.open(in_path) as src:
        out_image, out_transform = rasterio.tools.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            'driver': 'GTiff',
            'height': out_image.shape[1],
            'width': out_image.shape[2],
            'transform': out_transform
        })
        with rasterio.open(out_path, 'w', **out_meta) as dest:
            dest.write(out_image)

def feature_bounds_from(shape_file):
    """Devuelve el bounding box del +shape_file+, reproyectado a WGS84"""
    with fiona.open(shape_file, 'r') as source:
        orig_proj = Proj(source.crs)

        # Proyección de las imágenes de landsat:
        dest_proj = Proj('+proj=utm +zone=20 +datum=WGS84 +units=m +no_defs')

        minx, miny, maxx, maxy = source.bounds
        min_lon, min_lat = transform(orig_proj, dest_proj, minx, miny)
        max_lon, max_lat = transform(orig_proj, dest_proj, maxx, maxy)

        coords = [[[min_lon, max_lat], [max_lon, max_lat],
                  [max_lon, min_lat], [min_lon, min_lat], [min_lon, max_lat]]]

        return [{'type': 'Polygon', 'coordinates': coords}]

def each_file(input_dir, pattern):
    pat = os.path.join(input_dir, '**', pattern)
    for root, _, files in os.walk(input_dir):
        if files:
            for path in glob.glob(os.path.join(root, pattern)):
                yield path

def main():
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
        features = feature_bounds_from(args.shape_file)
        files = list(each_file(args.input_dir, args.pattern))

        worker = partial(process,
                args.output_dir,
                features,
                tag_name=args.tag_name,
                dry_run=args.dry_run)
        pool.map(worker, files)

    # TODO
    #if not args.dry_run:
    #    for scene_dir in all_scenes(args.input_dir):
    #        write_metadata_file(scene_dir, args.output_dir, tag_name=args.tag_name)

if __name__ == '__main__':
    main()
