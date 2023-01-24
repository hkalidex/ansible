#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_node_exists_results=dict(required=True, type='list', default=None),
        )
    )

    # This python module takes the following inputs:
    # vrops_node_exists_results: list of results from does_vm_exist module as
    # run by a previous ansible task.

    vrops_node_exists_results = module.params.get('vrops_node_exists_results')

    output_dict = {}

    try:
        for vrops_node_exists_result in vrops_node_exists_results:
            try:
                if vrops_node_exists_result.get('msg', None) != 'Appliance exists!':
                    # Get the key from the original result
                    _key = vrops_node_exists_result.get('async_result_item', {}).get('item', {}).get('key', None)
                    _value = vrops_node_exists_result.get('async_result_item', {}).get('item', {}).get('value', None)
                    output_dict[_key] = _value
            except Exception as ex:
                module.fail_json(msg='filter_out_existing_nodes_for_ova_deploy_paths exception for an item: {}\nItem: {}'.format(str(ex), str(vrops_node_exists_result)))
    except Exception as e:
        module.fail_json(msg='filter_out_existing_nodes_for_ova_deploy_paths exception: {}'.format(str(e)))
    module.exit_json(msg=output_dict)


if __name__ == "__main__":
    main()
