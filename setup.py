import pathlib

from setuptools import setup

pkg_name = 'pura'
base_dir = pathlib.Path(__file__).parent
with open(base_dir / 'src' / pkg_name / '_version.py') as f:
    version_globals = {}
    exec(f.read(), version_globals)
    version = version_globals['__version__']

setup(
    name=pkg_name,
    description='The little async embedded visualization framework that could',
    long_description='''
Pura is a simple embedded visualization framework inspired by the
Processing API and based on the python-trio async/await event loop.
''',
    long_description_content_type='text/markdown',
    version=version,
    author='GROOVE X, Inc.',
    author_email='gx-sw@groove-x.com',
    url='https://github.com/groove-x/pura',
    license='MIT',
    packages=[pkg_name],
    package_dir={'': 'src'},
    install_requires=[
        'attrs >= 18.1.0',
        'h11 >= 0.9.0',
        'trio >= 0.11.0',
        'trio-util >= 0.1.0',
        'trio-websocket >= 0.8.0'
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Framework :: Trio',
    ],
)
