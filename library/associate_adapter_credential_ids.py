#!/usr/bin/env python

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            solutions=dict(required=True, type='dict', default=None),
            current_credentials=dict(required=True, type='list', default=None),
            collector_groups=dict(required=True, type='list', default=None),
            current_adapters=dict(required=True, type='dict', default=None),
            vrops_nodes=dict(required=True, type='dict', default=None),
            current_collectors=dict(required=True, type='dict', default=None)
        )
    )

    # This python module takes the following inputs:
    # solutions: list of all of the vrops solutions in our env file
    # current_credentials: list of all the currently defined credentials in vROps
    # collector_groups: list of all the currently defined collector groups in vROps
    # current_adapters: list of adapters currently defined in vROps
    # vrops_nodes: list of all vrops nodes currently defined in vROps
    # current_collectors: list of all collectors currently defined in vROps

    # This module takes an input set of solutions and their desired adapter instances,
    # as well as credential IDs and collector group IDs from the vROps API, and
    # returns a list containing all of the adapter instances that need to be created.

    # Note that for each type of solution, there are different arguments required; as such,
    # case/switch-like blocks are expected.

    # The adapterkindkey_mappings dict is a quickfix method of distinguishing
    # credentials with the same name but different types. Something similar to this
    # should have been caught in #204 but it wasn't.
    # This quickfix is definitely adding some technical debt, but due to time
    # constraints a more elegant fix is not feasible as of writing this.
    # Basically in vROps API data, the adapter and credential instances
    # have SOMETHING LIKE resourceKey.adapterKindKey == 'VMWARE' and
    # in our environment configs, we have solutions.vcenter or solutions.vrealize_automation
    # This list connects the dots without requiring a ton of changes to environment configs.
    adapterkindkey_mappings = {
        'VMWARE': 'vcenter',
        'VCACAdapter': 'vrealize_automation',
        'HPOneviewVCopsAdapter3': 'hpeoneview',
        'LogInsightAdapter': 'loginsight'
    }

    solutions = module.params.get('solutions')
    current_credentials = module.params.get('current_credentials')
    collector_groups = module.params.get('collector_groups')
    current_adapters = module.params.get('current_adapters')
    vrops_nodes = module.params.get('vrops_nodes')
    current_collectors = module.params.get('current_collectors')
    adapter_instance_instances_to_create = []

    try:
        for solution in solutions.keys():
            # Start by determining if this solution has adapter_instances defined.
            # If it's set to False or undefined, then do not do anything for this solution.
            _solution_has_adapter_instances = False
            try:
                if solutions[solution]['adapter_instances']:
                    _solution_has_adapter_instances = True
            except:
                pass
            if _solution_has_adapter_instances is True:
                if solution == 'epops':
                    pass
                if (solution == 'vcenter' or
                   solution == 'vrealize_automation' or
                   solution == 'hpeoneview'):
                        # For the vCenter, vRA and HPE OneView solutions, we associate a collector group's ID
                        # as well as a credential instance's ID with the adapter instance that
                        # will need to be created.
                        for adapter_instance_name in solutions[solution]['adapter_instances'].keys():
                            adapter_instance = solutions[solution]['adapter_instances'][adapter_instance_name]
                            for credential_instance in current_credentials:
                                # Safely try to see if this is either a vcenter or vrealize_automation
                                # adapter instance by checking our adapterkindkey_mappings.
                                adapter_kind_mapped = ''
                                try:
                                    adapter_kind_mapped = adapterkindkey_mappings[credential_instance['adapterKindKey']]
                                except:
                                    # If the above line threw an exception, it's likely just an adapter kind
                                    # that we don't care about right now, such as PythonRemediationVcenterAdapter.
                                    # We do care about those adapters, but just not right now.
                                    pass
                                if (credential_instance['name'] == adapter_instance['credential'] and
                                   adapter_kind_mapped == solution):
                                    # This code will prevent duplicate adapter instances from being added
                                    # to the adapter_instance_instance_to_create list.
                                    _adapter_instance_instance_found = False
                                    for adapter_instance_instance_to_create in adapter_instance_instances_to_create:
                                        if adapter_instance_instance_to_create['name'] == adapter_instance_name:
                                            _adapter_instance_instance_found = True
                                            # do nothing else since the adapter already is scheduled to be created
                                    # Next, get the collector group ID. Start with the default ID, which is 1 in vROps.
                                    collector_group_id = 1
                                    for collector_group in collector_groups:
                                        if collector_group['name'] == adapter_instance['collector_group']:
                                            collector_group_id = collector_group['id']
                                    # If the adapter instance isn't already scheduled to be created,
                                    # add it to the list of adapter instances to be created
                                    if _adapter_instance_instance_found is False:
                                        new_adapter = {
                                            'name': adapter_instance_name,
                                            'credential_id': credential_instance['id'],
                                            'collector_group_id': collector_group_id,
                                            'type': solution
                                        }
                                        # For vRA adapter instances, the tenant must be defined.
                                        # However for vCenter adapters it is not.
                                        # Similarly, HPE OneView will have an ip_address property,
                                        # but the other types won't have it.
                                        # Try to safely handle this by using try/except/pass.
                                        new_adapter['tenant'] = adapter_instance.get('tenant', None)
                                        new_adapter['ip_address'] = adapter_instance.get('ip_address', None)
                                        # create the new adapter by putting the data in our output list
                                        adapter_instance_instances_to_create.append(new_adapter)
                if solution == 'sddc':
                    try:
                        for vrops_node_key in vrops_nodes.keys():
                            _adapter_instance_found = False
                            _collector_id = -1
                            vrops_node = vrops_nodes[vrops_node_key]
                            if vrops_node['role'] == 'master' or vrops_node['role'] == 'data':
                                for vrops_collector in current_collectors['json']['collector']:
                                    if vrops_node['name'] == vrops_collector['name'].split('vRealize Operations Manager Collector-')[1]:
                                        _collector_id = vrops_collector['id']
                                        for current_adapter in current_adapters['json']['adapterInstancesInfoDto']:
                                            if current_adapter['resourceKey']['name'] == 'SDDC Health Adapter Instance - ' + _collector_id:
                                                _adapter_instance_found = True
                            if _adapter_instance_found is False and _collector_id != -1:
                                new_adapter = {
                                    'id': _collector_id,
                                    'type': solution
                                }
                                if new_adapter not in adapter_instance_instances_to_create:
                                    adapter_instance_instances_to_create.append(new_adapter)
                    except Exception as e:
                        module.fail_json(msg="associate_adapter_credential_ids exception: {} ".format(str(e)))
                if solution == 'vrealize_business':
                    # TODO
                    pass
                if solution == 'loginsight':
                    # Get the collector group ID. Start with the default ID, which is 1 in vROps.
                    collector_group_id = 1
                    for adapter_instance_name in solutions[solution]['adapter_instances'].keys():
                        for collector_group in collector_groups:
                            if collector_group['name'] == adapter_instance['collector_group']:
                                collector_group_id = collector_group['id']
                    new_adapter = {
                        'name': adapter_instance_name,
                        'collector_group_id': collector_group_id,
                        'type': solution
                    }
                    adapter_instance_instances_to_create.append(new_adapter)
    except Exception as e:
        module.fail_json(msg="associate_adapter_credential_ids exception: " + str(e))
    module.exit_json(msg=adapter_instance_instances_to_create)


if __name__ == "__main__":
    main()
