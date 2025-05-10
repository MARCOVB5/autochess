#!/usr/bin/env bash
set -euo pipefail

# Simple and robust chess piece augmentation script for SIFT
# Focuses on generating clear, high-contrast images for reliable feature detection

# Create output directory
DST="sift_ready"
rm -rf "$DST"
mkdir -p "$DST"

echo "🔄 Generating high-quality SIFT training images..."

# Create a temp file for logging
LOG_FILE=$(mktemp)
trap 'rm -f "$LOG_FILE"' EXIT

process_image() {
    local img="$1"
    local base="${img%.png}"
    echo "Processing $img..."
    
    # 1) Create high-contrast edge versions
    # Edge detection with different strengths
    for strength in 1 2 3; do
        magick "$img" \
            -colorspace Gray \
            -normalize \
            -edge $strength \
            -negate \
            "$DST/${base}_edge${strength}.png"
    done
    
    # 2) Create solid silhouette with clean edges
    magick "$img" \
        -colorspace Gray \
        -level 25%,75% \
        -threshold 50% \
        "$DST/${base}_silhouette.png"
    
    # 3) Create outline version (border only)
    magick "$img" \
        -colorspace Gray \
        -level 25%,75% \
        -threshold 50% \
        -morphology edge Square \
        "$DST/${base}_outline.png"
    
    # 4) Create rotated versions (-30 to +30 degrees, 10-degree increments)
    for angle in -30 -20 -10 0 10 20 30; do
        # Edge version with rotation
        magick "$DST/${base}_edge2.png" \
            -background black \
            -rotate $angle \
            "$DST/${base}_edge_r${angle}.png"
        
        # Silhouette version with rotation
        magick "$DST/${base}_silhouette.png" \
            -background white \
            -rotate $angle \
            "$DST/${base}_silhouette_r${angle}.png"
            
        # Outline version with rotation
        magick "$DST/${base}_outline.png" \
            -background black \
            -rotate $angle \
            "$DST/${base}_outline_r${angle}.png"
    done
    
    # 5) Create scaled versions (80% to 120%, 20% increments)
    for scale in 80 100 120; do
        # Edge version with scaling
        magick "$DST/${base}_edge2.png" \
            -resize "${scale}%" \
            "$DST/${base}_edge_s${scale}.png"
            
        # Silhouette version with scaling
        magick "$DST/${base}_silhouette.png" \
            -resize "${scale}%" \
            "$DST/${base}_silhouette_s${scale}.png"
            
        # Outline version with scaling
        magick "$DST/${base}_outline.png" \
            -resize "${scale}%" \
            "$DST/${base}_outline_s${scale}.png"
    done
    
    # 6) Create a few combined transformations
    # Rotate and scale edge version
    magick "$DST/${base}_edge2.png" \
        -background black \
        -rotate 15 \
        -resize "110%" \
        "$DST/${base}_edge_r15_s110.png"
        
    magick "$DST/${base}_edge2.png" \
        -background black \
        -rotate -15 \
        -resize "90%" \
        "$DST/${base}_edge_rm15_s90.png"
        
    # 7) Create inverted versions for some variations
    magick "$DST/${base}_silhouette.png" \
        -negate \
        "$DST/${base}_silhouette_inv.png"
}

# Process each image
for img in *.png; do
    process_image "$img" >> "$LOG_FILE" 2>&1 || echo "⚠️ Error processing $img"
done

# Check if any images were generated
image_count=$(find "$DST" -name "*.png" | wc -l)

echo "✅ Generated $image_count images in the '$DST' directory"
echo ""
echo "For each chess piece, the following variations were created:"
echo "  • Edge detection (3 different strengths)"
echo "  • Silhouette (solid shape)"
echo "  • Outline (border only)"
echo "  • Rotations (-30° to +30°)"
echo "  • Scaling (80% to 120%)"
echo "  • Combined transformations"
echo ""
echo "To view all generated images:"
echo "feh $DST"
echo ""
echo "If you need to debug any issues, check the log file: $LOG_FILE"
