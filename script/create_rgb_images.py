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
import shutil
import subprocess

band_combinations = {
    'LANDSAT_5-TM':         (3, 2, 1),
    'LANDSAT_7-ETM':        (3, 2, 1),
    'LANDSAT_8-OLI_TIRS':   (4, 3, 2),
}

def process(root):
    out_path = create_rgb_image(root)
    correct_color(out_path)
    export_png(out_path)

def get_band_filenames(root):
    satsensor = root.split('/')[-1]
    bands = band_combinations[satsensor]
    return [glob.glob(os.path.join(root, '*_B{}.TIF'.format(n)))[0] for n in bands]

def create_rgb_image(root):
    """Crea una imagen GeoTIFF multibanda RGB usando las bandas RGB"""
    r_fn, g_fn, b_fn = get_band_filenames(root)
    out_path = os.path.join(root, 'rgb_preview.tif')
    with rasterio.open(r_fn) as r, rasterio.open(g_fn) as g, rasterio.open(b_fn) as b:
        profile = r.profile
        profile.update(count=3, compress='lzw')
        with rasterio.open(out_path, 'w', **profile) as dst:
            dst.write(r.read(1), 1)
            dst.write(g.read(1), 2)
            dst.write(b.read(1), 3)
    print('{} written'.format(out_path))
    return out_path

def correct_color(in_path):
    """Aplica una corrección de gamma y saturación para mejorar el contraste"""
    tmp_path = in_path + '.tmp'
    cmd = 'rio color -d uint16 -j 4 {src} {dst} ' \
          'sigmoidal RGB 5 0.2 ' \
          'gamma R 1.04 ' \
          'gamma G 1.05 ' \
          'gamma B 1.02 ' \
          'saturation 1.4'.format(src=in_path, dst=tmp_path)
    subprocess.run(cmd, shell=True)
    shutil.move(tmp_path, in_path)
    print('{} color corrected'.format(in_path))

def export_png(in_path):
    """Exporta la imagen en .PNG"""
    fname, _ = os.path.splitext(in_path)
    out_path = '{}.png'.format(fname)
    cmd = 'gdal_translate -q {src} {dst} ' \
          '-of PNG -ot Byte ' \
          '-scale_1 1 10000 ' \
          '-scale_2 1 10000 ' \
          '-scale_3 1 10000'.format(src=in_path, dst=out_path)
    subprocess.run(cmd, shell=True)
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
