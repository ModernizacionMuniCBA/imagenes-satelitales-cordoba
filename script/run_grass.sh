#!/bin/bash
# Le pasa un archivo descargado cualquiera para configurar el CRS del mapset de GRASS
somefile=$(find data/ -name *.TIF -print -quit)
# Levanta un contenedor de Docker con la imagen de GRASS
docker run -it --rm -v $(pwd)/script:/script -v $(pwd)/data:/data dymaxionlabs/grass -text -c /$somefile /tmp/db
