# Análisis sobre imágenes satelitales de la Ciudad de Córdoba

Recopilación de imágenes satelitales de la Ciudad de Córdoba y análisis
específicos sobre ellas.

## Descripción

Este repositorio contiene una serie de scripts que descargan imágenes
satelitales anuales de [Landsat](https://es.wikipedia.org/wiki/Landsat), las
procesa, y genera una serie de imágenes compuestas de color natural y color
falso para el análisis de la mancha urbana en el Municipio de Córdoba.

## Instalación

El código está pensado para ser ejecutado en Ubuntu/Debian y depende de las
siguientes bibliotecas y programas:

* Python 3.3+
* GDAL/OGR 1.8+
* proj.4
* GRASS GIS 7.2
* Google Cloud SDK
* Docker engine (para GRASS)

### Python, GDAL, proj.4

En Ubuntu algunas de las dependencias se pueden instalar ejecutando la
siguiente línea:

```
sudo apt-get install -y build-essential python3 libpython3-dev libgdal1-dev
```

Los paquetes de Python necesarios están listados en `requirements.txt`. Para
instalarlos, ejecutar lo siguiente:

```
sudo -H pip install -r requirements.txt
```

### Google Cloud SDK

Para los scripts de consulta y descarga de imágenes (`script/query` y
`script/download`) es necesario tener una cuenta de Google e [instalar Google
Cloud SDK](https://cloud.google.com/sdk/downloads).

La forma más facil de instalar el SDK es usando el instalador interactivo.
Desde una línea de comando ejecutar:

```
curl https://sdk.cloud.google.com | bash
```

Al terminar, reiniciar la terminal o ejecutar el siguiente comando:

```
exec -l $SHELL
```

Finalmente, para configurar el SDK con nuestra cuenta de Google:

```
gcloud init
```

### Docker engine

En una etapa del proceso se utiliza GRASS GIS para hacer distintas correcciones
a las imágenes originales.  Para simplificar el proceso, se provee de un script que
levanta un contenedor Docker de GRASS.

Ver [Get Docker CE for
Ubuntu](https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/#install-from-a-package)
para más información sobre cómo instalar Docker engine en Ubuntu.

## Uso

### Consulta y descarga

#### Consulta con `script/query`

Consulta en el [dataset de
BigQuery](https://bigquery.cloud.google.com/table/bigquery-public-data:cloud_storage_geo_index.landsat_index)
de Google por imágenes de Landsat que contengan al Municipio, y genera un
archivo CSV con la lista de cada producto por año.

Se asegura de armar una lista de escenas con las siguientes características:

* Bajo porcentaje de nubosidad (menor a 1%).
* Colección de nivel 1 (Tier 1): Las imágenes de esta colección ya tienen
  procesamiento geométrico y radiométrico.
* Sensores TM, ETM+ y OLI/TIRS: Estos sensores tienen bandas para rojo, verde y azul.
* Una imagen de cada satélite, en caso de que haya más de uno en un año dado.

El script toma de entrada un archivo de geometría (Shapefile, GeoJSON, etc.),
lo reproyecta a WGS84 (EPSG 4326), consulta por imágenes que contengan el
*bounding box* de todos los features, y escribe por salida estándar un archivo
CSV con información sobre cada escena, necesaria para la descarga.

Ejemplo de uso:

```
script/query.py EjidoMunicipal.shp > escenas.csv
```

El CSV tiene esta apariencia:

```
id,year,sensing_time,spacecraft_id,sensor_id,wrs_path,wrs_row,total_size,base_url
LC82290822017101LGN00,2017,2017-04-11T14:08:02.7848630Z,LANDSAT_8,OLI_TIRS,229,82,960658101,gs://gcp-public-data-landsat/LC08/01/229/082/LC08_L1TP_229082_20170411_20170415_01_T1
LC82290822016259LGN01,2016,2016-09-15T14:08:47.3154210Z,LANDSAT_8,OLI_TIRS,229,82,1001887426,gs://gcp-public-data-landsat/LC08/01/229/082/LC08_L1TP_229082_20160915_20170321_01_T1
LE72290822016235CUB00,2016,2016-08-22T14:11:12.3172647Z,LANDSAT_7,ETM,229,82,221288879,gs://gcp-public-data-landsat/LE07/01/229/082/LE07_L1TP_229082_20160822_20161007_01_T1
LC82290822015288LGN01,2015,2015-10-15T14:08:33.3921030Z,LANDSAT_8,OLI_TIRS,229,82,1010734265,gs://gcp-public-data-landsat/LC08/01/229/082/LC08_L1TP_229082_20151015_20170403_01_T1
...
```


#### Descarga con `script/download`

A partir del CSV generado anteriormente, descarga las imágenes del [dataset de
Google](https://cloud.google.com/storage/docs/public-datasets/landsat) usando
`gsutil`.

...

### Procesamiento de las imágenes

#### Conversión de DN a reflectancia ToA con GRASS

Lo primero que se debe hacer es convertir las imágenes de Landsat originales a
reflectancia *Top-of-Atmosphere* (ToA, o *at-sensor reflectance*).

...

#### Post procesamiento con `script/pots_process_toar`

A grandes rasgos los pasos de esta etapa son los siguientes:

* (sólo **Landsat 7**): Se rellenan los gaps causados por la
  [falla del scanline corrector](https://landsat.usgs.gov/slc-products-background)
  post-2003 en el Landsat 7.
* Se recortan las imágenes con el bounding box del shapefile pedido.
* Se generan imágenes RGB color natural y color falso.
* Se aplica una corrección de gamma y contraste.
* Se aplica *histogram matching* para que las imágenes compuestas
  sean comparables en el tiempo.

### Imagenes RGB

...
