"""
HTCondor REST Daemon

This webapp listens to HTTP queries and transforms them into queries
to the Condor daemons for queue, machine, and config information.
"""

from setuptools import setup

setup(
    name="HTCondor-RESTD",
    version="0.200924",
    long_description=__doc__,
    packages=["condor_restd"],
    include_package_data=True,
    zip_safe=False,
    install_requires=["flask", "flask-restful", "htcondor>=8.9.2"],
)
