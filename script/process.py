#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Procesa todas las imágenes de Landsat:

  * Recorta las imágenes con un shapefile
  * Genera imágenes multibanda color natural y color falso
  * Corrige gamma y contraste
  * Aplica _histogram matching_

NOTA: Procesamiento para las imágenes de Sentinel-2 aún no está
implementado.
"""
from pyproj import Proj, transform
import fiona
import rasterio
import rasterio.tools.mask

def process(in_path, out_basedir, shape_file):
    features = feature_bounds_from(shape_file)
    dirname, basename = os.path.split(in_path)
    out_dirname = os.path.join(out_basedir, dirname[dirname.find('/')+1:])
    out_path = os.path.join(out_dirname, basename)

    print(in_path, out_path, os.path.dirname(out_path))
    cut_image(in_path, out_path, features)
    print('[cut] {} done'.format(basename))


def cut_image(input_path, output_path, features):
    """Corta la imagen usando +features+ como máscara"""
    with rasterio.open(input_path) as src:
        out_image, out_transform = rasterio.tools.mask.mask(src, features, crop=True)
        out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

def feature_bounds_from(shape_file):
    """
    Devuelve el bounding box del +shape_file+, reproyectado a WGS84

    Es necesario reproyectar para poder hacer la consulta de productos en los
    datasets de BigQuery.

    """
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


if __name__ == '__main__':
    import argparse
    import os
    import glob

    parser = argparse.ArgumentParser(
            description='Procesa imágenes de Landsat',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('shape_file', metavar='SHAPE_FILE')
    parser.add_argument('--input-dir', '-i', nargs='?', default='data/',
            help='Ruta donde están almacenadas las imágenes')
    parser.add_argument('--output-dir', '-o', nargs='?', default='processed_data/',
            help='Ruta donde se guardarán las imágenes procesadas')
    parser.add_argument('--pattern', nargs='?', default='*_toar',
            help='Patrón de los archivos a ser procesados')

    args = parser.parse_args()

    pat = os.path.join(args.input_dir, '**', args.pattern)
    for root, _, files in os.walk(args.input_dir):
        if files:
            for path in glob.glob(os.path.join(root, args.pattern)):
                process(path, args.output_dir, args.shape_file)
