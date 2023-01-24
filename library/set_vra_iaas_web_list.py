#!/usr/bin/env python

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vra_iaas_web_instances=dict(required=True, type='list', default=None)
        )
    )
    vra_iaas_web_instances = module.params.get('vra_iaas_web_instances')
    vra_iaas_web_thumbprint_list = []
    added = []

    try:
        for result in vra_iaas_web_instances:
            if 'ansible_facts' in result.keys():
                for vra_iaas_web_instance in result['ansible_facts']['iaas_web']['iaas']:
                    instance_name = result['ansible_facts']['iaas_web']['iaas'][vra_iaas_web_instance]['name']
                    vra_adapter = result['ansible_facts']['iaas_web']['parent']
                    if instance_name not in added:
                        vra_iaas_web_thumbprint_list.append({'resourceKey': {'name': instance_name, 'vra_adapter': vra_adapter, 'resourceKindKey': 'CUSTOM IaaS Web'}})
                        added.append(instance_name)
    except Exception as e:
        module.fail_json(msg="ERROR in set_vra_iaas_web_list.py  exception: {}".format(e))

    module.exit_json(msg=vra_iaas_web_thumbprint_list)


if __name__ == "__main__":
    main()
