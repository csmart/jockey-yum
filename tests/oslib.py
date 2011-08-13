# -*- coding: utf-8 -*-

'''oslib tests'''

# (c) 2007 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest, os, tempfile, shutil, subprocess, sys, re, apt

from jockey.oslib import OSLib
import sandbox
import httpd

import jockey.detection

# fingerprint of tests/data/pubring.gpg
test_gpg_fp = '4EF8 3174 F985 6BD6 0E8D  584C 1A2E C5F3 E6B6 0077'

class OSLibTest(sandbox.LogTestCase):
    '''OSLib tests'''

    def setUp(self):
        (fd, self.tempfile) = tempfile.mkstemp()
        os.close(fd)
        self._create_apt_sandbox()

    def tearDown(self):
        os.unlink(self.tempfile)
        apt_root = os.path.join(OSLib.inst.workdir, 'aptroot')
        if os.path.isdir(apt_root):
            shutil.rmtree(apt_root)
        archive = os.path.join(OSLib.inst.workdir, 'archive')
        if os.path.isdir(archive):
            shutil.rmtree(archive)

    def test_module_blacklisting(self):
        '''module_blacklisted() and blacklist_module()'''

        for m in sandbox.fake_modinfo:
            self.failIf(OSLib.inst.module_blacklisted(m))

            # remove nonexisting entry
            OSLib.inst.blacklist_module(m, False)
            self.failIf(OSLib.inst.module_blacklisted(m))

            # double addition
            OSLib.inst.blacklist_module(m, True)
            self.assert_(OSLib.inst.module_blacklisted(m))
            OSLib.inst.blacklist_module(m, True)
            self.assert_(OSLib.inst.module_blacklisted(m))

        self.assertEqual(open(OSLib.inst.module_blacklist_file).read(), 
            ''.join(['blacklist %s\n' % m for m in sorted(sandbox.fake_modinfo.keys())]))

        # file is removed once it becomes empty
        for m in sandbox.fake_modinfo:
            OSLib.inst.blacklist_module(m, False)
            self.failIf(OSLib.inst.module_blacklisted(m))

        self.failIf(os.path.exists(OSLib.inst.module_blacklist_file))

        # directory gets created if it does not exist
        os.rmdir(os.path.dirname(OSLib.inst.module_blacklist_file))
        OSLib.inst.blacklist_module('vanilla', True)
        self.assert_(OSLib.inst.module_blacklisted('vanilla'))
        OSLib.inst.blacklist_module('vanilla', False)
        self.failIf(os.path.exists(OSLib.inst.module_blacklist_file))

    def test_module_blacklist_load(self):
        '''module blacklist loading.'''

        f = open(OSLib.inst.module_blacklist_file, 'w')
        try:
            f.write('''blacklist vanilla
# FOO BAR

 blacklist  cherry # we do not like red fruits
# blacklist mint
''')
            f.close()

            OSLib.inst._load_module_blacklist()

            self.assert_(OSLib.inst.module_blacklisted('vanilla'))
            self.assert_(OSLib.inst.module_blacklisted('cherry'))
            self.failIf(OSLib.inst.module_blacklisted('chocolate'))
            self.failIf(OSLib.inst.module_blacklisted('mint'))
            self.failIf(OSLib.inst.module_blacklisted('vanilla3d'))
        finally:
            os.unlink(OSLib.inst.module_blacklist_file)
            OSLib.inst._load_module_blacklist()

    def test_module_blacklist_load_thirdparty(self):
        '''module blacklist loading of other files in modprobe.d/.'''

        path = os.path.join(os.path.dirname(OSLib.inst.module_blacklist_file),
            'blacklist-custom')
        f = open(path, 'w')
        try:
            f.write('''blacklist vanilla
# FOO BAR

 blacklist  cherry # we do not like red fruits
# blacklist mint
''')
            f.close()

            OSLib.inst._load_module_blacklist()

            self.assert_(OSLib.inst.module_blacklisted('vanilla'))
            self.assert_(OSLib.inst.module_blacklisted('cherry'))
            self.failIf(OSLib.inst.module_blacklisted('chocolate'))
            self.failIf(OSLib.inst.module_blacklisted('mint'))
            self.failIf(OSLib.inst.module_blacklisted('vanilla3d'))
        finally:
            os.unlink(path)
            OSLib.inst._load_module_blacklist()

    def test_get_system_vendor_product(self):
        '''get_system_vendor_product()'''

        # vendor/product name
        self.assertEqual(OSLib.inst.get_system_vendor_product(), 
                ('VaporTech Inc.', 'Virtualtop X-1'))

        # without vendor/product name
        OSLib.inst.set_dmi(None, None)
        self.assertEqual(OSLib.inst.get_system_vendor_product(), ('', ''))

        # vendor name only
        OSLib.inst.set_dmi('VaporTech Inc.', None)
        self.assertEqual(OSLib.inst.get_system_vendor_product(), 
            ('VaporTech Inc.', ''))

        # actual system's implementation is a string
        v, p = OSLib(client_only=True).get_system_vendor_product()
        self.assert_(hasattr(v, 'startswith'))
        self.assert_(hasattr(p, 'startswith'))

    def test_package_query(self):
        '''package querying'''

        # use real OSLib here, not test suite's fake implementation
        o = OSLib()

        self.assertEqual(o.package_installed('coreutils'), True)
        self.assertEqual(o.package_installed('nonexisting'), False)

        self.assertEqual(o.is_package_free('coreutils'), True)
        self.assertRaises(ValueError, o.is_package_free, 'nonexisting')

        (short, long) = o.package_description('bash')
        self.assert_('sh' in short.lower())
        self.assert_('shell' in long) 
        self.failIf('size:' in long) 
        self.assertRaises(ValueError, o.package_description, 'nonexisting')

        self.assertRaises(ValueError, o.package_files, 'nonexisting')
        coreutils_files = o.package_files('coreutils')
        self.assert_('/bin/cat' in coreutils_files)
        self.assert_('/bin/tail' in coreutils_files or 
            '/usr/bin/tail' in coreutils_files)

    def test_package_install_unknown(self):
        '''package installation/removal for unknown package'''

        # use real OSLib here, not test suite's fake implementation
        o = OSLib()

        self.assertRaises(ValueError, o.install_package, 'nonexisting', None)
        # this should not crash, since it is not installed
        o.remove_package('nonexisting', None)

    def test_package_install_thirdparty_unsigned_indep(self):
        '''package installation for unsigned third-party repo, arch indep'''

        archive = self._create_archive()
        try:
            self.sandbox_oslib.install_package('myppd', None, 'deb file://' + archive + ' /',
                    None)
            # if we are run as root, this might succeed, and we clean up again
            self.assert_(self.sandbox_oslib.package_installed('myppd'))
            self.sandbox_oslib.remove_package('myppd', None)
        except SystemError, e:
            # this fails as non-root, as apt can't be told to not chroot(RootDir)
            self.assertEqual(str(e), 'installArchives() failed')

    def test_package_install_thirdparty_unsigned_binary(self):
        '''package installation for unsigned third-party repo, binary'''

        archive = self._create_archive()
        try:
            self.sandbox_oslib.install_package('binary', None, 
                    'deb file://' + archive + ' /', None)
            self.fail('installing unsigned binary package is not allowed')
        except SystemError, e:
            self.assert_('no trusted origin' in str(e))

    def test_package_install_thirdparty_signed_binary(self):
        '''package installation for signed third-party repo, binary'''

        archive = self._create_archive(signed=True)
        self._start_keyserver()
        try:
            self.sandbox_oslib.install_package('binary', None, 
                    'deb file://' + archive + ' /', test_gpg_fp)
            # if we are run as root, this might succeed, and we clean up again
            self.assert_(self.sandbox_oslib.package_installed('binary'))
            self.sandbox_oslib.remove_package('binary', None)
        except SystemError, e:
            # this fails as non-root, as apt can't be told to not chroot(RootDir)
            self.assertEqual(str(e), 'installArchives() failed')
        finally:
            self._stop_keyserver()

    def test_package_install_thirdparty_signed_binary_bad_fp(self):
        '''package installation for signed third-party repo, binary, bad fingerprint'''

        archive = self._create_archive(signed=True)
        self._start_keyserver()
        try:
            self.sandbox_oslib.install_package('binary', None, 
                    'deb file://' + archive + ' /', test_gpg_fp.replace('4', '1'))
            self.fail('installing binary package with bad GPG key is not allowed')
        except SystemError, e:
            # this fails as non-root, as apt can't be told to not chroot(RootDir)
            self.assert_('failed to import key' in str(e))
        finally:
            self._stop_keyserver()

    def test_ubuntu_repositories(self):
        '''Ubuntu implementation of repository add/removal/query'''

        f = open(self.sandbox_oslib.apt_sources, 'w')
        f.write('''deb file:///tmp/ /
deb-src http://foo.com/foo nerdy other
#deb http://foo.com/foo nerdy universe
deb http://foo.com/foo nerdy main
''')

        f.close()
        f = open(self.sandbox_oslib.apt_sources + '.d/fake.list', 'w')
        f.write('deb http://ubun.tu test/\ndeb-src http://ubu.tu xxx/\n')
        f.close()

        self.assert_(self.sandbox_oslib.repository_enabled('deb file:///tmp/ /'))
        self.failIf(self.sandbox_oslib.repository_enabled('deb file:///tmp2/ /'))
        self.failIf(self.sandbox_oslib.repository_enabled('deb http://foo.com/foo nerdy other'))
        self.failIf(self.sandbox_oslib.repository_enabled('deb http://foo.com/foo nerdy universe'))
        self.assert_(self.sandbox_oslib.repository_enabled('deb http://foo.com/foo nerdy main'))
        self.assert_(self.sandbox_oslib.repository_enabled('deb http://ubun.tu test/'))
        self.failIf(self.sandbox_oslib.repository_enabled('deb http://ubun.tu xxx/'))

        self.failIf(self.sandbox_oslib.repository_enabled('deb http://third.party moo'))

        archive = self._create_archive()
        debline = 'deb file://' + archive + ' /'
        self.sandbox_oslib._add_repository(debline, None, None)

        self.assert_(self.sandbox_oslib.repository_enabled(debline))
        self.assert_(os.path.exists(self.sandbox_oslib.apt_jockey_source))
        self.sandbox_oslib._remove_repository(debline)
        self.failIf(self.sandbox_oslib.repository_enabled(debline))
        self.failIf(os.path.exists(self.sandbox_oslib.apt_jockey_source))
        self.sandbox_oslib._remove_repository(debline)
        self.failIf(self.sandbox_oslib.repository_enabled(debline))

    def test_has_repositories(self):
        '''has_repositories()

        This is only a shallow test that the function works. We assume that we
        have repositories in the test environment for now.
        '''
        o = OSLib()
        self.assertEqual(o.has_repositories(), True)

    def test_ubuntu_package_header_modaliases(self):
        '''package_header_modaliases() plausibility for Ubuntu packages'''

        o = OSLib()
        map = o.package_header_modaliases()
        if not map:
            return self.skipTest('no data available')

        module_name_re = re.compile('^[a-zA-Z0-9_]+$')
        alias_re = re.compile('^[a-z]+:[a-zA-Z0-9_*-]+$')
        for p, ma_map in map.iteritems():
            # p should be a valid package name
            self.assertNotEqual(o.package_description(p), '')

            for module, aliases in ma_map.iteritems():
                self.assert_(module_name_re.match(module), 'invalid module name ' + module)
            self.assertNotEqual(len(aliases), 0)
            for a in aliases:
                self.assert_(alias_re.match(a), 'invalid modalias of %s: %s' % (module, a))

    def test_parse_ubuntu_package_header_modalias(self):
        '''package_header_modaliases()'''

        class MockPackage():
            pass
        class MockVersion():
            pass
        o = OSLib()
        pkg = MockPackage()
        pkg.name = 'foo'
        pkg.candidate = MockVersion()
        mock_record = { 'Package' : 'foo',
                        'Modaliases' : 'mod1(pci1, pci2), mod2(pci1)' 
                      }
        pkg.candidate.record = mock_record
        res = o.package_header_modaliases([pkg])
        self.assertEqual(res, 
                         {'foo': {'mod1': ['pci1', 'pci2'], 'mod2': ['pci1']}})

    @unittest.skipUnless(OSLib.has_defaultroute(), 'online test')
    def test_ssl_cert_file(self):
        '''ssl_cert_file()

        This uses a known-good URL from an Epson printer driver to ensure that
        the returned file contains useful certificates. Skipped if no
        SSL cert file is available.
        '''

        cert = OSLib().ssl_cert_file()
        if not cert:
            return self.skipTest('not available]')

        fp = jockey.detection.download_gpg_fingerprint(
                'https://linux.avasys.jp/drivers/lsb/epson-inkjet/key/fingerprint')
        self.assertNotEqual(fp, None)

    def test_import_gpg_key_valid(self):
        '''import_gpg_key() for valid fingerprint'''

        o = OSLib()
        o.gpg_key_server = 'localhost'
        self._start_keyserver()
        try:
            o.import_gpg_key(self.tempfile, test_gpg_fp)
        finally:
            self._stop_keyserver()
        self.assertEqual(o._gpg_keyring_fingerprints(self.tempfile),
                [test_gpg_fp])

    def test_import_gpg_key_invalid(self):
        '''import_gpg_key() for invalid fingerprint'''

        o = OSLib()
        o.gpg_key_server = 'localhost'
        self._start_keyserver()
        try:
            self.assertRaises(SystemError, o.import_gpg_key, self.tempfile,
                    test_gpg_fp.replace('4', '5')) 
        finally:
            self._stop_keyserver()

        self.assertEqual(o._gpg_keyring_fingerprints(self.tempfile), [])

    @unittest.skipUnless(OSLib.has_defaultroute(), 'online test')
    def test_import_gpg_key_multimatch(self):
        '''import_gpg_key() for multiple key ID matches'''

        o = OSLib()

        # there are two 0xDEADBEEF ID keys
        fp = '5425 931B 5B99 C58B 40BD  CE87 7AC1 3FB2 DEAD BEEF'
        o.import_gpg_key(self.tempfile, fp)
        self.assert_(fp in o._gpg_keyring_fingerprints(self.tempfile))

    def test_import_gpg_key_no_program(self):
        '''import_gpg_key() for unavailable gpg'''

        o = OSLib()
        orig_path = os.environ.get('PATH', '')
        try:
            os.environ['PATH'] = ''
            fp = '3BDC 0482 4EA8 1277 AE46  EA72 F988 25AC 26B4 7B9F'
            self.assertRaises(SystemError, o.import_gpg_key, self.tempfile, fp)
        finally:
            os.environ['PATH'] = orig_path
        self.assertEqual(o._gpg_keyring_fingerprints(self.tempfile), [])

    def test_ubuntu_xorg_video_abi(self):
        o = OSLib()
        self.assert_(o.current_xorg_video_abi().startswith('xorg-video-abi-'))
        self.assert_(o.video_driver_abi('nvidia-current').startswith('xorg-video-abi-'))

    def test_ubuntu_kernel_headers(self):
        o = OSLib()
        (short, long) = o.package_description(o.kernel_header_package)
        self.assert_(short)
        self.assert_(long)

    #
    # Helper methods
    #

    @classmethod
    def _start_keyserver(klass):
        '''Run a keyserver on localhost (just serves the test suite key).'''

        dir = os.path.join(OSLib.inst.workdir, 'pks')
        os.mkdir(dir, 0o700)
        # quiesce a message from gpg
        open(os.path.join(dir, 'secring.gpg'), 'w').close()
        lookup = open(os.path.join(dir, 'lookup'), 'w')
        assert subprocess.call(['gpg', '--homedir', dir, '--no-default-keyring',
            '--primary-keyring', os.path.join(os.path.dirname(__file__), 'data/pubring.gpg'),
            '--export', '-a'], stdout=lookup) == 0
        httpd.start(11371, OSLib.inst.workdir)

    @classmethod
    def _stop_keyserver(klass):
        '''Stop the keyserver.'''

        httpd.stop()
        shutil.rmtree(os.path.join(OSLib.inst.workdir, 'pks'))

    @classmethod
    def _create_deb(klass, name, arch, dir):
        '''Create a dummy deb with given name and architecture.

        Return the full path of the deb.
        '''
        d = os.path.join(OSLib.inst.workdir, name)
        os.makedirs(os.path.join(d, 'DEBIAN'))

        open(os.path.join(d, 'DEBIAN', 'control'), 'w').write('''Package: %s
Version: 1
Priority: optional
Section: devel
Architecture: %s
Maintainer: Joe <joe@example.com>
Description: dummy package
 just a test dummy package
''' % (name, arch))

        debpath = os.path.join(dir, '%s_1_%s.deb' % (name, arch))
        assert subprocess.call(['dpkg', '-b', d, debpath],
            stdout=subprocess.PIPE) == 0

        shutil.rmtree(d)
        assert os.path.exists(debpath)
        return debpath

    @classmethod
    def _create_archive(klass, signed=False):
        '''Create a test archive.

        This will create a deb archive with one Arch: all package "myppd"
        and one architecture dependent package "binary". The release is
        name is 'testy'.

        If signed is True, the Release file will be signed with the test
        suite's GPG key.

        Return the path to the archive.
        '''
        archive = os.path.join(OSLib.inst.workdir, 'archive')
        os.mkdir(archive)

        dpkg = subprocess.Popen(['dpkg-architecture', '-qDEB_HOST_ARCH'],
                stdout=subprocess.PIPE)
        host_arch = dpkg.communicate()[0].strip()
        assert dpkg.returncode == 0

        klass._create_deb('myppd', 'all', archive)
        klass._create_deb('binary', host_arch, archive)

        assert subprocess.call('apt-ftparchive packages . > Packages', shell=True,
                cwd=archive) == 0
        assert subprocess.call('apt-ftparchive -o APT::FTPArchive::Release::Suite=testy release . > Release',
                shell=True, cwd=archive) == 0

        if signed:
            assert subprocess.call(['gpg', '--homedir', OSLib.inst.workdir,
                '--no-default-keyring', '--primary-keyring',
                os.path.join(os.path.dirname(__file__), 'data', 'pubring.gpg'),
                '--secret-keyring', 
                os.path.join(os.path.dirname(__file__), 'data', 'secring.gpg'),
                '-abs', '--batch', '-o', os.path.join(archive, 'Release.gpg'), 
                os.path.join(archive, 'Release')]) == 0

        return archive

    def _create_apt_sandbox(self):
        '''Create sandbox for apt and configure it to use it'''

        apt_root = os.path.join(OSLib.inst.workdir, 'aptroot')

        # we need to symlink the apt_root into itself, as Cache.update()'s
        # sources_list argument prepends RootDir
        os.makedirs(apt_root + os.path.dirname(apt_root))
        os.symlink(apt_root, apt_root + apt_root)

        apt.apt_pkg.init_config()
        apt.apt_pkg.config.set('RootDir', apt_root)
        apt.apt_pkg.config.set('Debug::NoLocking', 'true')
        #apt.apt_pkg.config.set('Debug::pkgDPkgPM', 'true')
        apt.apt_pkg.config.clear('DPkg::Post-Invoke')
        apt.apt_pkg.config.clear('DPkg::Pre-Install-Pkgs')
        apt.apt_pkg.config.clear('APT::Update::Post-Invoke-Success')
        apt.apt_pkg.init_system()

        os.makedirs(os.path.join(apt_root, 'etc', 'apt', 'sources.list.d'))
        os.makedirs(os.path.join(apt_root, 'etc', 'apt', 'apt.conf.d'))
        os.makedirs(os.path.join(apt_root, 'etc', 'apt', 'trusted.gpg.d'))
        os.makedirs(os.path.join(apt_root, 'usr', 'lib', 'apt'))
        os.makedirs(os.path.join(apt_root, 'var', 'lib', 'apt', 'lists', 'partial'))
        os.makedirs(os.path.join(apt_root, 'var', 'cache', 'apt', 'archives', 'partial'))
        dpkglib = os.path.join(apt_root, 'var', 'lib', 'dpkg')
        os.symlink('/usr/lib/apt/methods', os.path.join(apt_root, 'usr', 'lib', 'apt', 'methods'))
        os.makedirs(dpkglib)
        open(os.path.join(dpkglib, 'status'), 'w').close()
        open(os.path.join(apt_root, 'etc', 'apt', 'sources.list'), 'w').close()

        # create matching OSLib
        self.sandbox_oslib = OSLib()
        self.sandbox_oslib.apt_jockey_source = apt_root + self.sandbox_oslib.apt_jockey_source
        self.sandbox_oslib.apt_trusted_keyring = apt_root + self.sandbox_oslib.apt_trusted_keyring
        self.sandbox_oslib.apt_sources = apt_root + self.sandbox_oslib.apt_sources
        self.sandbox_oslib.gpg_key_server = 'localhost'

