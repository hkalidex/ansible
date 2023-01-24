#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_nodes=dict(required=True, type='dict', default=None),
            vrops_collectors_from_api=dict(required=True, type='list', default=None),
        )
    )
    vrops_nodes = module.params.get('vrops_nodes')
    vrops_collectors_from_api = module.params.get('vrops_collectors_from_api')
    try:
        collector_groups = []
        for vrops_node_key in vrops_nodes.keys():
            vrops_node = vrops_nodes[vrops_node_key]
            if vrops_node['role'] == 'collector':
                for vrops_collector in vrops_collectors_from_api:
                    if vrops_node['name'] in vrops_collector['name'].split('vRealize Operations Manager Collector-')[1]:
                        _collector_group_found = False
                        for collector_group in collector_groups:
                            if collector_group['name'] == vrops_node['collector_group']:
                                if vrops_collector['id'] not in collector_group['collectorId']:
                                    collector_group['collectorId'].append(vrops_collector['id'])
                                _collector_group_found = True
                        if _collector_group_found is False:
                            collector_groups.append({
                                'id': None,
                                'name': vrops_node['collector_group'],
                                'description': vrops_node['collector_group'],
                                'collectorId': [vrops_collector['id']],
                                'systemDefined': False,
                                'others': [],
                                'otherAttributes': {
                                }
                            })
                            # for collector_id in collector_group['collectorId']:
                            #     if collector_id == vrops_collector['id']:
                # if _collector_group_found == False:
                #     vrops_adapter_data.remove(adapter)
    except Exception as e:
        module.fail_json(msg="determine_collector_groups module exception: " + str(e))
    module.exit_json(msg=collector_groups)


if __name__ == "__main__":
    main()
