from foqus_lib.framework.sdoe import sdoe
from importlib import resources
from pathlib import Path


def test_run_irsf():
    config_file = "config_irsf.ini"
    nd = 2
    copy_from_package("candidates_irsf.csv")
    copy_from_package(config_file)

    result = sdoe.run(config_file=config_file, nd=nd, test=False)


def test_run_usf():

    config_file = "config_usf.ini"
    nd = 2
    copy_from_package("candidates_usf.csv")
    copy_from_package(config_file)

    result = sdoe.run(config_file=config_file, nd=nd, test=False)


def test_run_nusf():
    config_file = "config_nusf.ini"
    nd = 2
    copy_from_package("candidates_nusf.csv")
    copy_from_package(config_file)

    result = sdoe.run(config_file=config_file, nd=nd, test=False)


def copy_from_package(file_name: str) -> None:
    content = resources.read_text(__package__, file_name)
    Path(file_name).write_text(content)