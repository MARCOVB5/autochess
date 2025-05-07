# Chess Vision System

A computer vision system developed in Python to automatically detect and recognize chess pieces on a physical 4×4 chess board with flat pieces.

## Project Overview

This system uses a webcam positioned above a yellow and green chess board to identify:

- Position of each piece (board coordinates)
- Color of each piece (black or white)
- Type of each piece (king, queen, rook/tower, pawn)

## System Architecture

The project follows a modular architecture for better organization and maintainability:

```
cv/
├── assets/            # Reference piece templates
├── modules/           # Core functionality modules
│   ├── __init__.py    # Package initialization
│   ├── pattern_detection.py     # Board pattern recognition
│   ├── piece_detection.py       # Chess piece detection
│   ├── piece_analysis.py        # Color and type analysis
│   ├── visualization.py         # Visualization tools
│   └── utils.py                 # Utility functions
└── main.py            # Main application entry point
```

## Features

- **Board Detection**: Identifies the chess board using color thresholding and perspective transformation
- **Piece Detection**: Locates chess pieces using contour detection and Hough Circle Transform
- **Color Analysis**: Determines piece color using HSV color space analysis
- **Type Recognition**: Identifies piece types using template matching and geometric analysis
- **Visualization**: Provides various visual outputs for analysis and debugging

## Technical Implementation

### Core Technologies
- **OpenCV**: Image processing and computer vision algorithms
- **NumPy**: Numerical operations and array manipulation

### Key Algorithms
1. **Board Detection**:
   - HSV color thresholding for yellow and green squares
   - Contour detection for board boundaries
   - Perspective transformation to normalize view

2. **Piece Detection**:
   - Adaptive thresholding for piece segmentation
   - Contour analysis with circularity filtering
   - Hough Circle Transform as a fallback detection method

3. **Piece Analysis**:
   - HSV color space analysis for piece color determination
   - Template matching for piece type identification
   - Geometric feature extraction as backup classification

4. **Visualization**:
   - Color-coded piece labeling
   - Symbol enhancement for clearer identification
   - Debug visualizations for HSV values and histograms

## Installation

### Prerequisites
- Python 3.6+
- OpenCV
- NumPy

### Setup
```bash
pip install opencv-python numpy
```

## Usage

### Basic Usage
```bash
python cv/main.py --image path/to/image.jpg
```

### Command-line Options
```
--image PATH             Path to the chessboard image
--yellow-lower H,S,V     Lower HSV bounds for yellow squares
--yellow-upper H,S,V     Upper HSV bounds for yellow squares
--green-lower H,S,V      Lower HSV bounds for green squares
--green-upper H,S,V      Upper HSV bounds for green squares
--save-all               Save all intermediate images
--output-dir DIR         Directory to save output images
--analyze-hsv            Run HSV color analysis tool
--debug                  Show detailed debug visualizations
--analyze-pieces         Analyze reference piece images
--use-hough              Force Hough Circle Transform for detection
```

### Example
```bash
python cv/main.py --image chessboard.jpg --debug --save-all
```

## Development Notes

- The system is designed for a 4×4 chess board with flat pieces
- The camera should be positioned directly above the board
- For best results, ensure good lighting conditions
- Template images can be added to the `assets` folder for improved type recognition

## Output

The system generates a combined visualization with four panels:
1. Original image
2. Piece detection visualization
3. Color and type identification
4. Symbol-only visualization

## License

This project is available for educational and research purposes. 