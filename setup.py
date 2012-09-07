import sys
#import os

VERSION = '1.0.0'
py_vers_tag = '-%s.%s' % sys.version_info[:2]

#test_dirs = ['functional_tests', 'unit_tests', os.path.join('doc','doc_tests'), 'nose']

if sys.version_info >= (3,):
    try:
        import setuptools #@UnusedImport
    except ImportError:
        from distribute_setup import use_setuptools
        use_setuptools()

    extra = {'use_2to3': True,
             #'test_dirs': test_dirs,
             #'test_build_dir': 'build/tests',
             'pyversion_patching': True,
             }
else:
    extra = {}

try:
    from setup3lib import setup
    from setuptools import find_packages
    addl_args = dict(
        zip_safe = False,
        packages = find_packages(exclude=['tests', 'tests.*']),
        entry_points = {
            'console_scripts': [
                'f5.install = f5test.macros.install:main',
                'f5.configurator = f5test.macros.confgen:main',
                'f5.keyswap = f5test.macros.keyswap:main',
                'f5.seleniumrc = f5test.macros.seleniumrc:main',
                'f5.irack = f5test.macros.irackprofile:main',
                'f5.ha = f5test.macros.ha:main',
                'f5.cloner = f5test.macros.cloner:main',
                'f5.ictester = f5test.macros.ictester:main',
                'f5.empytester = f5test.macros.empytester:main',
#                'f5.trafficgen = f5test.macros.trafficgen:main',
                'f5.trafficgen = f5test.macros.trafficgen2:main',
                'f5.webcert = f5test.macros.webcert:main',
                'f5.licensegen = f5test.macros.licensegen:main',
                'f5.loggen = f5test.macros.loggen:main',
                ],
            'nose.plugins.0.10': [
                'config = f5test.noseplugins.testconfig:TestConfig',
                'logcollect = f5test.noseplugins.logcollect:LogCollect',
                'testopia = f5test.noseplugins.testopia:Testopia',
                'email = f5test.noseplugins.email:Email',
                'bvtinfo = f5test.noseplugins.bvtinfo:BVTInfo',
                'irack = f5test.noseplugins.irack:IrackCheckout',
                'testtime = f5test.noseplugins.testtime:TestTime',
                ]
        },
    )
    addl_args.update(extra)

    # This is required by multiprocess plugin; on Windows, if
    # the launch script is not import-safe, spawned processes
    # will re-run it, resulting in an infinite loop.
    if sys.platform == 'win32':
        import re
        from setuptools.command.easy_install import easy_install

        def wrap_write_script(self, script_name, contents, *arg, **kwarg):
            bad_text = re.compile(
                "\n"
                "sys.exit\(\n"
                "   load_entry_point\(([^\)]+)\)\(\)\n"
                "\)\n")
            good_text = (
                "\n"
                "if __name__ == '__main__':\n"
                "    sys.exit(\n"
                r"        load_entry_point(\1)()\n"
                "    )\n"
                )
            contents = bad_text.sub(good_text, contents)
            return self._write_script(script_name, contents, *arg, **kwarg)
        easy_install._write_script = easy_install.write_script
        easy_install.write_script = wrap_write_script

except ImportError:
    from distutils.core import setup
    addl_args = dict(
        packages = ['f5test',
                    'f5test.commands',
                    'f5test.commands.icontrol',
                    'f5test.commands.icontrol.em',
                    'f5test.commands.shell',
                    'f5test.commands.shell.em',
                    'f5test.commands.testopia',
                    'f5test.commands.ui',
                    'f5test.commands.ui.em',
                    'f5test.commands.ui.bigip',
                    'f5test.macros',
                    'f5test.noseplugins',
                    'f5test.interfaces',
                    'f5test.interfaces.rest',
                    'f5test.interfaces.selenium',
                    'f5test.interfaces.ssh',
                    'f5test.interfaces.subprocess',
                    'f5test.interfaces.testopia',
                    'f5test.interfaces.icontrol',
                    'f5test.interfaces.icontrol.empython',
                    'f5test.interfaces.icontrol.empython.api',
                    'f5test.utils',
                    'f5test.utils.palb',
                    'f5test.utils.palb.getter',
                    'f5test.utils.parsers',
                    ],
        #scripts = ['bin/keyswap'],
    )

setup(
    name = 'f5test',
    version = VERSION,
    author = 'Ionut Turturica',
    author_email = 'i.turturica@f5.com',
    description = ('F5 Test Framework'),
    long_description = \
    """F5 Test Framework - A collection of libraries to help in testing F5 
    products.
    """,
    license = 'GNU LGPL',
    keywords = 'test unittest doctest automatic discovery',
    url = 'http://ionutdb01.mgmt.pdsea.f5net.com/dist',
    download_url = \
    'http://ionutdb01.mgmt.pdsea.f5net.com/dist/f5test-%s.tar.bz2' \
    % VERSION,
    package_dir={'f5test.noseplugins': 'f5test/noseplugins'},
    package_data = {'f5test.noseplugins': ['templates/*.tmpl'], 
                    'f5test.macros':      ['configs/*.yaml']},
    install_requires = [
        'paramiko',
        'SOAPpy',
#        'pycurl',
        'python-graph-core',
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
        'loggerglue'
        ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Testing'
        ],
    **addl_args
    )

