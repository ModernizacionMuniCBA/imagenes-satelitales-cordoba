#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera una serie de imágenes multibanda a partir de las bandas ya procesadas:

  * Genera imágenes multibanda color natural
  * Corrige gamma y contraste a una imagen
  * Aplica _histogram matching_ en base a la imagen corregida
  * Crea gifs animados con los previews, ordenados por fecha

"""
import glob
import os
import rasterio
import shutil
import subprocess
import imageio
import numpy as np
from itertools import groupby
from PIL import Image, ImageDraw, ImageFont

band_combinations = {
    'LANDSAT_5-TM':       (3, 2, 1),
    'LANDSAT_7-ETM':      (3, 2, 1),
    'LANDSAT_8-OLI_TIRS': (4, 3, 2),
}

def process_reference_image(root):
    out_path = create_rgb_image(root)
    correct_color(out_path)
    export_png(out_path)

def process_image(ref_scene, root):
    out_path = create_rgb_image(root)
    ref_path = glob.glob(os.path.join(ref_scene, 'rgb_preview.tif'))[0]
    apply_histogram_matching(out_path, ref_path)
    export_png(out_path)

def get_band_filenames(root):
    satsensor = root.split(os.path.sep)[-1]
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
    cmd = 'rio color -j -1 {src} {dst} ' \
          'sigmoidal RGB 5 0.1 gamma R 1.06 gamma G 1.08 gamma B 1.02 saturation 1.2'.format(src=in_path, dst=tmp_path)
    subprocess.run(cmd, shell=True)
    shutil.move(tmp_path, in_path)
    print('{} color corrected'.format(in_path))

def apply_histogram_matching(in_path, ref_path):
    """Aplica especificación de histograma en base a una imagen de referencia"""
    tmp_path = in_path + '.tmp'
    cmd = 'rio hist ' \
          '-c LCH -b 1,2,3 ' \
          '{src} {ref} {dst}'.format(src=in_path, ref=ref_path, dst=tmp_path)
    subprocess.run(cmd, shell=True)
    shutil.move(tmp_path, in_path)
    print('{} applied histogram matching using {}'.format(in_path, ref_path))

def export_png(in_path):
    """Exporta la imagen en .PNG"""
    fname, _ = os.path.splitext(in_path)
    out_path = '{}.png'.format(fname)
    cmd = 'gdal_translate -q {src} {dst} ' \
          '-of PNG -ot Byte ' \
          '-scale_1 1 255 ' \
          '-scale_2 1 255 ' \
          '-scale_3 1 255'.format(src=in_path, dst=out_path)
    subprocess.run(cmd, shell=True)
    print('{} written'.format(out_path))

def create_animations_per_satsensor(input_dir, **kwargs):
    """Crea GIFs animados a partir de los previews RGB de cada satélite"""

    def sortkey(fname):
        """Ordena por (satsensor, year)"""
        ps = fname.split(os.path.sep)
        return (ps[-2], ps[-3])

    files = sorted(rgb_preview_files(input_dir), key=sortkey)
    for satsensor, files in groupby(files, lambda f: f.split(os.path.sep)[-2]):
        gif_path = os.path.join(input_dir, 'rgb_{}.gif'.format(satsensor))
        create_animation(files, gif_path, **kwargs)
        print('{} written'.format(gif_path))

def rgb_preview_files(input_dir):
    for root, dirs, files in os.walk(input_dir):
        if files:
            for fname in glob.glob(os.path.join(root, 'rgb_preview.png')):
                yield fname

def create_animation(files, output_path, **kwargs):
    frames = []
    for fname in files:
        frame = imageio.imread(fname)
        year = fname.split(os.path.sep)[-3]
        annotated_frame = annotate_image(frame, year)
        frames.append(annotated_frame)
    imageio.mimsave(output_path, frames, format='GIF', **kwargs)

def annotate_image(img_array, year):
    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/roboto/hinted/Roboto-Bold.ttf", 32, encoding="unic")
    draw.text((img.width - 85, img.height - 55), year, (255, 255, 255), font=font)
    new_img_array = np.array(img.getdata(), dtype=np.uint8).reshape(img_array.shape)
    return new_img_array

def all_scenes(input_dir):
    for root, dirs, files in os.walk(input_dir):
        if files and glob.glob(os.path.join(root, '*.TIF')):
            yield root


if __name__ == '__main__':
    import argparse
    import multiprocessing
    from functools import partial

    parser = argparse.ArgumentParser(
            description='Genera imágenes RGB a partir de bandas procesadas de Landsat',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--input-dir', '-i', nargs='?', default='processed_data/',
            help='Ruta donde están almacenadas las imágenes')

    args = parser.parse_args()

    # Primero procesa la imagen de referencia para la especificación de histograma
    all_scenes = list(all_scenes(args.input_dir))
    ref_scene, other_scenes = all_scenes[0], all_scenes[1:-1]
    process_reference_image(ref_scene)

    # Luego procesa todas las imagenes
    count = multiprocessing.cpu_count()
    with multiprocessing.Pool(count) as pool:
        worker = partial(process_image, ref_scene)
        pool.map(worker, other_scenes)

    # Crea gifs animados de los previews RGB, por satélite
    create_animations_per_satsensor(args.input_dir, duration=0.1)
