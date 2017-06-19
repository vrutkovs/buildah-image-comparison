import os
import pytest
import subprocess
import json


dir_path = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.join(dir_path, "tests")


def prefill_dir_list():
    dir_list = []
    for root, dirs, _ in os.walk(test_dir, topdown=False):
        for x in dirs:
            dockerfile_path = os.path.join(root, x, 'Dockerfile')
            if os.path.isfile(dockerfile_path):
                dir_list.append(x)
    return list(sorted(dir_list))


@pytest.fixture(scope="module", params=prefill_dir_list())
def images(request):
    dockerapi_image = "test/%s:dockerapi" % request.param
    full_path = os.path.join(test_dir, request.param)
    exit_code = subprocess.call(["docker", "build", "-t", dockerapi_image, full_path])
    assert exit_code == 0

    buildah_image_name = "test/%s:buildah" % request.param
    full_path = os.path.join(test_dir, request.param)
    build_exit_code = subprocess.call(["buildah", "--storage-driver", "overlay2",
                                       "bud", "--tag", buildah_image_name, full_path])
    assert build_exit_code == 0
    push_exit_code = subprocess.call(["buildah", "--storage-driver", "overlay2",
                                      "push", buildah_image_name,
                                      "docker-daemon:{}".format(buildah_image_name)])
    assert push_exit_code == 0
    return (dockerapi_image, buildah_image_name)


def test_compare_with_atomic_diff(images):
    (original_image, buildah_image) = images

    diff_str = subprocess.check_output(["atomic", "diff", "--json", original_image, buildah_image])
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

    assert diff_json[original_image]['unique_files'] == []
    assert diff_json[buildah_image]['unique_files'] == []


def test_run_command_in_container(images):
    (_, buildah_image) = images

    exit_code = subprocess.call(["docker", "run", "--rm", "-i", buildah_image])
    assert exit_code == 0
