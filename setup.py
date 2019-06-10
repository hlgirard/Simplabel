'''Setuptools configuration for Simplabel'''

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(name='simplabel',
      version='0.1.5',
      description='Simple tool to manually label images in disctinct categories.',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/hlgirard/Simplabel',
      author='Henri-Louis Girard',
      author_email='hl.girard@gmail.com',
      license='GPLv3',
      packages=find_packages(exclude=["tests.*", "tests"]),
      install_requires=[
          'pillow>=6.0.0',
      ],
      entry_points={
          'console_scripts': [
              'simplabel = simplabel.simplabel:main',
              'flow_to_directory = simplabel.flow_to_directory:main',
          ],
      },
      zip_safe=False)
