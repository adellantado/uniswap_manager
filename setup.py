from setuptools import setup, find_packages

setup(
    name='bum',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'web3',
        'click'
    ],
    entry_points={
        'console_scripts': [
            'bum = cli:cli',
        ],
    },
)