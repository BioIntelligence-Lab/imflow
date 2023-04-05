import unittest
import pandas as pd
from imflow import imflow

class TestImageLoad(unittest.TestCase):
  def test_image_file(self):
    df = pd.read_csv('./tests/data/binary_labels.csv')
    df['patientId'] += '.png'
    ds = imflow.image_dataset_from_csv(
      './tests/data/binary_labels.csv',
      'patientId',
      'T_0',
      image_dir = './tests/data/images/',
      label_mode = 'binary',
      color_mode = 'grayscale',
      batch_size = 32,
      image_size = (224,224),
      shuffle = False,
      seed = 1337
    )
    try:
      for X, _ in ds.take(1):
        self.assertEqual(X.numpy().shape, (32,224,224), 'Reshape failed')
    except:
      self.fail('Image did not load correctly')

  def test_dicom_file(self):
    df = pd.read_csv('./tests/data/binary_labels.csv')
    df['patientId'] += '.dcm'
    ds = imflow.image_dataset_from_csv(
      './tests/data/binary_labels.csv',
      'patientId',
      'T_0',
      image_dir = './tests/data/images/',
      label_mode = 'binary',
      color_mode = 'grayscale',
      batch_size = 32,
      image_size = (224,224),
      shuffle = False,
      seed = 1337
    )
    try:
      for X, _ in ds.take(1):
        self.assertEqual(X.numpy().shape, (32,224,224), 'Reshape failed')
    except:
      self.fail('Image did not load correctly')

if __name__ == '__main__':
  unittest.main()