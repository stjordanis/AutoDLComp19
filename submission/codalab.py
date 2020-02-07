import argparse  # noqa: E402
import os
import shutil
import sys


import yaml


def _read_config(config_file):
    with open(config_file, 'r') as stream:
        return yaml.safe_load(stream)


sys.path.append(".")  # isort:skip

# Construct base CLI, later add args dynamically from config file too
parser = argparse.ArgumentParser()
parser.add_argument("--submission_dir", default=".codalab_submission")
parser.add_argument("--code_dir", default="src")
parser.add_argument("--config", default="general.yaml")
parser.add_argument("--zip_name", default="codalab_submission")
parser.add_argument("--no_clean_up", action="store_true", help="Do not delete submission dir")

args = parser.parse_args()

# Create submission directory
if os.path.isdir(args.submission_dir):
    shutil.rmtree(args.submission_dir)  # shutil does not work with pathlib
ignore = shutil.ignore_patterns("__pycache__")
shutil.copytree(args.code_dir, args.submission_dir, ignore=ignore)

# Read settings from config
def read_config(config_file):
    with open(config_file, 'r') as stream:
        return yaml.safe_load(stream)

config = read_config(args.code_dir + "/" + "configs/" + args.config)

# Copy active models
for model_file in config["active_model_files"]:
    model_name = model_file + ".pth"
    shutil.copyfile(config["model_dir"] + "/" + model_name, args.submission_dir + "/" + model_name)

# Include extra packages
for extra_package in config["extra_packages"]:
    shutil.copytree(
        extra_package,
        args.submission_dir + "/" + os.path.basename(extra_package),
        ignore=ignore,
    )

# Zip everything and clean up
shutil.make_archive(args.zip_name, "zip", args.submission_dir)
if not args.no_clean_up:
    shutil.rmtree(args.submission_dir)