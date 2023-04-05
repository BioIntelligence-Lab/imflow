# ImFlow

## What is ImFlow?

A better image dataset loader for TensorFlow.

ImFlow is an open source Python library for working with large-scale medical imaging datasets in TensorFlow. It extends TensorFlow's capability for dynamically loading imaging data by providing a quick interface for creating `tf.Dataset` objects from dataframes, CSV files, and manually. 

## Getting Started

ImFlow is currently not available through `pip`, but you can manually install it.

### Manual Installation

You can manually install ImFlow as follows:

```bash
$ git clone https://github.com/UM2ii/imflow
$ pip install imflow/
```

## Documentation

### `imflow.image_dataset_from_directory`

### `imflow.image_dataset_from_csv`

### `imflow.image_dataset_from_dataframe`

### `imflow.image_dataset_from_paths_and_labels`

## Roadmap

We are still working on expanding the capabilities of ImFlow. Here's a quick look at what to expect from future versions of ImFlow!

- Complete documentation and usage with examples and tests
- Built-in data preprocessing and augmentation pipelines (with support for custom pipelines)
- Extended support for DICOM and NifTI file formats
- Support for loading bounding boxes and segmentation masks as labels
- Support for 3D imaging data