"""
HTCondor REST Daemon

This webapp listens to HTTP queries and transforms them into queries
to the Condor daemons for queue, machine, and config information.
"""

from setuptools import setup

setup(
    name="HTCondor-RESTD",
    version="0.240508",
    long_description=__doc__,
    packages=["condor_restd"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "flask>=2.0.0",
        "flask-restful==0.3.10",
        "htcondor>=10.0.0",
    ],
)
