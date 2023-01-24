#!/usr/bin/env python
from time import sleep
import requests
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            response=dict(required=True, type='list', default=None),
            user=dict(required=True, type='str'),
            password=dict(required=True, type='str')
        )
    )

    response = module.params.get('response')
    user = module.params.get('user')
    password = module.params.get('password')

    status_url = ''

    # If response is None
    if not response:
        module.exit_json(msg='There is no upgrade in progress')

    try:
        # Get status url from response
        for data in response:
            if data['rel'] == 'pak_cluster_status':
                status_url = data['href']

    except Exception as e:
        module.fail_json(msg='Error obtaining url upgrade status: {0}'.format(e))

    # Check cluster_pak_install_status is equal to COMPLETED
    incomplete = True
    tries = 0

    while incomplete and tries <= 9:

        try:
            r = requests.get(status_url, auth=(user, password), verify=False)

            if r.status_code == 200:
                upgrade_status = r.json()

                if upgrade_status['cluster_pak_install_status'] == "COMPLETED":
                    incomplete = False
                    continue
        except requests.exceptions.ConnectionError:
            pass

        tries = tries + 1
        sleep(600)

    if incomplete and tries == 9:
        module.fail_json(msg='Timeout upgrading vROps')

    module.exit_json(msg='Upgrade was successfully completed')


if __name__ == "__main__":
    main()
