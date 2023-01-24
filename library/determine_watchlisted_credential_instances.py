#!/usr/bin/env python
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            credential_instances=dict(required=True, type='list', default=None),
            credential_watchlist=dict(required=True, type='list', default=None)
        )
    )
    credential_instances = module.params.get('credential_instances')
    credential_watchlist = module.params.get('credential_watchlist')
    purgeable_credentials = []
    protected_credentials = []
    updateable_credentials = []
    try:
        # Before this module existed, whenever the vrops_credentials tasks get run, they will destroy the
        # maintenanceAdmin credential instance and break some super important things, requiring a
        # VA pak file reinstall of the same version. See issue #214.
        # Rally: DE608 https://rally1.rallydev.com/#/95416637724d/detail/defect/176298984760

        # Take note of whether or not purge_all is defined
        purge_all = False
        for watchlisted_credential in credential_watchlist:
            try:
                if watchlisted_credential['action'] == 'purge_all':
                    purge_all = True
            except:
                module.fail_json(msg="An action was not defined for this item in credential_watchlist: " + str(watchlisted_credential))

        for credential_instance in credential_instances:
            actionable_credential = False
            for watchlisted_credential in credential_watchlist:
                # Try to safely get the action from this credential_watchlist item, defaulting to protect
                action = 'protect'
                try:
                    action = watchlisted_credential['action']
                except:
                    pass

                if action != 'purge_all':
                    try:
                        # Iterate over the keypairs and check for matches.
                        keypair_keys = False
                        # Safely get the fields
                        try:
                            keypair_keys = watchlisted_credential['keypairs'].keys()
                        except:
                            pass
                        num_keypairs_matched_count = 0
                        matched_all_keypairs = False
                        if keypair_keys is not False:
                            for keypair_key in keypair_keys:
                                keypair_value = watchlisted_credential['keypairs'][keypair_key]
                                if credential_instance[keypair_key] == keypair_value:
                                    num_keypairs_matched_count += 1
                            if num_keypairs_matched_count == len(keypair_keys):
                                matched_all_keypairs = True
                        else:
                            # If there were no keypairs specified, then logically,
                            # the processing of keypairs doesn't matter. And so
                            # it's OK to set matched_all_keypairs = True.
                            #
                            # If this is to be an "actionable" credential, i.e.,
                            # something we can either protect/purge/etc based on
                            # the filter of keypairs/fields, all specified keypairs
                            # AND fields must be matched with what is specified in
                            # this credential in group_vars/all.yml.
                            #
                            # Given the above context, if no keypairs are specified,
                            # then there is no filter applied to the keypairs,
                            # and there is nothing to match. So by default,
                            # a credential with no keypairs specified will always
                            # be considered "actionable", if filtering only on keypairs.
                            matched_all_keypairs = True

                        # Identical to the above, but with a slightly different mechanism.
                        # vROps credential instances have a "fields" dictionary
                        # that contains name/value pairs, typically containing user/passwords

                        watchlisted_credential_fields = False
                        # Safely get the fields
                        try:
                            watchlisted_credential_fields = watchlisted_credential['fields']
                        except:
                            pass
                        num_fields_matched_count = 0
                        matched_all_fields = False
                        if watchlisted_credential_fields is not False:
                            for whitelisted_field in watchlisted_credential_fields:
                                for credential_field in credential_instance['fields']:
                                    if (whitelisted_field['name'] == credential_field['name'] and
                                       whitelisted_field['value'] == credential_field['value']):
                                        num_fields_matched_count += 1
                            if num_fields_matched_count == len(watchlisted_credential_fields):
                                matched_all_fields = True
                        else:
                            # (the following is just a copy/paste from above)
                            #
                            # If there were no fields specified, then logically,
                            # the processing of fields doesn't matter. And so
                            # it's OK to set matched_all_fields = True.
                            #
                            # If this is to be an "actionable" credential, i.e.,
                            # something we can either protect/purge/etc based on
                            # the filter of fields/keypairs, all specified fields
                            # AND keypairs must be matched with what is specified in
                            # this credential in group_vars/all.yml.
                            #
                            # Given the above context, if no fields are specified,
                            # then there is no filter applied to the fields,
                            # and there is nothing to match. So by default,
                            # a credential with no fields specified will always
                            # be considered "actionable", if filtering only on fields.
                            matched_all_fields = True

                        # Wrap it all up
                        #
                        # This statement is the driving reason for why we had to
                        # set matched_all_fields and matched_all_keypairs to True
                        # when there were no fields/keypairs specified earlier.
                        #
                        # In order for us to consider a credential to be "actionable",
                        # i.e. protectable/purgeable, logically we must have
                        # matched all of the fields/keypairs given by the user in
                        # group_vars/all.yml with the fields/keypairs in the current
                        # credential instance.
                        #
                        # The scenario where there are no fields/keypairs specified
                        # is the same as matching everything, hence it becomes "actionable",
                        # and hence matched_all_fields and matched_all_keypairs are both True.
                        #
                        # Note: This scenario should never happen in practice!
                        #       Be as specific as possible when adding items to
                        #       the credential_watchlist object in group_vars/all.yml.
                        if (matched_all_fields is True and matched_all_keypairs is True):
                            actionable_credential = True

                    except Exception as e:
                        # If we encounter an exception in the above code,
                        # it's probably a new type of credential, and we shouldn't touch it just to be safe
                        actionable_credential = True
                        action = 'protect'
                        # But we're going to throw an exception anyway
                        module.fail_json(msg="determine_watchlisted_credential_instances module exception when processing credential: " + str(e), meta=credential_instance)

            if actionable_credential is True:
                if action == 'protect':
                    protected_credentials.append(credential_instance)
                    updateable_credentials.append(credential_instance)
                elif action == 'purge':
                    purgeable_credentials.append(credential_instance)
                elif purge_all is True:
                    purgeable_credentials.append(credential_instance)
            else:
                if purge_all is True:
                    purgeable_credentials.append(credential_instance)
                else:
                    protected_credentials.append(credential_instance)
                    updateable_credentials.append(credential_instance)
    except Exception as e:
        module.fail_json(msg="determine_watchlisted_credential_instances module threw an exception: " + str(e))
    results = {
        'purgeable_credentials': purgeable_credentials,
        'protected_credentials': protected_credentials,
        'updateable_credentials': updateable_credentials
    }
    module.exit_json(msg=results, protected_credentials=protected_credentials, purgeable_credentials=purgeable_credentials, updateable_credentials=updateable_credentials)


if __name__ == "__main__":
    main()
