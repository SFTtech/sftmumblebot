#!/usr/bin/env python2

from distutils.core import setup
from sftbot import VERSION
from sys import version_info
from os import path

if version_info[0] != 2:
    print("use python2 to install sftmumblebot")
    exit(1)

pb_filename = path.join(path.dirname(__file__),
                        "sftbot/protobuf/Mumble_pb2.py")
if not path.isfile(pb_filename):
    print("Mumble_pb2.py has not been generated yet.\nrun make first.")
    exit(1)

setup(
    name="sftmumblebot",
    version=VERSION,
    description="IRC-Mumble text bridge",
    long_description="Provides a text bridge between an IRC channel and a " +
                     "Mumble channel. Buil to be easily extendable to more " +
                     "protocols and uses.\n" +
                     "Repo: https://github.com/SFTtech/sftmumblebot",
    author="Michael Ensslin (see COPYING for contributors)",
    author_email="michael@ensslin.cc",
    url="https://github.com/SFTtech/sftmumblebot",
    license="GPLv3+",
    packages=["sftbot", "sftbot/protobuf"],
    scripts=["bin/sftbot"],
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: " +
        "GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Chat :: Internet Relay Chat",
        "Topic :: Communications :: Telephony",
    ],
)
