# Paper Size Options for MCQ Questions

## Current Setting: Custom Landscape (10in × 7in)
- **Format**: Landscape (wide)
- **Dimensions**: 10 inches × 7 inches
- **Best for**: Screen viewing, mobile devices, wide questions with multiple options
- **Pros**: Better aspect ratio for screens, more horizontal space for options
- **Cons**: May be too wide for some content

## Alternative Options:

### Option 1: A4 Landscape (Recommended for most cases)
```tex
\usepackage[a4paper,landscape,margin=0.4in]{geometry}
```
- **Dimensions**: 297mm × 210mm (11.7in × 8.3in)
- **Best for**: Standard format, good balance
- **Pros**: Standard size, familiar, good for printing if needed

### Option 2: A5 Landscape (More compact)
```tex
\usepackage[a5paper,landscape,margin=0.3in]{geometry}
```
- **Dimensions**: 210mm × 148mm (8.3in × 5.8in)
- **Best for**: Mobile viewing, compact questions
- **Pros**: Smaller file size, faster loading, better for mobile
- **Cons**: Less space for long questions

### Option 3: Square Format (Good for mobile)
```tex
\usepackage[paperwidth=8in,paperheight=8in,margin=0.4in]{geometry}
```
- **Dimensions**: 8 inches × 8 inches (square)
- **Best for**: Mobile screens, balanced viewing
- **Pros**: Works well on both portrait and landscape mobile orientations
- **Cons**: May waste space for wide content

### Option 4: Custom Wide (Current - optimized for screens)
```tex
\usepackage[paperwidth=10in,paperheight=7in,margin=0.4in,landscape]{geometry}
```
- **Dimensions**: 10 inches × 7 inches
- **Best for**: Screen viewing, wide questions
- **Pros**: Optimized for modern screen aspect ratios
- **Cons**: Non-standard size

## Recommendation:
For MCQ questions displayed on screens (especially mobile), **A4 Landscape** or **A5 Landscape** would be good choices:
- A4 Landscape: Good balance, standard size
- A5 Landscape: More compact, better for mobile, faster loading

The current custom wide format (10in × 7in) is also good for screen viewing.


