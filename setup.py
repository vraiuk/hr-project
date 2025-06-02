from setuptools import setup, find_packages

setup(
    name="hr-project",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pytest>=7.4.0",
        "python-dotenv>=1.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.0",
        "python-multipart>=0.0.6"
    ],
) 