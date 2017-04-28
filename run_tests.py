import sys
import os
import logging
import subprocess
import json


log = logging.getLogger()
log.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

dir_path = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.join(dir_path, "tests")


def build_via_docker_api(directory):
    log.info("Running docker build for directory %s" % directory)

    image_name = "test/%s:dockerapi" % directory
    full_path = os.path.join(test_dir, directory)
    subprocess.call(["docker", "build", "-t", image_name, full_path])
    return image_name


def build_via_ocexdockerbuild(directory):
    log.info("Running oc ex dockerbuild for directory %s" % directory)

    image_name = "test/%s:ocexdockerbuild" % directory
    full_path = os.path.join(test_dir, directory)
    subprocess.call(["oc", "ex", "dockerbuild", full_path, image_name])
    return image_name


def get_atomic_diff_json(image1, image2):
    log.info("Comparing %s and %s" % (image1, image2))

    diff_str = subprocess.check_output(["atomic", "diff", "--json", image1, image2])
    return json.loads(diff_str)


def compare_with_atomic_diff(image1, image2):
    diff_json = get_atomic_diff_json(image1, image2)

    log.info("Removing different files if the only reason is time")
    # Remove items from files_differ if the reason is only time
    if diff_json['files_differ']:
        new_files_differ = []
        for diff_file in diff_json['files_differ']:
            if 'reasons' in diff_file and diff_file['reasons'] == ['time']:
                continue
            else:
                new_files_differ.append(diff_file)
        diff_json['files_differ'] = new_files_differ

    log.info("Comparing unique and different files")
    if diff_json['files_differ'] != []:
        raise RuntimeError("Images have different files: %s" % diff_json['files_differ'])

    if diff_json[image1]['unique_files']:
        raise RuntimeError("Docker API image has unique files: %s" %
                           diff_json[image1]['unique_files'])
    if diff_json[image2]['unique_files']:
        raise RuntimeError("oc ex dockerbuild image has unique files: %s" %
                           diff_json[image2]['unique_files'])
    log.info("atomic diff test - PASS")


def run_test(directory):
    dockerapi_image = build_via_docker_api(directory)
    ocexdockerbuild = build_via_ocexdockerbuild(directory)
    compare_with_atomic_diff(dockerapi_image, ocexdockerbuild)
    log.info("Images are identical")

for _, dirs, _ in os.walk(test_dir, topdown=False):
    for directory in dirs:
        try:
            run_test(directory)
        except:
            log.exception("Error running test in %s" % directory)
