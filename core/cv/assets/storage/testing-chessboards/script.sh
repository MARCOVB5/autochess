#!/usr/bin/env bash
#
# rotate_all_180.sh — Gira todas as JPG do diretório atual em 180° usando `magick`
#

shopt -s nullglob
for img in *.jpg; do
  echo "Rotacionando $img → 180°"
  magick "$img" -rotate 180 "$img"
done

echo "Concluído: todas as JPG giradas 180°."

