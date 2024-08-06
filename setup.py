from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='anker-solix-api-2',
      version='2.0.0.1',
      description='API for the Anker Solix Solarbank',
      url='https://github.com/r09491/anker-solix-api-2.git',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          'solarbank_monitor.py',
          'energy_csv.py',
          'export_system.py',
          'test_api.py',
          'set_home_load.py',
      ],
      packages=[
          'anker_solix_api',
      ],
      install_requires=[
          'cryptography',
          'aiohttp',
          'aiofiles',
      ],
      zip_safe=False)
