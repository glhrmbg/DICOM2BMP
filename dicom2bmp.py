"""
DICOM to BMP Converter

A simple script to convert DICOM medical images of phantoms into
BMP for application in Monte Carlo simulations.

This script uses utility functions adapted from 'ykuo2' dicom2jpg project:
https://github.com/ykuo2/dicom2jpg
"""

from utils import _dicom_convertor

# Directories containing the input DICOM files and the directory for output BMP files
dicom_dir = "./DICOM_files"
bmp_dir = "./BMP_files"


# Function of dicom2jpg package to convert DICOM files from DICOM_files folder to BMP and store in BMP_files folder.
def dicom2bmp(origin, target_root=None, multiprocessing=True):
    return _dicom_convertor(origin, target_root, multiprocessing=multiprocessing)


if __name__ == '__main__':
    dicom2bmp(dicom_dir, bmp_dir)
