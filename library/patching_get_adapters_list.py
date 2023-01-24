#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def get_adapter_description(adapter_instance_name, adapter_instance_type):
    # {{ item.name }} {{ item.type }} adapter instance
    return adapter_instance_name + ' ' + adapter_instance_type + ' adapter instance'


def main():
    module = AnsibleModule(
        argument_spec=dict(
            solutions=dict(required=True, type='dict', default=None),
            current_adapters_from_api=dict(required=True, type='list', default=None)
        )
    )

    # This python module takes the following inputs:
    # solutions: list of all the vrops solutions
    # current_adapters_from_api: list of adapters currently defined in vrops

    # This module takes the environment-specified set of vROps solutions (which are
    # management packs and their adapter instances) and compares it with the list of
    # adapter instances returned by the vROps API. If there are any that were defined
    # in the environment-specified list of solutions that are not in the vROps API
    # data, then return those adapter instance ID's (with the expectation that they
    # will be deleted later)

    solutions = module.params.get('solutions')
    current_adapters_from_api = module.params.get('current_adapters_from_api')
    adapter_instance_ids_to_delete = []
    # This is done to prevent deletion of system-created adapter instances as well as
    # any solutions that have adapter instances that are not managed by our automation.
    adapter_kind_keys_to_delete = ['VMWARE', 'VCACAdapter', 'HPOneviewVCopsAdapter3']
    # Do not add SDDCHealthAdapter to adapter_kind_keys_to_delete, See issue #286
    # TODO: add more types of adapter instances to adapter_kind_keys_to_delete
    try:
        for current_adapter in current_adapters_from_api:
            # The following code will try to find each adapter instance by its name
            _current_adapter_is_defined = False
            # Set this to False in advance.
            adapter_should_be_deleted = False
            # Is this a deletable adapter instance?
            deletable_adapter_type = current_adapter['resourceKey']['adapterKindKey'] in adapter_kind_keys_to_delete
            if deletable_adapter_type is True:
                # Iterate over every solution in our environment config
                # Then check if the adapter instances for that solution are defined as a dictionary,
                # or as a boolean (i.e. SDDC just sets True)
                for solution in solutions.keys():
                    if isinstance(solutions[solution]['adapter_instances'], dict):
                        for adapter_instance_name in solutions[solution]['adapter_instances'].keys():
                            # If needed, here's how to get the current adapter instance object from config
                            # adapter_instance = solutions[solution]['adapter_instances'][adapter_instance_name]
                            # Check if the adapter instance's names match. Note: All adapter instances must have unique names.
                            try:
                                if current_adapter['resourceKey']['name'].strip().lower() == adapter_instance_name.strip().lower():
                                    _current_adapter_is_defined = True
                            except Exception as e:
                                # If there was an exception and this was an adapter instance we're responsible for,
                                # fail out!
                                module.fail_json(msg=str("patching_get_adapters_list.py failed to process the " +
                                                         adapter_instance_name + " adapter instance from the vROps API: " + str(current_adapter) +
                                                         '   - The python exception is this: ' + str(e)))
                    elif isinstance(solutions[solution], bool):
                        if solutions[solution]['adapter_instances'] is False:
                            # If the current solution (vsphere/vra/etc) has adapter_instances: False,
                            # and this is a deletable adapter type, then schedule it for deletion.
                            adapter_should_be_deleted = True
            # If the adapter instance couldn't be found in our defined environment's solutions,
            # and it is an adapter type that we are responsible for, then schedule it for deletion.
            if deletable_adapter_type is True and _current_adapter_is_defined is False:
                adapter_should_be_deleted = True
            # If the adapter should be deleted, put its ID in the output list for this module.
            if adapter_should_be_deleted is True:
                adapter_instance_ids_to_delete.append(current_adapter['id'])
    except Exception as e:
        module.fail_json(msg="patching_get_adapters_list exception: " + str(e))
    module.exit_json(msg=adapter_instance_ids_to_delete)


if __name__ == "__main__":
    main()
