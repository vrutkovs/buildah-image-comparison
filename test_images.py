import os
import pytest
import subprocess
import json


dir_path = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.join(dir_path, "tests")


def prefill_dir_list():
    dir_list = []
    for _, dirs, _ in os.walk(test_dir, topdown=False):
        dir_list += [x for x in dirs]
    return dir_list


@pytest.fixture(scope="module", params=prefill_dir_list())
def images(request):
    dockerapi_image = "test/%s:dockerapi" % request.param
    full_path = os.path.join(test_dir, request.param)
    exit_code = subprocess.call(["docker", "build", "-t", dockerapi_image, full_path])
    assert exit_code == 0

    ocex_image_name = "test/%s:ocexdockerbuild" % request.param
    full_path = os.path.join(test_dir, request.param)
    exit_code = subprocess.call(["oc", "ex", "dockerbuild", full_path, ocex_image_name])
    assert exit_code == 0
    return (dockerapi_image, ocex_image_name)


def test_compare_with_atomic_diff(images):
    (image1, image2) = images

    diff_str = subprocess.check_output(["atomic", "diff", "--json", image1, image2])
    diff_json = json.loads(diff_str)

    # Remove items from files_differ if the reason is only time
    if diff_json['files_differ']:
        new_files_differ = []
        for diff_file in diff_json['files_differ']:
            if 'reasons' in diff_file and diff_file['reasons'] == ['time']:
                continue
            else:
                new_files_differ.append(diff_file)
        assert new_files_differ == []

    assert diff_json[image1]['unique_files'] == []
    assert diff_json[image2]['unique_files'] == []


def test_run_command_in_container(images):
    (_, image2) = images

    exit_code = subprocess.call(["docker", "run", "--rm", "-i", image2])
    assert exit_code == 0
