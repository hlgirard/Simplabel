from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(name='simplabel',
      version='0.1.0',
      description='Simple tool to manually label images in disctinct categories to build training datasets.',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/hlgirard/Simplabel',
      author='Henri-Louis Girard',
      author_email='hl.girard@gmail.com',
      license='GPLv3',
      packages=find_packages(),
      install_requires=[
          'pillow',
      ],
      scripts=[
          'bin/simplabel',
          'bin/flow_to_directory'
      ],
      zip_safe=False)