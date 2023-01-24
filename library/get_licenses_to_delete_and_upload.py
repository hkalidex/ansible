#!/usr/bin/env python

import json
from ansible.module_utils.basic import AnsibleModule


def get_license_ids_to_delete(licenses_on_server, license_keys_on_file_list):
    license_ids_to_delete = []
    for license in licenses_on_server:
        if license["licenseKey"] not in license_keys_on_file_list:
            license_ids_to_delete.append(license["id"])
    return license_ids_to_delete


def get_license_keys_to_upload(licenses_on_server, license_keys_on_file_list):
    license_keys_to_upload = []
    license_keys_on_server_list = []
    for license in licenses_on_server:
        license_keys_on_server_list.append(license["licenseKey"])
    for license_key in license_keys_on_file_list:
        if license_key not in license_keys_on_server_list:
            license_keys_to_upload.append(license_key)

    return license_keys_to_upload


def main():
    module = AnsibleModule(
        argument_spec=dict(
            licenses_on_server=dict(required=True, type='dict', default=None),
            license_keys_file_path=dict(required=True, type='str', default=None)
        )
    )
    licenses_on_server = module.params.get('licenses_on_server')
    license_keys_file_path = module.params.get('license_keys_file_path')

    try:
        with open(license_keys_file_path) as license_keys_file:
            updated_license_keys = json.load(license_keys_file)
    except Exception as e:
        module.fail_json(msg="Unable to open file {}: {}".format(license_keys_file_path, e))

    license_ids_to_delete = get_license_ids_to_delete(licenses_on_server["solutionLicenses"], updated_license_keys["licenses"])
    license_keys_to_upload = get_license_keys_to_upload(licenses_on_server["solutionLicenses"], updated_license_keys["licenses"])
    output = {
        'license_ids_to_delete': license_ids_to_delete,
        'license_keys_to_upload': license_keys_to_upload
    }
    module.exit_json(msg=output)


if __name__ == "__main__":
    main()
