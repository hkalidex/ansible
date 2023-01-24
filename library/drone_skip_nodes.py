#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_node_exists=dict(required=True, type='list', default=None),
        )
    )

    # This python module takes the following inputs:
    # vrops_node_exists: list of results from does_vm_exist module as
    # run by a previous ansible task.

    # NOTE: This module is only ever run when Drone is running a build.
    # This module determines if a vrops_node should be skipped based on
    # whether or not it has "drone_skip: True" field set.
    # This module needed to be created because Ansible "when" statements
    # were not working.

    vrops_node_exists = module.params.get('vrops_node_exists')

    output_list = []

    try:
        for vrops_node_exists_result in vrops_node_exists:
            _node_should_be_skipped = False
            try:
                if vrops_node_exists_result['item']['value']['drone_skip'] is True:
                    _node_should_be_skipped = True
            except:
                pass
            if _node_should_be_skipped is False:
                output_list.append(vrops_node_exists_result)
    except Exception as e:
        module.fail_json(msg='drone_skip_nodes exception: ' + str(e))
    module.exit_json(msg={'results': output_list})


if __name__ == "__main__":
    main()
