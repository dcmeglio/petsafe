import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="petsafe",
    version="1.3",
    author="Jordan Stremming & Dominick Meglio",
    license="MIT",
    author_email="dmeglio@gmail.com",
    description="Provides ability to connect and control a PetSafe Smart Feed and Scoopfree device using the PetSafe API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dcmeglio/petsafe",
    packages=setuptools.find_packages(),
    install_requires=["requests", "boto3"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
