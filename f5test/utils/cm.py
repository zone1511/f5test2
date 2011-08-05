"""Find files needed for BIGIP installation.

This module allows you to find the file location of a
BIGIP ISO image based on the value of various keys.

There are two high level functions available: L{released_isofile}
and L{isofile}. Here are examples showing their
basic usage::

    >>> # Using released_isofile
    >>> findiso.released_isofile('10.0.0')
    '/build/bigip/v10.0.0/dist/release/BIGIP-10.0.0.5401.0.iso'
    >>> findiso.released_isofile('10.0.0', 'hf1')
    '/build/bigip/v10.0.0-hf1/dist/release/Hotfix-BIGIP-10.0.0-5460.0-HF1.iso'
    >>> findiso.released_isofile('9.4.6')
    '/build/bigip/v9.4.6/dist/release/BIGIP-9.4.6.401.0.iso'
    >>> findiso.released_isofile('1.1.1')
    Traceback (most recent call last):
        (traceback omitted)
    findiso.IsoNotFoundError: \
            Could not find an ISO that matches: identifier: 1.1.1

    >>> # Using isofile
    >>> findiso.isofile('solstice')
    '/build/bigip/project/solstice/daily/current/BIGIP-11.0.0.6216.0.iso'
    >>> findiso.isofile('10.2.2')
    '/build/bigip/v10.2.2/daily/current/BIGIP-10.2.2.525.0.iso'
    >>> findiso.isofile('parkcity', '5354.0')
    '/build/bigip/project/parkcity/daily/build5354.0/BIGIP-10.0.0.5354.0.iso'
    >>> findiso.isofile('10.0.0', '5399.0')
    '/build/bigip/v10.0.0/daily/build5399.0/BIGIP-10.0.0.5399.0.iso'
    >>> findiso.isofile('10.0.0', '5459.0', 'hf2')
    '/build/bigip/v10.0.0-hf2/daily/build5459.0/Hotfix-BIGIP-10.0.0-5459.0-HF2.iso'
    >>> findiso.isofile('fakeproject', '100.0')
    Traceback (most recent call last):
        (traceback omitted)
    findiso.IsoNotFoundError: \
            Could not find an ISO that matches: identifier: fakeproject build: 100.0

"""
import os
import re
from itertools import ifilter
from xml.etree.ElementTree import fromstring
from .version import Version, Product
from ..base import Options
from ..interfaces.subprocess import ShellInterface

ROOT_PATH = '/build'
BIGIP = Product.BIGIP


class FileNotFoundError(Exception):
    pass

class IsoNotFoundError(FileNotFoundError):
    pass

class MD5NotFoundError(FileNotFoundError):
    pass

class OVANotFoundError(FileNotFoundError):
    pass



def is_version_string(string):
    version_regex = re.compile(r'^\s*\d+\.\d+\.\d+\s*$')
    
    if version_regex.search(string):
        return True
    else:
        return False

def is_project_string(string):
    project_regex = re.compile(r'^\s*[a-zA-Z]+')
    
    if project_regex.search(string):
        return True
    else:
        return False

def md5_file_for(filename):
    """Find the md5 associated with the specified iso filename.

    This essentially tries two recipes in this order:

        - add ".md5" to the filename.
        - replace the C{filename} extension with .md5.

    @return: The path to the md5 file associated with the filename.
    @raise MD5NotFoundError
    """
    try:
        directory_contents = os.listdir(os.path.dirname(filename))
    except OSError, e:
        raise MD5NotFoundError('Could not find md5 file for file "%s" '
                               'because: %s' % (filename, e))
    filename_with_md5_added = filename + '.md5'
    filename_with_no_extension = os.path.splitext(filename)[0]
    filename_with_md5_extension = filename_with_no_extension + '.md5'
    possibles = [filename_with_md5_added, filename_with_md5_extension]
    for potential_md5_file in possibles:
        if os.path.basename(potential_md5_file) in directory_contents:
            return potential_md5_file
    raise MD5NotFoundError("Could not find md5 file for: %s"
                           % filename)


def released_isofile(identifier, hotfix=None, product=BIGIP):
    """Return full path to an ISO file for a released BIGIP version.

    @param identifier: The version string.
    @param hotfix: The hotfix identifier string, ie 'hf1'
    @param product: A string containing one of the L{SUPPORTED_PRODUCTS}.
    @raise IsoNotFoundError: If no ISO could be found that matches the
                             given parameters.
    """
    finder = create_released_finder(identifier, hotfix, product=product)
    return finder.find_file()


def create_released_finder(identifier, hotfix=None, product=BIGIP):
    if not is_version_string(identifier):
        raise ValueError("%s is not a version string." % identifier)
    if hotfix is None:
        finder = ReleasedVersionFinder(identifier=identifier, product=product)
    else:
        finder = ReleasedHotfixFinder(identifier=identifier, hotfix=hotfix,
                                      product=product)
    return finder


def isofile(identifier, build=None, hotfix=None, product=BIGIP, root=ROOT_PATH):
    """Return the ISO file location associated with identifier and build.

    @param identifier: Either the project or the version string.
    @param build: The build string, ie '5354.0'
    @param hotfix: The hotfix identifier string, ie 'hf1'
    @param product: A string containing one of the L{SUPPORTED_PRODUCTS}.
    @raise IsoNotFoundError: If no ISO could be found that matches the
                             given parameters.

    """
    if build and not '.' in build:
        build = '%s.0' % build
    finder = create_finder(identifier, build, hotfix, product, root)
    return finder.find_file()


def ovafile(identifier, build=None, hotfix=None, product=BIGIP, disk='scsi'):
    """Return the OVA file location associated with identifier and build.

    @param identifier: Either the project or the version string.
    @param build: The build string, ie '5354.0'
    @param hotfix: The hotfix identifier string, ie 'hf1'
    @param product: A string containing one of the L{SUPPORTED_PRODUCTS}.
    @param disk: The disk type ("scsi" or "ide").

    @return: The path to the ova file associated with the filename.

    @raise OVANotFoundError: If the OVA file can't be located.
    """
    try:
        iso = isofile(identifier, build, hotfix, product=product)
    except IsoNotFoundError, e:
        raise OVANotFoundError("Could not find ova file due to an error "
                               "locating the corresonding iso: %s" % e)

    dirname, filename = os.path.split(iso)
    base_filename = os.path.splitext(filename)[0]

    potential_filenames = ['%s-%s.ova' % (base_filename, disk.lower())]
    if disk.lower() == 'scsi':
        potential_filenames.append('%s.ova' % (base_filename))
    for potential_filename in potential_filenames:
        ova_path = os.path.join(dirname, 'VM', potential_filename)
        if os.path.exists(ova_path):
            return ova_path
    raise OVANotFoundError("Could not find ova file for: %s" % filename)


def create_finder(identifier, build, hotfix=None, product=BIGIP, root=ROOT_PATH):
    common_kwargs = dict(identifier=identifier, build=build,
                         product=product, root=root)

    if is_version_string(identifier) and hotfix is None:
        finder = VersionFinder(**common_kwargs)
    elif is_project_string(identifier) and hotfix is None:
        finder = ProjectFinder(**common_kwargs)
    elif is_version_string(identifier) and hotfix is not None:
        finder = HotfixFinder(hotfix=hotfix, **common_kwargs)
    else:
        if hotfix is not None:
            errmsg = ("invalid combination of project %s and hotfix %s"
                                % (identifier, hotfix))
        else:
            errmsg = "%s is not a project or version" % identifier
        raise ValueError(errmsg)
    return finder

def iso_metadata(isofile):
    """Return a L{Options} containing version, plaftorms, etc.

    @param isofile: the path to a ISO file
    @type isofile: str
    """
    sp = ShellInterface().open()
    xml = fromstring(sp.run('isoinfo -i "%s" -x "/METADATA.XML;1"' % isofile))
    product = Product(xml.find("productName").text)
    version = Version("%s %s" % (xml.find("version").text, 
                                 xml.find("buildNumber").text),
                      product=product)
    
    ret = Options()
    spnode = xml.find('supportedPlatforms')
    if spnode is not None:
        ret.platforms = [e.text for e in spnode.findall('platform')]
    ret.version = version
    if xml.find("minVersion") is not None:
        ret.minversion = Version("%s" % xml.find("minVersion").text, product=product)
    ret.emversion = Version("%s" % xml.find("requiredEmVersion").text, product=Product('EM'))
    ret.releasenotes = xml.find("releaseNotesUrl").text
    if xml.find("versionReleaseDateText") is not None:
        ret.releasedate = xml.find("versionReleaseDateText").text
    ret.requirements = dict((e.find('name').text, e.find('value').text) 
                            for e in xml.find('platformRequirements'))
    ret.image_type = xml.find("imageType").text
    if ret.image_type == 'hotfix':
        hfnode = xml.find("thisHotfix")
        ret.hfid = hfnode.find('hotfixID').text
        ret.hftitle = hfnode.find('hotfixTitle').text
    return ret

def version_from_metadata(isofile):
    """Return a L{Version} object according to the info in metadata.xml.

    @param isofile: the path to a ISO file
    @type isofile: str
    """
    return iso_metadata(isofile).version


class CMFileFinder(object):
    """Base class for finding a file associated with a BIGIP build.

    The L{find_file} method will look at all the potential files in all
    the potential directories and check if a file matches.  If it finds
    a file that matches, then it returns the full path to the user.

    Subclasses conceptually need to supply two basic things:

        - C{potential_locations} - where to look.
        - C{matches} - how to tell if I've found the right file.

    """
    def __init__(self, root='/', *args, **kwargs):
        self.root = root

    def find_file(self):
        """Find a file that matches its attribute values.

        @return: The full path to the file if one is found.
        @raise IsoNotFoundError: If no file could be found matching its
                                 given criteria.

        """
        for directory in ifilter(self._isdir, self.potential_locations()):
            for potential_file in self.files_for(directory):
                if self.matches(potential_file):
                    # potential_file is only a relative path, but need to give
                    # the user the full path.
                    full_path = self._get_full_path(directory, potential_file)
                    return full_path
        else:
            self._raise_not_found_error()

    def potential_locations(self):
        raise NotImplementedError("Subclasses must implement a potential_locations "
                                  "method.")

    def matches(self, filename):
        raise NotImplementedError("Subclasses must implement a matches "
                                  "method.")

    def _isdir(self, d):
        return os.path.isdir(d)

    def files_for(self, directory):
        return self.os_service.files_for(directory)

    def _get_full_path(self, directory, basename):
        return os.path.join(directory, basename)

    def _raise_not_found_error(self):
        param_str = ' '.join([
            '%s: %s' % (k, v) for k, v
            in self.__dict__.iteritems() if not k.startswith('_')])
        raise FileNotFoundError("Could not find file that matches:"
                                " %s" % (param_str))

    @property
    def os_service(self):
        if not hasattr(self, '_os_service'):
            self._os_service = OSFileLister()
        return self._os_service


class OSFileLister(object):
    def files_for(self, directory):
        for content in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, content)):
                yield content


class IsoFinder(CMFileFinder):
    """Base class used to find BIGIP ISO files.

    These classes are parameterized with the appropriate criteria
    needed to find an an iso file on creation.

    The C{find_file} method is then called to search for
    an ISO file that matches its criteria.

    Subclasses are only overriding
    two internal methods:

        - C{_basepath} - The root directory to start looking.
        - C{_make_regex} - The regex to use to determine a file match.

    This is because all of the subclasses rely on a regex search to
    find the correct file, and the subclasses have the same algorithm
    for finding potential locations, except for where to start the
    search (C{_basepath}).
    """
    def __init__(self, identifier, build=None, product=BIGIP, *args, **kwargs):
        self.identifier = identifier
        self.build = build
        self._product = product
        self._regex = self._make_regex()
        super(IsoFinder, self).__init__(*args, **kwargs)

    def _make_regex(self):
        raise NotImplementedError("Subclass must provide _make_regex method.")

    def _basepath(self, identifier):
        raise NotImplementedError("Subclass must provide _basepath method.")

    def potential_locations(self):
        # The base path is typically based on the identifier, ie "10.0.0"
        # gives something like /build/bigip/v10.0.0/
        basepath = self._basepath(self.identifier)
        for subdir in ('daily', 'dist'):
            if self.build is None:
                yield os.path.join(basepath, subdir, 'current')
                yield os.path.join(basepath, subdir, 'release')
            else:
                yield os.path.join(basepath, subdir, 'build%s' % self.build)

    def matches(self, filename):
        if self._regex.search(filename):
            return True
        else:
            return False

    def _raise_not_found_error(self):
            param_str = ' '.join(['%s: %s' % (k, v) for k, v
                         in self.__dict__.iteritems()
                         if not k.startswith('_')])
            raise IsoNotFoundError("Could not find ISO file that matches:"
                                    " %s" % param_str)


class VersionFinder(IsoFinder):
    def _make_regex(self):
        iso_regex = re.compile(r'%s-'
                               '\d+\.\d+\.\d+'
                               '\.\d+\.\d+'
                               '\.iso$' % self._product,
                               re.IGNORECASE)
        return iso_regex

    def _basepath(self, version):
        return os.path.join(self.root, self._product, 'v%s' % version)


class ReleasedVersionFinder(VersionFinder):

    def potential_locations(self):
        basepath = self._basepath(self.identifier)
        yield os.path.join(basepath, 'dist', 'release')


class ProjectFinder(IsoFinder):
    def _basepath(self, identifier):
        return os.path.join(self.root, self._product, 'project', identifier)

    def _make_regex(self):
        iso_regex = re.compile(r'%s-'
                               '\d+\.\d+\.\d+'
                               '\.\d+\.\d+'
                               '\.iso$' % self._product,
                               re.IGNORECASE)
        return iso_regex


class HotfixFinder(IsoFinder):
    def __init__(self, identifier, hotfix='eng', *args, **kwargs):
        self.hotfix = hotfix.lower()
        hf_identifier = self.create_actual_identifier(identifier, self.hotfix)
        self._original_identifier = identifier
        super(HotfixFinder, self).__init__(identifier=hf_identifier, 
                                           *args, **kwargs)

    def create_actual_identifier(self, identifier, hotfix):
        if hotfix.lower() == 'eng':
            return identifier
        return '-'.join([identifier, hotfix])

    def potential_locations(self):
        for location in super(HotfixFinder, self).potential_locations():
            yield location
        # Old location. See EM 1.8.0 for example.
        yield os.path.join(self.root,
                           'hotfix',
                           self._product,
                           'v%s' % self._original_identifier,
                           'test',
                           '%s-%s-ENG' % (self.hotfix.upper(), self.build))
        if self.hotfix == 'eng':
            yield os.path.join(self.root,
                               self._product,
                               'v%s' % self._original_identifier,
                               'hotfix',
                               'HF-%s-ENG' % self.build)
            yield os.path.join(self.root,
                               'enghf',
                               self._product,
                               'v%s' % self._original_identifier,
                               'build%s' % self.build,
                               'current')
            yield os.path.join(self.root,
                               'hotfix',
                               self._product,
                               'v%s' % self._original_identifier,
                               'test',
                               'HF-%s-ENG' % self.build)
        else:
            yield os.path.join(self.root,
                               self._product,
                               'v%s' % self.identifier,
                               'hotfix',
                               '%s-%s-ENG' % (self.hotfix.upper(), self.build))

    def matches(self, name):
        if any(regex.search(name) for regex in self._regex):
            return True
        else:
            return False

    def _basepath(self, identifier):
        basepath = os.path.join(self.root, self._product, 'v%s' % identifier)
        return basepath

    def _make_regex(self):
        build = r'\d+\.\d+' if self.build is None else self.build
        
        hotfix_regex = re.compile(r'hotfix-%s-'
                                  '%s-%s-%s\.(iso|im)$'
                                  % (self._product, self._original_identifier,
                                     build, self.hotfix), re.IGNORECASE)
        eng_hotfix_regex = re.compile(r'hotfix-%s-'
                                      '%s-%s-%s-eng\.(iso|im)$'
                                      % (self._product,
                                         self._original_identifier,
                                         self.hotfix, build), re.IGNORECASE)
        # Sometimes with an identifier of 'hf1-random', the iso will
        # only have the 'hf1' part, so we check this "partial" match as well.
        partial_hotfix_refex = re.compile(r'hotfix-%s-'
                                          '%s-%s-%s\.(iso|im)$' %
                                          (self._product,
                                           self._original_identifier,
                                           build,
                                           self.hotfix.split('-')[0]),
                                          re.IGNORECASE)
        return [hotfix_regex, eng_hotfix_regex, partial_hotfix_refex]


class ReleasedHotfixFinder(HotfixFinder):

    def potential_locations(self):
        basepath = self._basepath(self.identifier)
        yield os.path.join(basepath, 'dist', 'release')

    def _make_regex(self):
        hotfix_regex = re.compile(r'hotfix-%s-'
                                  '\d+\.\d+\.\d+'
                                  '-\d+\.\d+-(\w+)'
                                  '\.(iso|im)$' % self._product, re.IGNORECASE)
        return [hotfix_regex]
