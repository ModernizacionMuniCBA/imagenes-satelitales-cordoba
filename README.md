# Análisis sobre imágenes satelitales de la Ciudad de Córdoba

Recopilación de imágenes satelitales de la Ciudad de Córdoba y análisis
específicos sobre ellas.

## Descripción

Este repositorio contiene una serie de scripts que descargan imágenes
satelitales anuales de [Landsat](https://es.wikipedia.org/wiki/Landsat), las
procesa, y genera una serie de imágenes compuestas de color natural y color
falso para el análisis de la mancha urbana en el Municipio de Córdoba.

### Consulta y descarga

Para esta etapa del proceso es necesario una cuenta de Google e [instalar Google Cloud SDK](https://cloud.google.com/sdk/downloads).

*(explicar como instalar y configurar gsutil)*
...

#### Consulta con `script/query`

Consulta en el [dataset de
BigQuery](https://bigquery.cloud.google.com/table/bigquery-public-data:cloud_storage_geo_index.landsat_index)
de Google por imágenes de Landsat que contengan al Municipio, y genera un
archivo CSV con la lista de cada producto por año.

Se pide:

* Bajo porcentaje de nubosidad (menor a 1%).
* Collección de nivel 1 (Tier 1): Las imágenes ya tuvieron procesamiento
  geométrico y radiométrico.
* Sensores TM, ETM+ y OLI/TIRS: Estos sensores tienen bandas para rojo, verde y azul.
* Una imagen de cada satélite, en caso de que haya más de uno en un año dado

...

#### Descarga con `script/download`

A partir del CSV generado anteriormente, descarga las imágenes del [dataset de
Google](https://cloud.google.com/storage/docs/public-datasets/landsat) usando
`gsutil`.

...

### Procesamiento de las imágenes

#### GRASS GIS

Lo primero que se debe hacer es convertir las imágenes de Landsat originales a
reflectancia *Top-of-Atmosphere* (ToA, o *at-sensor reflectance*).

...

#### Otros procesos con `script/process`

A grandes rasgos los pasos de esta etapa son los siguientes:

* `fill_slc_gaps` (sólo **Landsat 7**): Se rellenan los gaps causados por la
  [falla del scanline corrector](https://landsat.usgs.gov/slc-products-background)
  post-2003 en el Landsat 7.
* `cut_image`: Se recortan las imágenes con el bounding box del shapefile pedido.
* `create_rgb_images`: Se generan imágenes RGB color natural y color falso.
* `gamma_corr`: Se aplica una corrección de gamma y contraste.
* `hist_match`: Se aplica *histogram matching* para que las imágenes compuestas
  sean comparables en el tiempo.

...
