from setuptools import setup, find_packages
import sys, os

version = '0.2.2'

setup(name='py-natpmp',
      version=version,
      description="Python classes for interacting with NAT-PMP v0",
      long_description="""\
Provides functions to interact with NAT-PMP gateways implementing version 0 of the NAT-PMP draft specification.""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='NAT-PMP NAT networking port port_forwarding port_mapping AirPort Apple',
      author='Yiming Liu',
      author_email='yiming@yimingliu.com',
      url='http://yimingliu.com',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points={'console_scripts': [
            'natpmp-client.py = natpmp.natpmp_client:main',
            ],}
      )
