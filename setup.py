import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="vaxup",
    version="0.0.1",
    author="Trevor Manz",
    author_email="trevor.j.manz@gmail.com",
    description="A bot to batch fill vaccine registration froms for authorized enrollers in NYC.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/manzt/vaxup",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "selenium>=3.141.0",
    ],
    entry_points={
        "console_scripts": ["vaxup=vaxup.main:main"],
    },
)
