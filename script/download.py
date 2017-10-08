#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dado un CSV pasado por entrada estandar (stdin), descarga los productos del
dataset de Google.

"""
import json
import os
import subprocess

def product_dir(product, output_dir):
    satsensor = '{}-{}'.format(product['spacecraft_id'], product['sensor_id'])
    path = os.path.join(output_dir, satsensor, product['year'], product['id'])
    return path

def download_product(product, output_dir, dry_run=False):
    # Define ruta y crea directorio
    path = product_id(product, output_dir)
    if not dry_run:
        os.makedirs(path, exist_ok=True)

    # Arma cadena del comando
    cmd = 'gsutil -m cp -r {src} {dst}'.format(src=product['base_url'], dst=path)

    # Si está en modo dry-run sólo imprime en pantalla el comando
    if dry_run:
        print(cmd)
        return

    # Ejecuta el comando
    subprocess.run(cmd, shell=True)

def write_metadata_file(product, output_dir, dry_run=False):
    if dry_run:
        return
    path = product_dir(product, output_dir)
    os.makedirs(path, exist_ok=True)

    json_path = os.path.join(path, 'metadata.json')
    with open(json_path, 'w') as f:
        f.write(json.dumps(product))

if __name__ == '__main__':
    import argparse
    import csv
    import sys

    parser = argparse.ArgumentParser(
            description='Descarga imágenes de Landsat o Sentinel-2 ' \
                        'a partir de un CSV de productos',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('csvfile', metavar='CSV_FILE', nargs='?',
            type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output-dir', '-o', nargs='?', default='data/',
            help='Ruta donde se almacenarán las imágenes descargadas')
    parser.add_argument('--dry-run', action='store_true',
            help='Imprime en pantalla los comandos de gsutil, pero no los ejecuta')

    args = parser.parse_args()

    reader = csv.DictReader(args.csvfile)
    for row in reader:
        download_product(row, args.output_dir, dry_run=args.dry_run)
        write_metadata_file(row, args.output_dir, dry_run=args.dry_run)
