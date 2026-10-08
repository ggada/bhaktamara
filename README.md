# Bhaktamara Stotra EPUB Generator

A Python script that generates a beautiful EPUB e-book of the **Bhaktamara Stotra**, one of the most revered hymns in Jainism, composed by Acharya Manatunga in the 6th century CE.

## About Bhaktamara Stotra

The hymn praises Rishabhanatha, the first Tirthankara of Jainism in this time cycle. Bhaktāmara Stotra was composed sometime in the Gupta or the post-Gupta period. Devotees believe that the verses of Bhaktāmara Stotra possess magical properties, and associate a mystical diagram (yantra) with each verse.

Some also believe in the following significance of different shlokas:

- **Shloka 4**: Protection from fear
- **Shloka 6**: Relief from diseases
- **Shloka 7**: Removal of obstacles
- **Shloka 11**: Gaining knowledge and wisdom
- **Shloka 18**: Relief from poverty
- **Shloka 48**: Spiritual liberation

This script creates an e-ink optimized EPUB containing all 48 verses with:
- Sanskrit text in Devanagari (as images) and transliteration
- English translations
- Beautiful illustrations for each shloka
- Special significance notes for key verses

## Features

- Valid EPUB 3 (passes epubcheck) with an NCX table of contents for older readers
- Color Sanskrit text and illustrations scaled for e-ink devices (75%)
- Tight, readable formatting optimized for digital reading
- Contents page listing every shloka by its opening line, with significance annotations
- Embedded images (no internet connection required)

## Setup

### Prerequisites

- [Conda](https://docs.conda.io/en/latest/miniconda.html) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

### Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd bhaktamara
```

2. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate bhaktamara
```

## Usage

### Generate the EPUB

```bash
python create_epub.py
```

The script will:
1. Fetch all 48 shloka pages from jainworld.com
2. Extract and process Sanskrit text, translations, and images
3. Generate `Bhaktamara_Stotra.epub` in the current directory

**Note**: The generation process takes 1-2 minutes as it respectfully fetches content with delays between requests.

### Direct Download

If you just want to read the e-book without generating it yourself, download the pre-generated EPUB:

**[Download Bhaktamara_Stotra.epub](Bhaktamara_Stotra.epub)**

Transfer this file to your e-reader (Kindle, Kobo, etc.) or open it with any EPUB reader app.

## Project Structure

```
bhaktamara/
├── create_epub.py          # Main script
├── environment.yml         # Conda dependencies
├── Bhaktamara_Stotra.epub  # Generated e-book
├── CLAUDE.md              # Developer documentation
└── README.md              # This file
```

## Troubleshooting

### Environment Issues
```bash
# Update existing environment
conda env update -f environment.yml --prune

# Recreate from scratch
conda deactivate
conda env remove -n bhaktamara
conda env create -f environment.yml
```

### Validation
To verify the generated EPUB is valid (requires [epubcheck](https://github.com/w3c/epubcheck)):
```bash
epubcheck Bhaktamara_Stotra.epub
```

## Credits

**Content Source**: All Sanskrit text, English translations, and images are sourced from [Jainworld.com](https://jainworld.com), a non-profit organization dedicated to promoting Jain philosophy, culture, and heritage. We are deeply grateful for their work in preserving and sharing these sacred texts.

**Original Author**: Acharya Manatunga (6th century CE)

**Technical Implementation**: This EPUB generation script processes and formats the content for modern e-readers while preserving the beauty and accuracy of the original material.

## License

This is a devotional project. The content belongs to the Jain community and is freely available for spiritual purposes. Please respect the sacred nature of these texts.

---

*Jai Jinendra* 🙏
