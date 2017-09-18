#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca una imagen anual de Landsat o Sentinel-2 que recubra las figuras de un
Shapefile determinado.  La salida del script es un CSV, con una imagen por
fila, y su URL para descargar desde Google Cloud Storage.

"""
import sys

def feature_bounds_from(shape_file):
    """
    Devuelve el bounding box del +shape_file+, reproyectado a WGS84

    Es necesario reproyectar para poder hacer la consulta de productos en los
    datasets de BigQuery.

    """
    from pyproj import Proj, transform
    import fiona

    with fiona.open(shape_file, 'r') as source:
        orig_proj = Proj(source.crs)
        dest_proj = Proj(init='EPSG:4326')
        minx, miny, maxx, maxy = source.bounds
        min_lon, min_lat = transform(orig_proj, dest_proj, minx, miny)
        max_lon, max_lat = transform(orig_proj, dest_proj, maxx, maxy)
        return (min_lon, min_lat, max_lon, max_lat)

def query_images(shp_path, query_method, print_query=False):
    """Consulta el dataset de BigQuery y retorna los resultados."""
    from google.cloud import bigquery

    client = bigquery.Client()

    bounds = feature_bounds_from(shp_path)

    query_string = query_method(bounds)
    if print_query:
        print(query_string, file=sys.stderr)

    query = client.run_sync_query(query_string)
    query.timeout_ms = 10000
    query.run()

    fieldnames = [field.name for field in query.schema]
    results = (dict((k, v) for k, v in zip(fieldnames, row)) for row in query.fetch_data())

    return results, fieldnames

def build_landsat_query(bounding_box):
    """Genera la consulta para el dataset de Landsat."""
    west_lon, south_lat, east_lon, north_lat = bounding_box
    qs = ('SELECT '
          'YEAR(sensing_time) AS year, '
          'FIRST(sensing_time) as sensing_time, '
          'FIRST(scene_id) AS scene_id, '
          'FIRST(spacecraft_id) AS spacecraft_id, '
          'FIRST(sensor_id) AS sensor_id, '
          'wrs_path, '
          'wrs_row, '
          'FIRST(total_size) AS total_size, '
          'FIRST(base_url) AS base_url '
        'FROM '
          '[bigquery-public-data:cloud_storage_geo_index.landsat_index] '
        'WHERE '
          'west_lon < {0} '
          'AND south_lat < {1} '
          'AND east_lon > {2} '
          'AND north_lat > {3} '
          'AND FLOAT(cloud_cover) < 1 '
          'AND collection_number = "01" '
          'AND data_type = "L1TP" '
          'AND sensor_id IN ("TM", "ETM", "OLI_TIRS") '
        'GROUP BY '
          'year, '
          'wrs_path, '
          'wrs_row '
        'ORDER BY '
          'year DESC, '
          'spacecraft_id DESC')
    return qs.format(west_lon, south_lat, east_lon, north_lat)

def build_sentinel2_query(bounding_box):
    """Genera la consulta para el dataset de Sentinel-2."""
    west_lon, south_lat, east_lon, north_lat = bounding_box
    qs = ('SELECT '
          'YEAR(sensing_time) AS year, '
          'FIRST(sensing_time) AS sensing_time, '
          'FIRST(granule_id) AS granule_id, '
          'FIRST(product_id) AS product_id, '
          'mgrs_tile, '
          'FIRST(total_size) AS total_size, '
          'FIRST(base_url) AS base_url '
        'FROM '
          '[bigquery-public-data:cloud_storage_geo_index.sentinel_2_index] '
        'WHERE '
          'west_lon < {0} '
          'AND south_lat < {1} '
          'AND east_lon > {2} '
          'AND north_lat > {3} '
          'AND FLOAT(cloud_cover) < 1 '
          'AND geometric_quality_flag = "PASSED" '
        'GROUP BY '
          'year, '
          'mgrs_tile '
        'ORDER BY '
          'year DESC')
    return qs.format(west_lon, south_lat, east_lon, north_lat)

def writecsv(results, fieldnames):
    """Escribe a stdout un CSV con los resultados."""
    import csv

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow(row)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Consulta de imágenes en Sentinel-2 o Landsat para un Shapefile')
    parser.add_argument('shape_file', metavar='SHAPE_FILE')
    parser.add_argument('--dataset', '-d', default='landsat', help='Dataset de imágenes. Opciones: landsat, sentinel2')
    parser.add_argument('--print-query', default=False, action='store_true', help='Imprime la consulta BigQuery')
    args = parser.parse_args()

    # Hace la consulta al dataset pedido
    query_method = build_landsat_query if args.dataset == 'landsat' else build_sentinel2_query
    results, fieldnames = query_images(args.shape_file, query_method, args.print_query)

    # Escribe a stdout un CSV con los resultados
    writecsv(results, fieldnames)
