from setuptools import setup, find_packages, findall
try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    # 2.x
    from distutils.command.build_py import build_py

VERSION = '1.0.0'

media_files = [x.replace('f5test/web/', '') for x in findall('f5test/web/media/')]

addl_args = dict(
    zip_safe=False,
    cmdclass={'build_py': build_py},
    packages=find_packages(exclude=['tests', 'tests.*']),
    entry_points={
        'console_scripts': [
            'f5.install = f5test.macros.install:main',
            'f5.configurator = f5test.macros.tmosconf.placer:main',
            'f5.keyswap = f5test.macros.keyswap:main',
            'f5.seleniumrc = f5test.macros.seleniumrc:main',
            'f5.irack = f5test.macros.irackprofile:main',
            'f5.ha = f5test.macros.ha:main',
            'f5.cloner = f5test.macros.cloner:main',
            'f5.ictester = f5test.macros.ictester:main',
            'f5.empytester = f5test.macros.empytester:main',
            'f5.trafficgen = f5test.macros.trafficgen2:main',
            'f5.webcert = f5test.macros.webcert:main',
            'f5.licensegen = f5test.macros.licensegen:main',
            'f5.loggen = f5test.macros.loggen:main',
            ],
        'nose.plugins.0.10': [
            'randomize = f5test.noseplugins.randomize:Randomize',
            'config = f5test.noseplugins.testconfig:TestConfig',
            'testopia = f5test.noseplugins.testopia:Testopia',
            'irack = f5test.noseplugins.irack:IrackCheckout',
            'repeat = f5test.noseplugins.repeat:Repeat',
            'extender = f5test.noseplugins.extender:Extender',
            ]
    },
)

setup(
    name='f5test',
    version=VERSION,
    author='Ionut Turturica',
    author_email='i.turturica@f5.com',
    description='F5 Test Framework',
    long_description='F5 Test Framework - A collection of libraries to help '
                     'with testing F5 products.',
    license='GNU LGPL',
    keywords='test unittest doctest automatic discovery',
    url='http://ionutdb01.mgmt.pdsea.f5net.com/dist',
    download_url='http://ionutdb01.mgmt.pdsea.f5net.com/dist/f5test-%s.tar.bz2' % VERSION,
    package_dir={'f5test.noseplugins': 'f5test/noseplugins'},
    package_data={'f5test.utils.stage': ['templates/*.tmpl'],
                  'f5test.macros': ['configs/*.yaml'],
                  'f5test.web': media_files + ['views/*.tpl']},
    install_requires=[
        'paramiko',
        'SOAPpy',
#        'pycurl',
        'pyOpenSSL',
        'PyYAML',
        'pyparsing',
        'restkit',
        'selenium',
        'jinja2',
        'httpagentparser',
        'dnspython',
        'netaddr',
        'geventhttpclient',
        'pexpect',
        'blinker',
        'loggerglue',
        'pysnmp',
        'xmltodict',
        'boto',
        # Openstack
        'python-novaclient',
        'python-glanceclient',
        'python-neutronclient'
        ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Testing'
        ],
    **addl_args
    )
