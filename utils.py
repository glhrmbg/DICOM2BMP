"""
Utility functions for DICOM to BMP conversion
Adapted from dicom2jpg by ykuo2: https://github.com/ykuo2/dicom2jpg

This file contains only the essential functions for converting DICOM
image files to BMP, with the purpose of converting phantom images for
application in Monte Carlo simulations.
"""

import pydicom
from pydicom.pixel_data_handlers.util import apply_voi_lut, apply_modality_lut
import cv2
import numpy as np
from pathlib import Path
import os
import concurrent.futures


def _is_unsupported(ds):
    # Exclude unsupported SOP classes by UID
    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.104.1':
        return 'Encapsulated PDF Storage'
    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.88.59':
        return 'Key Object Selection Document'
    else:
        return False


def _pixel_process(ds, pixel_array):
    # Step 1: Modality LUT (Rescale slope/intercept)
    if 'RescaleSlope' in ds and 'RescaleIntercept' in ds:
        rescale_slope = float(ds.RescaleSlope)
        rescale_intercept = float(ds.RescaleIntercept)
        pixel_array = pixel_array * rescale_slope + rescale_intercept
    else:
        pixel_array = apply_modality_lut(pixel_array, ds)

    # Step 2: VOI LUT (Window/Level)
    if 'VOILUTFunction' in ds and ds.VOILUTFunction == 'SIGMOID':
        pixel_array = apply_voi_lut(pixel_array, ds)
    elif 'WindowCenter' in ds and 'WindowWidth' in ds:
        window_center = ds.WindowCenter
        window_width = ds.WindowWidth

        # Handle multi-value fields
        if type(window_center) == pydicom.multival.MultiValue:
            window_center = float(window_center[0])
        else:
            window_center = float(window_center)
        if type(window_width) == pydicom.multival.MultiValue:
            window_width = float(window_width[0])
        else:
            window_width = float(window_width)

        pixel_array = _get_LUT_value_LINEAR_EXACT(pixel_array, window_width, window_center)
    else:
        pixel_array = apply_voi_lut(pixel_array, ds)

    # Step 3: Presentation LUT - normalize to 8 bit
    pixel_array = ((pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min())) * 255.0

    # Handle MONOCHROME1 (invert for X-rays, etc.)
    if 'PhotometricInterpretation' in ds and ds.PhotometricInterpretation == "MONOCHROME1":
        pixel_array = np.max(pixel_array) - pixel_array

    return pixel_array.astype('uint8')


def _get_LUT_value_LINEAR_EXACT(data, window, level):
    data_min = data.min()
    data_max = data.max()
    data_range = data_max - data_min

    data = np.piecewise(data,
                        [data <= (level - (window) / 2),
                         data > (level + (window) / 2)],
                        [data_min, data_max,
                         lambda data: ((data - level + window / 2) / window * data_range) + data_min])
    return data


def _ds_to_file(file_path, target_root):
    try:
        # Read DICOM file
        ds = pydicom.dcmread(file_path, force=True)

        # Check if supported
        is_unsupported = _is_unsupported(ds)
        if is_unsupported:
            return f'{file_path} cannot be converted.\n{is_unsupported} is currently not supported'

        # Load pixel array
        pixel_array = ds.pixel_array.astype(float)

        # Check for multiframe (not supported in this simple version)
        if len(pixel_array.shape) == 3 and pixel_array.shape[2] != 3:
            return f'{file_path} cannot be converted.\nMultiframe images are currently not supported'

        # Process pixel data
        pixel_array = _pixel_process(ds, pixel_array)

        # Handle color images (convert RGB to BGR for OpenCV)
        if 'PhotometricInterpretation' in ds and ds.PhotometricInterpretation in \
                ['YBR_RCT', 'RGB', 'YBR_ICT', 'YBR_PARTIAL_420', 'YBR_FULL_422', 'YBR_FULL', 'PALETTE COLOR']:
            pixel_array[:, :, [0, 2]] = pixel_array[:, :, [2, 0]]

        # Generate output file path
        full_export_fp_fn = _get_export_file_path(ds, file_path, target_root)

        # Create output directory
        Path.mkdir(full_export_fp_fn.parent, exist_ok=True, parents=True)

        # Write BMP file
        cv2.imwrite(str(full_export_fp_fn), pixel_array)

        return True

    except Exception as e:
        return f'Error converting {file_path}: {str(e)}'


def _get_export_file_path(ds, file_path, target_root):
    # Get metadata for filename
    try:
        series_number = ds.SeriesNumber
    except:
        series_number = 'Ser'
    try:
        instance_number = ds.InstanceNumber
    except:
        instance_number = 'Ins'

    # Create filename: SeriesNumber_InstanceNumber.bmp
    filename = f"{series_number}_{instance_number}.bmp"
    full_export_fp_fn = target_root / Path(filename)

    return full_export_fp_fn


def _get_root_get_dicom_file_list(origin_input, target_root):
    # Handle different input types
    if isinstance(origin_input, list) or isinstance(origin_input, tuple):
        origin_list = [Path(ori) for ori in origin_input]
    else:
        origin_list = [Path(origin_input)]

    dicom_file_list = []

    # Check existence and collect DICOM files
    for origin in origin_list:
        if not origin.exists():
            raise OSError(f"File or folder '{origin}' does not exist")

        if origin.is_file():
            if origin.suffix.lower() != '.dcm':
                raise Exception('Input file type should be a DICOM file')
            else:
                dicom_file_list.append(origin)
        elif origin.is_dir():
            # Find all .dcm files in directory and subdirectories
            for root, sub_f, files in os.walk(origin):
                for f in files:
                    if f.lower().endswith('.dcm'):
                        file_path_dcm = Path(root) / Path(f)
                        dicom_file_list.append(file_path_dcm)

    # Sort file list
    dicom_file_list.sort()

    # Set target root directory
    if target_root is None:
        if isinstance(origin_input, list) or isinstance(origin_input, tuple):
            root_folder = Path(origin_input[0]).parent
        else:
            root_folder = Path(origin_input).parent
    else:
        root_folder = Path(target_root)

    return root_folder, dicom_file_list


def _dicom_convertor(origin, target_root=None, multiprocessing=True):
    # Get target directory and list of DICOM files
    target_root, dicom_file_list = _get_root_get_dicom_file_list(origin, target_root)

    if not dicom_file_list:
        print("No DICOM files found!")
        return False

    print(f"Found {len(dicom_file_list)} DICOM files to convert...")

    # Process files
    if multiprocessing and len(dicom_file_list) > 1:
        # Use parallel processing for multiple files
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(_ds_to_file, file_path, target_root)
                       for file_path in dicom_file_list]
            results = [future.result() for future in futures]
        print("DICOM images converted to BMP successfully!")
    else:
        # Sequential processing
        results = [_ds_to_file(file_path, target_root) for file_path in dicom_file_list]

    # Count successful conversions
    successful = sum(1 for result in results if result is True)
    failed = len(results) - successful

    if failed > 0:
        print(f"Conversion completed: {successful} successful, {failed} failed")
        # Print error messages
        for result in results:
            if result is not True:
                print(f"  - {result}")
    else:
        print(f"All {successful} files converted successfully!")

    return successful > 0