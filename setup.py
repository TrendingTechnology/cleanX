#!/usr/bin/env python

import sys
import shlex
import os
import subprocess
import site
import shutil
import platform

from glob import glob
from distutils.dir_util import copy_tree
from io import BytesIO
from string import Template

from setuptools import setup
from setuptools.command.install import install as InstallCommand
from setuptools.command.easy_install import easy_install as EZInstallCommand
from setuptools.dist import Distribution
from setuptools import Command


project_dir = os.path.dirname(os.path.realpath(__file__))
# This will exclude the project directory from sys.path so that Sphinx
# doesn't get confused about where to load the sources.
# _Note_ you _must_ install the project
# before you generate documentation, otherwise it will not work.
sys.path = [x for x in sys.path if not x == project_dir]


with open('README.md', 'r') as f:
    readme = f.read()

name = 'cleanX'
try:
    tag = subprocess.check_output([
        'git',
        '--no-pager',
        'describe',
        '--abbrev=0',
        '--tags',
    ]).strip().decode()
except subprocess.CalledProcessError as e:
    print(e.output)
    tag = 'v0.0.0'

version = tag[1:]


class TestCommand(Command):

    user_options = [('pytest-args=', 'a', 'Arguments to pass into py.test')]

    def initialize_options(self):
        self.pytest_args = ''

    def finalize_options(self):
        self.test_args = []
        self.test_suite = True

    def run(self):
        recs = self.distribution.tests_require

        if os.environ.get('CONDA_DEFAULT_ENV'):
            if recs:
                result = subprocess.call([
                    'conda',
                    'install',
                    '-y',
                    '-c', 'conda-forge',
                    ] + recs
                )
                if result:
                    raise RuntimeError('Cannot install test requirements')
        else:
            test_dist = Distribution()
            test_dist.install_requires = recs
            ezcmd = EZInstallCommand(test_dist)
            ezcmd.initialize_options()
            ezcmd.args = recs
            ezcmd.always_copy = True
            ezcmd.finalize_options()
            ezcmd.run()
            site.main()

        self.run_tests()


class PyTest(TestCommand):

    description = 'run unit tests'

    def run_tests(self):
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


class Pep8(TestCommand):

    description = 'validate sources against PEP8'

    def run_tests(self):
        from pycodestyle import StyleGuide

        package_dir = os.path.dirname(os.path.abspath(__file__))
        sources = glob(
            os.path.join(package_dir, 'cleanX', '**/*.py'),
            recursive=True,
        )
        style_guide = StyleGuide(paths=sources)
        options = style_guide.options

        report = style_guide.check_files()
        report.print_statistics()

        if report.total_errors:
            if options.count:
                sys.stderr.write(str(report.total_errors) + '\n')
            sys.exit(1)


class SphinxApiDoc(Command):

    description = 'run apidoc to generate documentation'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from sphinx.ext.apidoc import main

        src = os.path.join(project_dir, 'docs')
        special = (
            'index.rst',
            'cli.rst',
            'developers.rst',
            'medical-professionals.rst',
        )

        for f in glob(os.path.join(src, '*.rst')):
            for end in special:
                if f.endswith(end):
                    os.utime(f, None)
                    break
            else:
                os.unlink(f)

        sys.exit(main([
            '-o', src,
            '-f',
            os.path.join(project_dir, 'cleanX'),
            '--separate',
        ]))


class AnacondaUpload(Command):

    description = 'upload packages for Anaconda'

    user_options = [
        ('token=', 't', 'Anaconda token'),
        ('package=', 'p', 'Package to upload'),
    ]

    def initialize_options(self):
        self.token = None
        self.package = None

    def finalize_options(self):
        if (self.token is None) or (self.package is None):
            sys.stderr.write('Token and package are required\n')
            raise SystemExit(2)

    def run(self):
        env = dict(os.environ)
        env['ANACONDA_API_TOKEN'] = self.token
        proc = subprocess.Popen(
            [
                'anaconda',
                'upload',
                '--force',
                '--label', 'main',
                glob(self.package)[0],
            ],
            env=env,
            stderr=subprocess.PIPE,
        )
        _, err = proc.communicate()
        if proc.returncode:
            sys.stderr.write('Upload to Anaconda failed\n')
            sys.stderr.write('Stderr:\n')
            for line in err.decode().split('\n'):
                sys.stderr.write(line)
                sys.stderr.write('\n')
            raise SystemExit(1)


class GenerateCondaYaml(Command):

    description = 'generate metadata for conda package'

    user_options = [(
        'target-python=',
        't',
        'Python version to build the package for',
    )]

    def initialize_options(self):
        self.target_python = None

    def finalize_options(self):
        if self.target_python is None:
            maj, min, patch = sys.version.split(maxsplit=1)[0].split('.')
            
            self.target_python = '{}.{}'.format(maj, min)

    def run(self):
        tpls = glob(os.path.join(project_dir, 'conda-pkg/*.in'))

        for tpl_path in tpls:
            if tpl_path.endswith('env.yml.in'):
                continue
            with open(tpl_path) as f:
                tpl = Template(f.read())

            dst_path = tpl_path[:-3]

            with open(dst_path, 'w') as f:
                f.write(tpl.substitute(
                    version=version,
                    tag=tag,
                    python_version=self.target_python,
                ))


class FindEgg(Command):

    description = 'find Eggs built by this script'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print(glob('./dist/*.egg')[0])


class GenCondaEnv(Command):

    description = (
        'generate YAML file with requirements for conda environmnent'
    )

    user_options = [(
        'output=',
        'o',
        'File to save the environmnent description',
    )]

    def initialize_options(self):
        self.output = None

    def finalize_options(self):
        if self.output is None:
            self.output = 'cleanx-env-{}-py{}{}.yml'.format(
                platform.system().lower(),
                sys.version_info[0],
                sys.version_info[1],
            )

    def run(self):
        if os.environ.get('CONDA_DEFAULT_ENV') is None:
            raise RuntimeError(
                'This command can only run in conda environmnent',
            )
        env_tpl_path = os.path.join(
            os.path.dirname(__file__),
            'conda-pkg',
            'env.yml.in',
        )
        with open(env_tpl_path) as f:
            tpl = Template(f.read())
        conda_recs = []
        # TODO(wvxvw): Add flags to also include extras
        all_recs = (
            self.distribution.install_requires +
            self.distribution.tests_require +
            self.distribution.setup_requires
        )
        for rec in all_recs:
            result = subprocess.check_output(['conda', 'list', '-e', rec])
            for line in BytesIO(result):
                if not line.startswith(b'#'):
                    conda_recs.append(line.strip().decode())
                    break
            else:
                raise RuntimeError(
                    'Missing {}\n'.format(rec) +
                    'run "conda install -c conda-forge {}"'.format(rec),
                )
        output_contents = tpl.substitute(
            env_name=os.path.splitext(self.output)[0],
            conda_recs='\n  - '.join(conda_recs),
        )
        with open(self.output, 'w') as f:
            f.write(output_contents)


class Install(InstallCommand):

    def run(self):
        if os.environ.get('CONDA_DEFAULT_ENV'):
            packages = subprocess.check_output(['conda', 'list', '--export'])
            cmd = ['conda', 'install', '-y', 'conda-build', 'conda-verify']
            for line in packages.split(b'\n'):
                if line.startswith(b'conda-build='):
                    break
            else:
                if subprocess.call(cmd):
                    raise RuntimeError('Cannot install conda-build')
            shutil.rmtree(
                os.path.join(project_dir, 'dist'),
                ignore_errors=True,
            )
            shutil.rmtree(
                os.path.join(project_dir, 'build'),
                ignore_errors=True,
            )

            cmd = [
                'conda',
                'build',
                '-c', 'conda-forge',
                os.path.join(project_dir, 'conda-pkg'),
            ]
            if subprocess.call(cmd):
                raise RuntimeError('Couldn\'t build {} package'.format(name))
            cmd = [
                'conda',
                'install',
                '-c', 'conda-forge',
                '--use-local',
                '--update-deps',
                '--force-reinstall',
                '-y',
                'cleanx',
            ]
            if subprocess.call(cmd):
                raise RuntimeError('Couldn\'t install {} package'.format(name))
        else:
            # TODO(wvxvw): Find a way to avoid using subprocess to do
            # this
            if subprocess.call([sys.executable, __file__, 'bdist_egg']):
                raise RuntimeError('Couldn\'t build {} package'.format(name))
            egg = glob(os.path.join(project_dir, 'dist', '*.egg'))[0]
            # TODO(wvxvw): Use EZInstallCommand instead
            if subprocess.call([
                    sys.executable,
                    __file__,
                    'easy_install',
                    '--always-copy',
                    egg
            ]):
                raise RuntimeError('Couldn\'t install {} package'.format(name))
            package_dir = os.path.dirname(os.path.abspath(__file__))
            egg_info = os.path.join(package_dir, 'cleanX.egg-info')

            # Apparently, this is only set if we are in bdist_xxx
            if self.root:
                # PyPA idiots run setup.py install inside setup.py
                # bdist_wheel.  Because we don't do what a typical
                # install command would, and they rely on a bunch of
                # side effects of a typical install command, we need
                # to pretend that install happened in a way that they
                # expect.
                egg_info_cmd = self.distribution.get_command_obj(
                    'install_egg_info',
                )
                egg_info_cmd.ensure_finalized()
                make_pypa_happy = egg_info_cmd.target
                package_contents = os.path.join(
                    package_dir,
                    'build',
                    'lib',
                )
                copy_tree(egg_info, make_pypa_happy)
                copy_tree(package_contents, self.root)


class InstallDev(Install):

    def run(self):
        super().run()
        if os.environ.get('CONDA_DEFAULT_ENV'):
            cmd = [
                'conda',
                'install',
                '-c', 'conda-forge',
                '-y',
            ] + self.distribution.extras_require['dev']
            if subprocess.call(cmd):
                raise RuntimeError('Couldn\'t install {} package'.format(name))
        else:
            extras_dist = Distribution()
            extras_dist.install_requires = self.distribution.extras_require['dev']
            ezcmd = EZInstallCommand(extras_dist)
            ezcmd.initialize_options()
            ezcmd.args = self.distribution.extras_require['dev']
            ezcmd.always_copy = True
            ezcmd.finalize_options()
            ezcmd.run()

def install_requires():
    if os.environ.get('CONDA_DEFAULT_ENV'):
        return [
            'pandas',
            'numpy',
            'matplotlib',
            'pillow',
            'tesserocr',
            'opencv',
        ]
    return [
        'pandas',
        'numpy',
        'matplotlib',
        'pillow',
        'tesserocr',
        'opencv-python',
        'pytz',
    ]


# If we don't do this, we cannot run tests that involve
# multiprocessing
if __name__ == '__main__':
    setup(
        name=name,
        version=version,
        description='Python library for cleaning data in large datasets of Xrays',
        long_description=readme,
        long_description_content_type='text/markdown',
        author='doctormakeda@gmail.com',
        author_email='doctormakeda@gmail.com',
        maintainer='doctormakeda@gmail.com',
        maintainer_email= 'doctormakeda@gmail.com',
        url='https://github.com/drcandacemakedamoore/cleanX',
        license='MIT',
        packages=[
            'cleanX',
            'cleanX.dataset_processing',
            'cleanX.dicom_processing',
            'cleanX.image_work',
            'cleanX.cli',
        ],
        cmdclass={
            'test': PyTest,
            'lint': Pep8,
            'apidoc': SphinxApiDoc,
            'genconda': GenerateCondaYaml,
            'install': Install,
            'install_dev': InstallDev,
            'find_egg': FindEgg,
            'anaconda_upload': AnacondaUpload,
            'anaconda_gen_env': GenCondaEnv,
        },
        tests_require=['pytest', 'pycodestyle'],
        command_options={
            'build_sphinx': {
                'project': ('setup.py', name),
                'version': ('setup.py', version),
                'source_dir': ('setup.py', './docs'),
                'config_dir': ('setup.py', './docs'),
            },
        },
        setup_requires=['sphinx'],
        install_requires=install_requires(),
        extras_require={
            'cli': ['click'],
            'pydicom': ['pydicom'],
            'simpleitk': ['SimpleITK'],
            'dev': [
                'wheel',
                'sphinx',
                'pytest',
                'codestyle',
                'click',
                'pydicom',
                'SimpleITK',
            ],
        },
        zip_safe=False,
    )
