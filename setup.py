from setuptools import setup, find_packages

setup(
    name="statsmonitor",
    version="1.0.0",
    description="CPU, GPU & RAM usage + temperature in the Ubuntu taskbar",
    author="Your Name",
    author_email="you@example.com",
    url="https://github.com/yourname/StatsMonitor",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "psutil>=5.9",
    ],
    entry_points={
        "console_scripts": [
            "statsmonitor=statsmonitor:main",
        ],
    },
    classifiers=[
        "Environment :: X11 Applications :: GTK",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Monitoring",
    ],
)