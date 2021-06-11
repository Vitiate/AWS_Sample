import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="event_bridge_shipper",
    version="1.0.0-beta.1",

    description="Creates a Cloud Trail and a rule for forwarding s3 put notifications to an event bridge in a different account",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Jeremy Tirrell",

    package_dir={"": "event_bridge_shipper"},
    packages=setuptools.find_packages(where="event_bridge_shipper"),

    install_requires=[
        "aws-cdk.core==1.84.0",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
