#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def id_exists_in_list(id, list_target):
    for item in list_target:
        if item['id'] == id:
            return True
    return False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_credential_instances_purgeable=dict(required=True, type='list', default=None),
            vrops_credential_instances_updateable=dict(required=True, type='list', default=None),
            credentials_list=dict(required=True, type='list', default=None)
        )
    )
    # The data in vrops_credential_instances_purgeable/updateable must be pre-filtered by checking the credential_watchlist
    # See vrops_credentials tag to see the module that does this
    vrops_credential_instances_purgeable = module.params.get('vrops_credential_instances_purgeable')
    vrops_credential_instances_updateable = module.params.get('vrops_credential_instances_updateable')

    # Pre-work: combine vrops_credential_instances_purgeable and vrops_credential_instances_updateable into one.
    vrops_credential_instances = []
    for i in vrops_credential_instances_purgeable:
        i['_purgeable'] = True
        i['_updateable'] = False
        vrops_credential_instances.append(i)
    for i in vrops_credential_instances_updateable:
        i['_updateable'] = True
        i['_purgeable'] = False
        vrops_credential_instances.append(i)

    credentials_list = module.params.get('credentials_list')
    output = {
        'updateable': [],
        'deletable': []
    }

    # Define some constants
    # These are used to help map the important values from the credentials_list (defined in the env config)
    # to the resulting output API call body
    # TODO: Move this to group_vars/all.yml or just do it in a way that's smarter
    vra_type = 'vra'
    vra_cred_set = ['sysadmin_username', 'sysadmin_password', 'superuser_username', 'superuser_password']
    vra_adapterkindkey = 'VCACAdapter'
    # vSphere Credentials
    vc_type = 'vc'
    vc_cred_set = ['username', 'password']
    vc_adapterkindkey = 'VMWARE'
    pythonvc_adapterkindkey = 'PythonRemediationVcenterAdapter'
    pythonvc_type = 'pythonvc'
    # HPE OneView
    hpov_type = 'hpeoneview'
    hpov_adapterkindkey = 'HPOneviewVCopsAdapter3'
    hpov_cred_set = ['username', 'password', 'vrops_username', 'vrops_password', 'directory']

    # The adapterkindkey_mappings dict converts vROps adapterKindKeys to our internally-defined
    # credential types
    adapterkindkey_mappings = {
        vc_adapterkindkey: vc_type,
        vra_adapterkindkey: vra_type,
        pythonvc_adapterkindkey: pythonvc_type,
        hpov_adapterkindkey: hpov_type
    }

    try:
        # Start with the credentials that are defined in vROps.
        # Check if each credential has a corresponding definition in our environment.
        # If not, delete it. If yes, update the credential with our current password.
        # Any credentials that are in our environment but not in vROps get created later.
        for vrops_credential_instance in vrops_credential_instances:
            # Refactoring - these values get used frequently.
            credential_is_defined = False
            credential_id = vrops_credential_instance['id']
            credential_adapterkindkey = vrops_credential_instance['adapterKindKey']
            credential_kindkey = vrops_credential_instance['credentialKindKey']
            # Begin iterating over our locally defined credentials list.
            for credential in credentials_list:
                # if one of our environment-defined credentials' names matches a record we got from the vROps API,
                # and we haven't already encountered it, process the record such that the data we will send to the vROps API
                # will contain the username/password in our environment config

                # TODO: Improve this code, which was copied from associate_adapter_credential_ids.py
                # Safely try to see if this is either a vcenter or vrealize_automation
                # adapter instance by checking our adapterkindkey_mappings.
                mapped_credential_type = ''
                try:
                    mapped_credential_type = adapterkindkey_mappings[credential_adapterkindkey]
                except:
                    # If the above line threw an exception, it's likely just an adapter kind
                    # that we don't care about right now
                    pass
                # If the credential matches by name, type, and we haven't already found it,
                # proceed.
                if (credential['name'] == vrops_credential_instance['name'] and
                   credential['type'] == mapped_credential_type and
                   id_exists_in_list(credential_id, output['updateable']) is False and
                   vrops_credential_instance['_updateable'] is True):
                    credential_type = credential['type']
                    # We don't create PythonRemediationVcenterAdapter instances but vROps does,
                    # whenever someone updates the vCenter Adapter instance through the UI.
                    # See issue #164.
                    # The pythonvc credential type is something used internally to our automation.
                    if credential_kindkey == pythonvc_adapterkindkey:
                        credential_type = pythonvc_type

                    # Start with a skeleton structure.
                    credential_to_update = {
                        'id': credential_id,
                        'name': credential['name'],
                        'type': credential_type,
                        'adapterKindKey': credential_adapterkindkey,
                        'credentialKindKey': credential_kindkey
                    }
                    # Set the username/password fields as appropriate for the type of credential
                    # For example vRA credentials have 4 values but VC credentials have 2
                    cred_set = []
                    if credential['type'] == vc_type or credential['type'] == pythonvc_type:
                        cred_set = vc_cred_set
                    if credential['type'] == vra_type:
                        cred_set = vra_cred_set
                    if credential['type'] == hpov_type:
                        cred_set = hpov_cred_set
                    # Now using the cred_set from above, map the values of our locally-defined credential data
                    # to the soon-to-be-outgoing body of the API call (which is mapped from credential_to_update later)
                    for i in cred_set:
                        credential_to_update[i] = credential[i]
                    output['updateable'].append(credential_to_update)
                    credential_is_defined = True

            # If we weren't able to find the credential in our environment config, but it exists in vROps, prepare to delete it from vROps.
            if (credential_is_defined is False and
               id_exists_in_list(credential_id, output['deletable']) is False and
               vrops_credential_instance['_purgeable'] is True):
                # Start with a skeleton structure.
                credential_to_delete = {
                    'id': credential_id,
                    'name': credential['name'],
                    'type': credential['type']
                }

                output['deletable'].append(credential_to_delete)
    except Exception as e:
        module.fail_json(msg="patching_get_credentials_list exception: " + str(e))
    module.exit_json(msg=output, deletable=output['deletable'], updateable=output['updateable'])


if __name__ == "__main__":
    main()
