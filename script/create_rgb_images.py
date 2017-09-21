#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera una serie de imágenes multibanda a partir de las bandas ya procesadas:

  * Genera imágenes multibanda color natural y color falso
  * Corrige gamma y contraste
  * Aplica _histogram matching_

"""
import glob
import os
import rasterio

band_combinations = {
    'nat__LANDSAT_5-TM':         (3, 2, 1),
    'urban__LANDSAT_5-TM':       (7, 5, 3),
    'nat__LANDSAT_7-ETM':        (3, 2, 1),
    'urban__LANDSAT_7-ETM':      (7, 5, 3),
    'nat__LANDSAT_8-OLI_TIRS':   (4, 3, 2),
    'urban__LANDSAT_8-OLI_TIRS': (7, 6, 4),
}

def process(root):
    create_rgb_image(root, 'nat')
    create_rgb_image(root, 'urban')

def get_band_filenames(root, combtype):
    satsensor = root.split('/')[-1]
    bands = band_combinations['{}__{}'.format(combtype, satsensor)]
    return [glob.glob(os.path.join(root, '*_B{}.TIF'.format(n)))[0] for n in bands]

def create_rgb_image(root, combtype='nat'):
    r_fn, g_fn, b_fn = get_band_filenames(root, combtype)
    out_path = os.path.join(root, '{}.tif'.format(combtype))
    with rasterio.open(r_fn) as r, rasterio.open(g_fn) as g, rasterio.open(b_fn) as b:
        profile = r.profile
        profile.update(count=3, compress='lzw')
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(r.read(1), 1)
            dst.write(g.read(1), 2)
            dst.write(b.read(1), 3)
    print('{} written'.format(out_path))

def main():
    import argparse

    parser = argparse.ArgumentParser(
            description='Genera imágenes RGB a partir de bandas procesadas de Landsat',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input-dir', '-i', nargs='?', default='processed_data/',
            help='Ruta donde están almacenadas las imágenes')

    args = parser.parse_args()

    for root, dirs, files in os.walk(args.input_dir):
        if files and glob.glob(os.path.join(root, '*.TIF')):
            process(root)


if __name__ == '__main__':
    main()
