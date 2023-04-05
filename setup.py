from setuptools import setup, find_packages

setup(
    name = 'imflow',
    version = '0.1.0',    
    description = 'A better image dataset loader for TensorFlow.',
    url = 'https://github.com/UM2ii/intelligent_streaming',
    author = 'Pranav Kulkarni',
    author_email = 'pkulkarni@som.umaryland.edu',
    license = 'Apache License',
    packages = find_packages(),
    install_requires = [
      'tensorflow>=2.7',
      'tensorflow_io>=0.23',
      'numpy',
      'pandas'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires = ">=3.7",
    test_suite = 'tests'
)