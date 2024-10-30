from setuptools import setup

setup(
    version="2.0.0",
    name="dcm-bag-validator",
    description="bag profile and format validator",
    author="LZV.nrw",
    install_requires=[
        "bagit==1.*",
        "bagit_profile==1.3.1",
        "opf-fido==1.6.1",
        "xmltodict==0.*",
        "dcm-common>=3.0.0,<4.0.0",
    ],
    packages=[
        "dcm_bag_validator",
        "dcm_bag_validator.file_format_plugins"
    ],
    package_data={"dcm_bag_validator": ["py.typed"]},
    setuptools_git_versioning={
        "enabled": True,
        "version_file": "VERSION",
        "count_commits_from_version_file": True,
        "dev_template": "{tag}.dev{ccount}",
    },
)
