#!/usr/bin/env python

import json
from ansible.module_utils.basic import AnsibleModule


def vra_adapter_already_exists(responses, adapter_name):
    adapter_already_exists = False
    for response in responses:
        response_name = None
        skipped = False
        if 'name' in response['item'].keys():
            response_name = response['item']['name']
            skipped = 'skipped' in response.keys()
        elif 'ansible_facts' in response.keys():
            response_name = response['ansible_facts']['name']
            skipped = response['ansible_facts']['skipped']
        else:
            pass
        if adapter_name == response_name:
            if skipped:
                adapter_already_exists = True
            else:
                if response['status'] != 201:
                    response_content = json.loads(response['content'])
                    if "already exists" in response_content['moreInformation'][0]['value']:
                        adapter_already_exists = True
    return adapter_already_exists


def get_vra_stdout_thumbprints(openssl_certificate_data):
    vra_stdout_thumbprints = {}
    for adapter_instance_ssl_info in openssl_certificate_data:
        resource_kind_key = adapter_instance_ssl_info['item']['resourceKey']['resourceKindKey']
        vra_adapter_name = adapter_instance_ssl_info['item']['resourceKey']['name']
        vra_adapter_parent = None
        if resource_kind_key == 'CUSTOM IaaS Web':
            vra_adapter_parent = adapter_instance_ssl_info['item']['resourceKey']['vra_adapter']
            vra_adapter_name = vra_adapter_parent
        if vra_adapter_parent or resource_kind_key == 'VCACAdapter Instance':
            has_cert = len(adapter_instance_ssl_info['stdout_lines']) > 0
            if vra_adapter_name not in vra_stdout_thumbprints.keys():
                if has_cert:
                    vra_stdout_thumbprints[vra_adapter_name] = [{'thumbprint': adapter_instance_ssl_info['stdout']}]
            else:
                if has_cert:
                    vra_stdout_thumbprints[vra_adapter_name].append({'thumbprint': adapter_instance_ssl_info['stdout']})
    return vra_stdout_thumbprints


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_adapter_data=dict(required=True, type='list', default=None),
            openssl_certificate_data=dict(required=True, type='list', default=None),
            adapter_responses=dict(required=True, type='list', default=None)
        )
    )
    vrops_adapter_data = module.params.get('vrops_adapter_data')
    openssl_certificate_data = module.params.get('openssl_certificate_data')
    adapter_responses = module.params.get('adapter_responses')
    adapters_exist = []
    vra_stdout_thumbprints = get_vra_stdout_thumbprints(openssl_certificate_data)
    try:
        for adapter in vrops_adapter_data:
            adapter_found = False
            for adapter_instance_ssl_info in openssl_certificate_data:
                if adapter['resourceKey']['name'] == adapter_instance_ssl_info['item']['resourceKey']['name']:
                    already_exists = vra_adapter_already_exists(adapter_responses, adapter['resourceKey']['name'])
                    adapters_exist.append({'name': adapter['resourceKey']['name'], 'exists': already_exists})
                    if adapter['resourceKey']['resourceKindKey'] == 'VCACAdapter Instance':
                        if already_exists is False:
                            for response in adapter_responses:
                                if response.get('json', None):
                                    if response['json'].get('resourceKey', None):
                                        if adapter['resourceKey']['name'] == response['json']['resourceKey']['name']:
                                            adapter['adapter-certificates'] = []
                                            for cert in response['json'].get('adapter-certificates', []):
                                                adapter['adapter-certificates'].append({'thumbprint': cert['thumbprint']})
                        else:
                            # This vra adapter already has been added, retrieved thumbprints
                            adapter['adapter-certificates'] = vra_stdout_thumbprints[adapter['resourceKey']['name']]
                    else:
                        adapter['adapter-certificates'] = [{'thumbprint': adapter_instance_ssl_info['stdout']}]

                    # If we failed to reach the VC, the rc != 0 and we won't do anything with it
                    if adapter_instance_ssl_info['rc'] == 0:
                        adapter_found = True

            if adapter_found is False:
                vrops_adapter_data.remove(adapter)
    except Exception as e:
        module.fail_json(msg="combine_thumbprints exception: " + str(e))

    module.exit_json(msg=vrops_adapter_data)


if __name__ == "__main__":
    main()
