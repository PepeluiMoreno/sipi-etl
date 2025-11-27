#!/bin/bash

# Script para ejecutar scraping diario de todas las provincias

echo "=== Daily Scraping Started: $(date) ==="

# Provincias objetivo
PROVINCIAS=(
    "sevilla"
    "cadiz"
    "cordoba"
    "granada"
    "jaen"
    "huelva"
    "malaga"
    "almeria"
)

# Ejecutar para cada provincia
for provincia in "${PROVINCIAS[@]}"
do
    echo "Scraping: $provincia"
    docker-compose run --rm pipeline-idealista \
        python examples/full_pipeline_with_screenshots.py \
        --portal idealista \
        --provincia "$provincia" \
        --max-pages 10
done

echo "=== Daily Scraping Finished: $(date) ==="