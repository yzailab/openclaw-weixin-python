"""
Setup script for openclaw-weixin-python
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="openclaw-weixin-python",
    version="1.0.0",
    author="OpenClaw Community",
    author_email="",
    description="Python SDK for OpenClaw Weixin (WeChat) channel",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openclaw/openclaw-weixin-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "weixin=weixin_sdk.cli:entry_point",
        ],
    },
    install_requires=[
        "aiohttp>=3.8.0",
        "pycryptodome>=3.15.0",
        "qrcode[pil]>=7.4.0",
        "Pillow>=9.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
        "media": [
            "pysilk-python>=0.1.0",
        ],
        "cli": [
            "requests>=2.28.0",
            "tabulate>=0.9.0",
        ],
    },
)
