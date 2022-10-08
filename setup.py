from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name='pycurl-requests',
    version='0.2.2',
    description='A Requests-compatible interface for pycURL',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/dcoles/pycurl-requests',
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'pycurl',
        'chardet',
    ],
)
