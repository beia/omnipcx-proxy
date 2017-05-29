#!/usr/bin/env python
from distutils.core import setup

setup(name='omnipcx',
    version='1.0',
    description='Proxy between OmniPCX and ONL',
    author='Vlad Wing',
    author_email='vlad.wing@gmail./com',
    url='https://github.com/vladwing/omnipcx',
    packages=['omnipcx', 'omnipcx.messages'],
    entry_points = {
        'console_scripts': ['proxy=omnipcx:main'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Python Software Foundation License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Communications :: Email',
        'Topic :: Office/Business',
        'Topic :: Software Development :: Bug Tracking',
    ],
)
