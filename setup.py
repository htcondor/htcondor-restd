"""
HTCondor REST daemon

This webapp listens to HTTP queries and transforms them into queries
to the Condor daemons for queue, machine, and config information.
"""

from setuptools import setup

setup(
    name="HTCondor REST daemon",
    version="1.0",
    long_description=__doc__,
    packages=["condor_restd"],
    include_package_data=True,
    zip_safe=False,
    install_requires=["flask", "flask-restful", "htcondor"],
)
