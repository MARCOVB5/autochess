#!/usr/bin/env bash

set -e
set -u
set -o pipefail

DST="sift_ready"
echo "Creating output directory: $DST"
rm -rf "$DST"
mkdir -p "$DST"

echo "Starting image augmentation for SIFT training..."

PNG_FILES=(*.png)
if [ ! -f "${PNG_FILES[0]}" ]; then
    echo "ERROR: No PNG files found in the current directory!"
    echo "Please run this script in a directory containing PNG images."
    exit 1
fi

echo "Found ${#PNG_FILES[@]} PNG files to process"

total=${#PNG_FILES[@]}
current=0

for img in "${PNG_FILES[@]}"; do
    current=$((current + 1))
    base="${img%.png}"
    echo -ne "Processing image $current/$total: $img [$(( (current * 100) / total ))%]\r"
    
    if ! magick "$img" -colorspace Gray "$DST/${base}_gray.png"; then
        echo "ERROR: Failed to process $img with ImageMagick. Is ImageMagick installed correctly?"
        exit 1
    fi
    
    # Variações de forma, iluminação e foco usadas pelo fallback SIFT.
    magick "$img" -colorspace Gray -normalize -edge 2 -negate "$DST/${base}_edge.png"
    
    magick "$img" -colorspace Gray -level 25%,75% -threshold 50% "$DST/${base}_silhouette.png"
    
    magick "$img" -modulate 80 "$DST/${base}_darker.png"
    magick "$img" -modulate 120 "$DST/${base}_brighter.png"
    
    magick "$img" -brightness-contrast 0x30 "$DST/${base}_highcontrast.png"
    
    magick "$img" \( +clone -sparse-color Barycentric "0,0 black 0,100% white" \
           -function polynomial 3,-2,0.5 \) \
        -compose Overlay -composite "$DST/${base}_toplight.png"
    
    magick "$img" \( +clone -sparse-color Barycentric "0,0 black 100%,0 white" \
           -function polynomial 3,-2,0.5 \) \
        -compose Overlay -composite "$DST/${base}_sidelight.png"
    
    magick "$img" -statistic NonPeak 5x5 "$DST/${base}_noise.png"
    
    magick "$img" -gaussian-blur 0x1 "$DST/${base}_blur.png"
    
    for angle in -20 20; do
        magick "$img" -background none -rotate $angle "$DST/${base}_rotate${angle}.png"
    done
    
    magick "$img" -resize 80% "$DST/${base}_small.png"
    magick "$img" -resize 120% "$DST/${base}_large.png"
    
    magick "$img" -modulate 80 -rotate 15 "$DST/${base}_dark_rotated.png"
    
    magick "$img" -modulate 120 -statistic NonPeak 3x3 "$DST/${base}_bright_noise.png"
done

echo -e "\n"

image_count=$(find "$DST" -name "*.png" | wc -l)

if [ "$image_count" -eq 0 ]; then
    echo "ERROR: No images were generated in the output directory!"
    echo "Please check the script for errors."
    exit 1
fi

echo "Successfully generated $image_count images in the '$DST' directory"
echo ""
echo "For each chess piece, the following variations were created:"
echo "  • Grayscale conversion"
echo "  • Edge detection"
echo "  • Silhouette (solid shape)"
echo "  • Brightness variations (darker and brighter)"
echo "  • Contrast enhancement"
echo "  • Directional lighting (top and side)"
echo "  • Noise addition"
echo "  • Blur effect"
echo "  • Rotations (-20° and +20°)"
echo "  • Scaling (80% and 120%)"
echo "  • Combined transformations"
echo ""
echo "To view all generated images:"
echo "feh $DST"
