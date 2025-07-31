## DICOM to BMP Converter

Convert DICOM phantom images to BMP format for the construction of new phantoms to be used in Monte Carlo simulations.

### Overview
This tool simplifies the conversion of DICOM medical images to BMP format, specifically designed for researchers working with phantom construction for Monte Carlo radiation transport simulations. The converter maintains proper medical image processing standards while providing a streamlined workflow for simulation preparation.

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install pydicom opencv-python numpy
   ```

2. **Place your DICOM files** in `./DICOM_files/` folder

3. **Run:**
   ```bash
   python dicom2bmp.py
   ```

4. **Output:** BMP files will be saved in `./BMP_files/` folder

### Credits

This project is based on [dicom2jpg](https://github.com/ykuo2/dicom2jpg) by ykuo2. 
Core DICOM processing functions adapted with permission under MIT License.
Copyright (c) 2022 ykuo2
