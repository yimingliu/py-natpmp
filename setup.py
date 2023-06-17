from setuptools import setup, find_packages
import sys, os

version = '0.2.5'

setup(name='py-natpmp',
      version=version,
      description="Python classes for interacting with NAT-PMP v0",
      long_description="""Provides functions to interact with NAT-PMP gateways implementing version 0 of the NAT-PMP draft specification.""",
      keywords='NAT-PMP NAT networking port port_forwarding port_mapping AirPort Apple',
      author='Yiming Liu',
      author_email='yliu@ischool.berkeley.edu',
      url='https://github.com/yimingliu/py-natpmp',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          
      ],
      classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 4 - Beta',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',

    # Pick your license as you wish (should match "license" above)
     'License :: OSI Approved :: BSD License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 2.7',
    'Topic :: System :: Networking',
    ],
      entry_points={'console_scripts': [
            'natpmp-client.py = natpmp.natpmp_client:main',
            ],}
)
