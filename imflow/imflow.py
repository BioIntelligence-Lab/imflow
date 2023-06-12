# Copyright 2020 The TensorFlow Authors. All Rights Reserved.
#
# Modifications Copyright 2022 Pranav Kulkarni. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
'''ImFlow'''

import sys
import numpy as np
import pandas as pd
import tensorflow_io as tfio
import tensorflow.compat.v2 as tf
import nibabel as nib
import pydicom

from .utils import dataset_utils, image_utils

ALLOWLIST_FORMATS = ('.bmp', '.gif', '.jpeg', '.jpg', '.png', '.dcm')

def paths_and_labels_to_dataset(
  image_paths,
  image_size,
  num_channels,
  labels,
  label_mode,
  num_classes,
  interpolation,
  crop_to_aspect_ratio=False,
):
  '''Constructs a dataset of images and labels.'''
  path_ds = tf.data.Dataset.from_tensor_slices(image_paths)
  args = (image_size, num_channels, interpolation, crop_to_aspect_ratio)
  img_ds = path_ds.map(
    lambda x: load_image(x, *args), num_parallel_calls=tf.data.AUTOTUNE
  )
  if label_mode:
    label_ds = dataset_utils.labels_to_dataset(
      labels, label_mode, num_classes
    )
    img_ds = tf.data.Dataset.zip((img_ds, label_ds))
  return img_ds

def numpy_channels(x, num_channels):
  if x.ndim == 2:
    x = np.expand_dims(x, axis=-1)
    if num_channels == 3:
      x = np.concatenate((x,)*3, axis=-1)
    if num_channels == 4:
      x = np.concatenate((x,)*4, axis=-1)
    return x

def decode_npz_image(path, num_channels):
  x = np.load(path)['arr_0'].astype(np.float32)
  return numpy_channels(x, num_channels)
  
def decode_npy_image(path, num_channels):
  x = np.load(path).astype(np.float32)
  return numpy_channels(x, num_channels)

# def decode_nifti_image(path, num_channels):
#   x = nib.load(path).get_fdata().astype(np.float32)
#   return numpy_channels(x, num_channels)

# def decode_dicom_image(path, num_channels):
#   x = pydicom.dcmread(path).pixel_array.astype(np.float32)
#   return numpy_channels(x, num_channels)
      
def load_image(
  path, 
  image_size, 
  num_channels, 
  interpolation, 
  crop_to_aspect_ratio=False
):
  '''Load an image from a path and resize it.'''
  if tf.strings.regex_full_match(path, '.*\.dcm.*'):
    # TODO: Add support for Multiframe DICOM
    # TODO: Add support for creating 3D input from MRI/CT slices
    # Idea: Provide each MRI/CT as list of paths to slices in order
    img_bytes = tf.io.read_file(path)
    img = tfio.image.decode_dicom_image(img_bytes, scale='auto', dtype=tf.uint8)
    assert_op = tf.Assert(tf.math.equal(tf.shape(img)[0], 1), ['Multiframe DICOM files are not supported. Received Tensor with shape:', tf.shape(img)])
    with tf.control_dependencies([assert_op]):
      img = tf.squeeze(img, axis=0)
      if num_channels == 3:
        img = tf.concat((img, img, img), axis=-1) # changes from 2 to -1
      elif num_channels == 4:
        img = tf.concat((img, img, img, tf.math.multiply(tf.ones(tf.shape(img), dtype=tf.uint8), 255)), axis=-1)
      if crop_to_aspect_ratio:
        img = tf.image.resize_with_crop_or_pad(img, image_size[0], image_size[1], method=interpolation)
      else:
        img = tf.image.resize(img, image_size, method=interpolation)
      img.set_shape((image_size[0], image_size[1], num_channels))
      return img
  elif tf.strings.regex_full_match(path, '.*\.npz.*'):
    img= tf.numpy_function(decode_npz_image, [path, num_channels], tf.float32)
    if crop_to_aspect_ratio:
      img = tf.image.resize_with_crop_or_pad(img, image_size[0], image_size[1], method=interpolation)
    else:
      img = tf.image.resize_with_pad(img, image_size[0], image_size[1], method=interpolation)
    img.set_shape((image_size[0], image_size[1], num_channels))
    return img
  elif tf.strings.regex_full_match(path, '.*\.npy.*'):
    img= tf.numpy_function(decode_npy_image, [path, num_channels], tf.float32)
    if crop_to_aspect_ratio:
      img = tf.image.resize_with_crop_or_pad(img, image_size[0], image_size[1], method=interpolation)
    else:
      img = tf.image.resize_with_pad(img, image_size[0], image_size[1], method=interpolation)
    img.set_shape((image_size[0], image_size[1], num_channels))
    return img
  # elif tf.strings.regex_full_match(path, '.*\.nii.*'):
  #   img= tf.numpy_function(decode_nifti_image, [path, num_channels], tf.float32)
  #   if crop_to_aspect_ratio:
  #     img = tf.image.resize_with_crop_or_pad(img, image_size[0], image_size[1], method=interpolation)
  #   else:
  #     img = tf.image.resize_with_pad(img, image_size[0], image_size[1], method=interpolation)
  #   img.set_shape((image_size[0], image_size[1], num_channels))
  #   return img
  else:
    img_bytes = tf.io.read_file(path)
    img = tf.image.decode_image(
      img_bytes, channels=num_channels, expand_animations=False
    )
    if crop_to_aspect_ratio:
      img = tf.image.resize_with_crop_or_pad(img, image_size[0], image_size[1], method=interpolation)
    else:
      img = tf.image.resize(img, image_size, method=interpolation)
    img.set_shape((image_size[0], image_size[1], num_channels))
    return img

# TODO: Update doc
def image_dataset_from_directory(
  directory,
  labels='inferred',
  label_mode='int',
  class_names=None,
  color_mode='rgb',
  batch_size=32,
  image_size=(256, 256),
  shuffle=True,
  seed=None,
  validation_split=None,
  subset=None,
  interpolation='bilinear',
  follow_links=False,
  crop_to_aspect_ratio=False,
):
  '''Generates a `tf.data.Dataset` from image files in a directory.

  If your directory structure is:

  ```
  main_directory/
  ...class_a/
  ......a_image_1.jpg
  ......a_image_2.jpg
  ...class_b/
  ......b_image_1.jpg
  ......b_image_2.jpg
  ```

  Then calling `image_dataset_from_directory(main_directory,
  labels='inferred')` will return a `tf.data.Dataset` that yields batches of
  images from the subdirectories `class_a` and `class_b`, together with labels
  0 and 1 (0 corresponding to `class_a` and 1 corresponding to `class_b`).

  Supported image formats: jpeg, png, bmp, gif, dcm.
  Currently, `imflow` does not support 3D data. Animated gifs are truncated to the first frame and multi-frame DICOMs are not supported.

  Args:
    directory: Directory where the data is located.
      If `labels` is "inferred", it should contain
      subdirectories, each containing images for a class.
      Otherwise, the directory structure is ignored.
    labels: Either "inferred"
      (labels are generated from the directory structure),
      None (no labels),
      or a list/tuple of integer labels of the same size as the number of
      image files found in the directory. Labels should be sorted according
      to the alphanumeric order of the image file paths
      (obtained via `os.walk(directory)` in Python).
    label_mode: String describing the encoding of `labels`. Options are:
      - 'int': means that the labels are encoded as integers
        (e.g. for `sparse_categorical_crossentropy` loss).
      - 'categorical' means that the labels are
        encoded as a categorical vector
        (e.g. for `categorical_crossentropy` loss).
      - 'multi_label': means that the labels are encoded as a one hot vector (e.g. for `binary_crossentropy`). Note that this is different from `categorical`, which assumes every class is mutually exclusive.
      - 'binary': means that the labels (there can be only 2)
        are encoded as `float32` scalars with values 0 or 1
        (e.g. for `binary_crossentropy`).
      - 'custom': enables the use of custom ground truths for tasks beyond classification. Note that currently only integer-based labels are supported but this may change in the future to add support for segmentation masks, bounding boxes, etc.
      - None (no labels).
    class_names: Only valid if "labels" is "inferred". This is the explicit
      list of class names (must match names of subdirectories). Used
      to control the order of the classes
      (otherwise alphanumerical order is used).
    color_mode: One of "grayscale", "rgb", "rgba". Default: "rgb".
      Whether the images will be converted to
      have 1, 3, or 4 channels.
    batch_size: Size of the batches of data. Default: 32.
    If `None`, the data will not be batched
    (the dataset will yield individual samples).
    image_size: Size to resize images to after they are read from disk,
      specified as `(height, width)`. Defaults to `(256, 256)`.
      Since the pipeline processes batches of images that must all have
      the same size, this must be provided.
    shuffle: Whether to shuffle the data. Default: True.
      If set to False, sorts the data in alphanumeric order.
    seed: Optional random seed for shuffling and transformations.
    validation_split: Optional float between 0 and 1,
      fraction of data to reserve for validation.
    subset: Subset of the data to return.
      One of "training", "validation" or "both".
      Only used if `validation_split` is set.
      When `subset="both"`, the utility returns a tuple of two datasets
      (the training and validation datasets respectively).
    interpolation: String, the interpolation method used when resizing images.
    Defaults to `bilinear`. Supports `bilinear`, `nearest`, `bicubic`,
    `area`, `lanczos3`, `lanczos5`, `gaussian`, `mitchellcubic`.
    follow_links: Whether to visit subdirectories pointed to by symlinks.
      Defaults to False.
    crop_to_aspect_ratio: If True, resize the images without aspect
    ratio distortion. When the original aspect ratio differs from the target
    aspect ratio, the output image will be cropped so as to return the
    largest possible window in the image (of size `image_size`) that matches
    the target aspect ratio. By default (`crop_to_aspect_ratio=False`),
    aspect ratio may not be preserved.
    **kwargs: Legacy keyword arguments.

  Returns:
    A `tf.data.Dataset` object.
    - If `label_mode` is None, it yields `float32` tensors of shape
      `(batch_size, image_size[0], image_size[1], num_channels)`,
      encoding images (see below for rules regarding `num_channels`).
    - Otherwise, it yields a tuple `(images, labels)`, where `images`
      has shape `(batch_size, image_size[0], image_size[1], num_channels)`,
      and `labels` follows the format described below.

  Rules regarding labels format:
    - if `label_mode` is `int`, the labels are an `int32` tensor of shape
    `(batch_size,)`.
    - if `label_mode` is `binary`, the labels are a `float32` tensor of
    1s and 0s of shape `(batch_size, 1)`.
    - if `label_mode` is `categorical`, the labels are a `float32` tensor
    of shape `(batch_size, num_classes)`, representing a one-hot
    encoding of the class index.

  Rules regarding number of channels in the yielded images:
    - if `color_mode` is `grayscale`,
    there's 1 channel in the image tensors.
    - if `color_mode` is `rgb`,
    there are 3 channels in the image tensors.
    - if `color_mode` is `rgba`,
    there are 4 channels in the image tensors.
  '''
  if isinstance(labels, np.ndarray):
    labels = labels.tolist()
  if labels not in ('inferred', None):
    if not isinstance(labels, (list, tuple)):
      raise ValueError(
        '`labels` argument should be a list/tuple of integer labels, '
        'of the same size as the number of image files in the target '
        'directory. If you wish to infer the labels from the '
        'subdirectory '
        'names in the target directory, pass `labels="inferred"`. '
        'If you wish to get a dataset that only contains images '
        f'(no labels), pass `labels=None`. Received: labels={labels}'
      )
    if class_names:
      raise ValueError(
        'You can only pass `class_names` if '
        f'`labels="inferred"`. Received: labels={labels}, and '
        f'class_names={class_names}'
      )
  if label_mode not in {'int', 'categorical', 'multi_class', 'multi_label', 'binary', None}:
    raise ValueError(
      '`label_mode` argument must be one of "int", '
      '"categorical", "multi_class", "multi_label", "binary", '
      f'or None. Received: label_mode={label_mode}'
    )
  if labels is None or label_mode is None:
    labels = None
    label_mode = None

  if seed is None:
    seed = np.random.randint(1e6)

  image_paths, labels = dataset_utils.index_directory(
    directory,
    labels,
    label_mode,
    formats=ALLOWLIST_FORMATS,
    class_names=class_names,
    shuffle=shuffle,
    seed=seed,
    follow_links=follow_links,
  )

  return image_dataset_from_paths_and_labels(image_paths, labels, label_mode, color_mode, batch_size, image_size, shuffle, seed, validation_split, subset, interpolation, crop_to_aspect_ratio)

# TODO: Add doc
def image_dataset_from_csv(
  csv_path,
  path_col,
  label_col,
  image_dir='',
  label_mode='int',
  color_mode='rgb',
  batch_size=32,
  image_size=(256, 256),
  shuffle=True,
  seed=None,
  validation_split=None,
  subset=None,
  interpolation='bilinear',
  crop_to_aspect_ratio=False
):
  df = pd.read_csv(csv_path)
  return image_dataset_from_dataframe(df, path_col, label_col, image_dir, label_mode, color_mode, batch_size, image_size, shuffle, seed, validation_split, subset, interpolation, crop_to_aspect_ratio)

# TODO: Add doc
def image_dataset_from_dataframe(
  df,
  path_col,
  label_col,
  image_dir='',
  label_mode='int',
  color_mode='rgb',
  batch_size=32,
  image_size=(256, 256),
  shuffle=True,
  seed=None,
  validation_split=None,
  subset=None,
  interpolation='bilinear',
  crop_to_aspect_ratio=False
):
  if not isinstance(path_col, str):
    raise ValueError(
      '`label_mode` argument must be one of "int", '
      '"categorical", "multi_label", "binary", "custom", '
      f'or None. Received: label_mode={label_mode}'
    )
  if not isinstance(label_col, (str, list)):
    raise ValueError(
      '`label_mode` argument must be one of "int", '
      '"categorical", "multi_label", "binary", "custom", '
      f'or None. Received: label_mode={label_mode}'
    )
  image_dir = image_dir + '/' if image_dir != '' and image_dir[-1] != '/' else image_dir
  image_paths = (image_dir + df[path_col].values).tolist()
  labels = df[label_col].values.tolist()
  return image_dataset_from_paths_and_labels(image_paths, labels, label_mode, color_mode, batch_size, image_size, shuffle, seed, validation_split, subset, interpolation, crop_to_aspect_ratio)

# TODO: Update doc
def image_dataset_from_paths_and_labels(
  image_paths,
  labels,
  label_mode='int',
  color_mode='rgb',
  batch_size=32,
  image_size=(256, 256),
  shuffle=True,
  seed=None,
  validation_split=None,
  subset=None,
  interpolation='bilinear',
  crop_to_aspect_ratio=False
):
  '''Generates a `tf.data.Dataset` from image files in a directory.

  If your directory structure is:

  ```
  main_directory/
  ...class_a/
  ......a_image_1.jpg
  ......a_image_2.jpg
  ...class_b/
  ......b_image_1.jpg
  ......b_image_2.jpg
  ```

  Then calling `image_dataset_from_directory(main_directory,
  labels='inferred')` will return a `tf.data.Dataset` that yields batches of
  images from the subdirectories `class_a` and `class_b`, together with labels
  0 and 1 (0 corresponding to `class_a` and 1 corresponding to `class_b`).

  Supported image formats: jpeg, png, bmp, gif.
  Animated gifs are truncated to the first frame.

  Args:
    directory: Directory where the data is located.
      If `labels` is "inferred", it should contain
      subdirectories, each containing images for a class.
      Otherwise, the directory structure is ignored.
    labels: Either "inferred"
      (labels are generated from the directory structure),
      None (no labels),
      or a list/tuple of integer labels of the same size as the number of
      image files found in the directory. Labels should be sorted according
      to the alphanumeric order of the image file paths
      (obtained via `os.walk(directory)` in Python).
    label_mode: String describing the encoding of `labels`. Options are:
      - 'int': means that the labels are encoded as integers
        (e.g. for `sparse_categorical_crossentropy` loss).
      - 'categorical' means that the labels are
        encoded as a categorical vector
        (e.g. for `categorical_crossentropy` loss).
      - 'binary' means that the labels (there can be only 2)
        are encoded as `float32` scalars with values 0 or 1
        (e.g. for `binary_crossentropy`).
      - None (no labels).
    class_names: Only valid if "labels" is "inferred". This is the explicit
      list of class names (must match names of subdirectories). Used
      to control the order of the classes
      (otherwise alphanumerical order is used).
    color_mode: One of "grayscale", "rgb", "rgba". Default: "rgb".
      Whether the images will be converted to
      have 1, 3, or 4 channels.
    batch_size: Size of the batches of data. Default: 32.
    If `None`, the data will not be batched
    (the dataset will yield individual samples).
    image_size: Size to resize images to after they are read from disk,
      specified as `(height, width)`. Defaults to `(256, 256)`.
      Since the pipeline processes batches of images that must all have
      the same size, this must be provided.
    shuffle: Whether to shuffle the data. Default: True.
      If set to False, sorts the data in alphanumeric order.
    seed: Optional random seed for shuffling and transformations.
    validation_split: Optional float between 0 and 1,
      fraction of data to reserve for validation.
    subset: Subset of the data to return.
      One of "training", "validation" or "both".
      Only used if `validation_split` is set.
      When `subset="both"`, the utility returns a tuple of two datasets
      (the training and validation datasets respectively).
    interpolation: String, the interpolation method used when resizing images.
    Defaults to `bilinear`. Supports `bilinear`, `nearest`, `bicubic`,
    `area`, `lanczos3`, `lanczos5`, `gaussian`, `mitchellcubic`.
    follow_links: Whether to visit subdirectories pointed to by symlinks.
      Defaults to False.
    crop_to_aspect_ratio: If True, resize the images without aspect
    ratio distortion. When the original aspect ratio differs from the target
    aspect ratio, the output image will be cropped so as to return the
    largest possible window in the image (of size `image_size`) that matches
    the target aspect ratio. By default (`crop_to_aspect_ratio=False`),
    aspect ratio may not be preserved.
    **kwargs: Legacy keyword arguments.

  Returns:
    A `tf.data.Dataset` object.
    - If `label_mode` is None, it yields `float32` tensors of shape
      `(batch_size, image_size[0], image_size[1], num_channels)`,
      encoding images (see below for rules regarding `num_channels`).
    - Otherwise, it yields a tuple `(images, labels)`, where `images`
      has shape `(batch_size, image_size[0], image_size[1], num_channels)`,
      and `labels` follows the format described below.

  Rules regarding labels format:
    - if `label_mode` is `int`, the labels are an `int32` tensor of shape
    `(batch_size,)`.
    - if `label_mode` is `binary`, the labels are a `float32` tensor of
    1s and 0s of shape `(batch_size, 1)`.
    - if `label_mode` is `categorical`, the labels are a `float32` tensor
    of shape `(batch_size, num_classes)`, representing a one-hot
    encoding of the class index.

  Rules regarding number of channels in the yielded images:
    - if `color_mode` is `grayscale`,
    there's 1 channel in the image tensors.
    - if `color_mode` is `rgb`,
    there are 3 channels in the image tensors.
    - if `color_mode` is `rgba`,
    there are 4 channels in the image tensors.
  '''
  if isinstance(labels, np.ndarray):
    labels = labels.tolist()
  if labels != None and not isinstance(labels, (list, tuple)):
    raise ValueError(
      f'`labels` argument should be a list/tuple of integer labels, of the same size as the number of image files in the target directory. If you wish to infer the labels from the subdirectory names in the target directory, pass `labels="inferred"`. If you wish to get a dataset that only contains images (no labels), pass `labels=None`. Received: labels={labels}'
    )
  if label_mode not in {'int', 'categorical', 'multi_label', 'binary', None}:
    raise ValueError(
      f'`label_mode` argument must be one of "int", "categorical", "multi_label", "binary", "custom", or None. Received: label_mode={label_mode}'
    )
  if labels is None or label_mode is None:
    labels = None
    label_mode = None
  if color_mode == 'rgb':
    num_channels = 3
  elif color_mode == 'rgba':
    num_channels = 4
  elif color_mode == 'grayscale':
    num_channels = 1
  else:
    raise ValueError(
      f'`color_mode` must be one of {"rgb", "rgba", "grayscale"}. Received: color_mode={color_mode}'
    )
  
  interpolation = image_utils.get_interpolation(interpolation)
  dataset_utils.check_validation_split_arg(
    validation_split, subset, shuffle, seed
  )

  if seed is None:
    seed = np.random.randint(1e6)

  # Temporarily convert labels to ndarray for quick mafs!
  labels = np.array(labels)
  # Ensure `labels` match format for each `label_mode`
  if label_mode in ('int', 'categorical') and labels.ndim > 1:
    raise ValueError(
      f'When `label_mode` is "int" or "categorical", input `labels` must have shape (samples,)'
    ) 
  if label_mode == 'binary':
    if labels.ndim < 2:
      labels = np.expand_dims(labels, axis=-1)
    if len(np.unique(labels)) != 2:
      raise ValueError(
        f'When passing `label_mode="binary"`, there must be exactly 2 classes'
      )
    labels = labels.astype(float)
  if label_mode in ('multi_class', 'multi_label'):
    if labels.ndim < 2:
      raise ValueError(
        f'When `label_mode` is "multi_class" or "multi_label", `labels` must have shape (samples, num_classes)'
      )
    if labels.shape[1] < 2:
      raise ValueError(
        f'Only a single class/label found, please use `label_mode="binary"` instead!'
      )
    if label_mode == 'multi_class' and np.max(np.sum(labels, axis=1)) > 1:
      raise ValueError(
        f'More than one class assigned to label, please use `label_mode="multi_label"` instead!'
      )
  # Calculate `num_classes` from labels
  if label_mode == 'binary':
    num_classes = 2
  if label_mode in ('int', 'categorical'):
    num_classes = np.max(labels) + 1
  if label_mode == 'multi_class':
    num_classes = labels.shape[1]
  if label_mode == 'multi_label':
    num_classes = labels.shape[1] + 1
  # Convert back to list
  labels = labels.tolist()

  if subset == 'both':
    (
      image_paths_train,
      labels_train,
    ) = dataset_utils.get_training_or_validation_split(
      image_paths, labels, validation_split, 'training'
    )
    (
      image_paths_val,
      labels_val,
    ) = dataset_utils.get_training_or_validation_split(
      image_paths, labels, validation_split, 'validation'
    )
    if not image_paths_train:
      raise ValueError(
        f'No training images found in directory. '
        f'Allowed formats: {ALLOWLIST_FORMATS}'
      )
    if not image_paths_val:
      raise ValueError(
        f'No validation images found in directory. '
        f'Allowed formats: {ALLOWLIST_FORMATS}'
      )
    train_dataset = paths_and_labels_to_dataset(
      image_paths=image_paths_train,
      image_size=image_size,
      num_channels=num_channels,
      labels=labels_train,
      label_mode=label_mode,
      num_classes=num_classes,
      interpolation=interpolation,
      crop_to_aspect_ratio=crop_to_aspect_ratio,
    )
    val_dataset = paths_and_labels_to_dataset(
      image_paths=image_paths_val,
      image_size=image_size,
      num_channels=num_channels,
      labels=labels_val,
      label_mode=label_mode,
      num_classes=num_classes,
      interpolation=interpolation,
      crop_to_aspect_ratio=crop_to_aspect_ratio,
    )
    train_dataset = train_dataset.prefetch(tf.data.AUTOTUNE)
    val_dataset = val_dataset.prefetch(tf.data.AUTOTUNE)
    if batch_size is not None:
      if shuffle:
        # Shuffle locally at each iteration
        train_dataset = train_dataset.shuffle(
          buffer_size=batch_size * 8, seed=seed
        )
      train_dataset = train_dataset.batch(batch_size)
      val_dataset = val_dataset.batch(batch_size)
    else:
      if shuffle:
        train_dataset = train_dataset.shuffle(
          buffer_size=1024, seed=seed
        )

    # Include file paths for images as attribute.
    train_dataset.file_paths = image_paths_train
    val_dataset.file_paths = image_paths_val
    dataset = [train_dataset, val_dataset]
  else:
    image_paths, labels = dataset_utils.get_training_or_validation_split(
      image_paths, labels, validation_split, subset
    )
    if not image_paths:
      raise ValueError(
        f'No images found in directory. '
        f'Allowed formats: {ALLOWLIST_FORMATS}'
      )

    dataset = paths_and_labels_to_dataset(
      image_paths=image_paths,
      image_size=image_size,
      num_channels=num_channels,
      labels=labels,
      label_mode=label_mode,
      num_classes=num_classes,
      interpolation=interpolation,
      crop_to_aspect_ratio=crop_to_aspect_ratio,
    )
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    if batch_size is not None:
      if shuffle:
        # Shuffle locally at each iteration
        dataset = dataset.shuffle(
          buffer_size=batch_size * 8, seed=seed)
      dataset = dataset.batch(batch_size)
    else:
      if shuffle:
        dataset = dataset.shuffle(buffer_size=1024, seed=seed)

    # Include file paths for images as attribute.
    dataset.file_paths = image_paths
  return dataset
