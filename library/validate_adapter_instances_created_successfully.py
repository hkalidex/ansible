#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def get_adapter_description(adapter_instance_name, adapter_instance_type):
    return adapter_instance_name + ' (' + adapter_instance_type + ' adapter instance)'


def main():
    module = AnsibleModule(
        argument_spec=dict(
            solutions=dict(required=True, type='dict', default=None),
            current_adapters_from_api=dict(required=True, type='list', default=None),
            current_collectors=dict(required=True, type='dict', default=None),
            vrops_nodes=dict(required=True, type='dict', default=None)
        )
    )

    # This python module takes the following inputs:
    # solutions: list of all the vrops solutions
    # current_adapters_from_api: list of adapters currently defined in vrops

    # This module takes the environment-specified set of vROps solutions (which are
    # management packs and their adapter instances) and compares it with the list of
    # adapter instances returned by the vROps API. If there are any that were defined
    # in the environment-specified list of solutions that are not in the vROps API
    # data, then fail.

    solutions = module.params.get('solutions')
    current_adapters_from_api = module.params.get('current_adapters_from_api')
    vrops_nodes = module.params.get('vrops_nodes')
    current_collectors = module.params.get('current_collectors')

    adapter_instances_not_created_successfully = []

    try:
        # Iterate over each vROps solution
        for solution in solutions.keys():
            # Iterate over each vROps solution's adapter_instances object
            if isinstance(solutions[solution]['adapter_instances'], dict):
                for adapter_instance_name in solutions[solution]['adapter_instances'].keys():
                    # If needed, here's how to get the adapter_instance object
                    # adapter_instance = solutions[solution]['adapter_instances'][adapter_instance_name]
                    # Try to find the adapter instance by its name, which is unique.
                    _adapter_instance_was_created_successfully = False
                    for current_adapter_from_api in current_adapters_from_api:
                        try:
                            if current_adapter_from_api['resourceKey']['name'].strip().lower() == adapter_instance_name.strip().lower():
                                _adapter_instance_was_created_successfully = True
                        except:
                            pass
                    # If we couldn't find it, put the adapter instance description into the list of failure output
                    if _adapter_instance_was_created_successfully is False:
                        adapter_instances_not_created_successfully.append(get_adapter_description(adapter_instance_name, solution))
            if isinstance(solutions[solution]['adapter_instances'], bool):
                if solutions[solution]['adapter_instances'] is True:
                    if solution == 'sddc':
                        try:
                            for vrops_node_key in vrops_nodes.keys():
                                _adapter_instance_was_created_successfully = False
                                _collector_id = -1
                                vrops_node = vrops_nodes[vrops_node_key]
                                if vrops_node['role'] == 'master' or vrops_node['role'] == 'data':
                                    for vrops_collector in current_collectors['json']['collector']:
                                        if vrops_node['name'] == vrops_collector['name'].split('vRealize Operations Manager Collector-')[1]:
                                            _collector_id = vrops_collector['id']
                                            for current_adapter_from_api in current_adapters_from_api:
                                                if current_adapter_from_api['resourceKey']['name'] == 'SDDC Health Adapter Instance - ' + _collector_id:
                                                    _adapter_instance_was_created_successfully = True
                                    if _adapter_instance_was_created_successfully is False:
                                        adapter_instances_not_created_successfully.append(get_adapter_description('SDDC Health Adapter Instance - ' + _collector_id, solution))
                        except Exception as e:
                            module.fail_json(msg="sddc_adapter_was_not_created exception: {}".format(str(e)))
                    else:
                        pass
                if solutions[solution]['adapter_instances'] is False:
                    pass
    except Exception as e:
        module.fail_json(msg='validate_adapter_instances_created_successfully exception: ' + str(e))
    if len(adapter_instances_not_created_successfully) > 0:
        module.fail_json(msg='The following adapter instances were not created successfully in vROps: ' + ', '.join(adapter_instances_not_created_successfully))
    module.exit_json(msg="All adapters were created successfully in vROps! Wooooo!")


if __name__ == "__main__":
    main()
