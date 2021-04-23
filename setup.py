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
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "selenium>=3.141.0",
        "rich>=9.13.0",
        "pydantic>=1.8.1",
        "openpyxl>=3.0.7",
    ],
    entry_points={
        "console_scripts": ["vaxup=vaxup.cli:main"],
    },
)
