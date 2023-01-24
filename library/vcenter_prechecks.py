#!/usr/bin/env python

import atexit
import ssl
import yaml
import os
import requests
from ansible.module_utils.basic import AnsibleModule


try:
    from pyVim import connect
    from pyVmomi import vim
    pyvmomi_import_failure = False
except ImportError:
    pyvmomi_import_failure = True


def load_yml(yml_file):
    try:
        with open(yml_file, 'r') as f:
            env_yml = yaml.load(f)
    except IOError:
            env_yml = None

    return env_yml


def get_vc_connection(vc, username, password):
    service_instance = None
    error_message = ''
    # Disable ssl verification for python >= 2.7.9
    context = None

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
    except:
        pass

    try:
        service_instance = connect.SmartConnect(host=vc,
                                                user=username,
                                                pwd=password,
                                                sslContext=context)
        atexit.register(connect.Disconnect, service_instance)
    except Exception as e:
        error_message = str(e)

    return {'service_instance': service_instance, 'error': error_message}


def get_container_view(vc_connection, view_type):
    content = vc_connection.RetrieveContent()
    container = content.rootFolder
    recursive = True
    container_view = content.viewManager.CreateContainerView(container, view_type, recursive)
    return container_view


def network(vc_connection, network_name=''):
    networks = []
    result = {
        'status': 'ok'
    }

    vimtype = [vim.HostSystem]
    hosts = (get_container_view(vc_connection, vimtype)).view

    for host in hosts:
        for network in host.network:
            networks.append(network.name)

    if network_name not in networks:
        result['status'] = 'failed'
        result['err_description'] = 'Network name does not exist. Existing networks: {0}'.format(networks)

    return result


def datacenter(vc_connection, datacenter_name=''):
    datacenters = []
    result = {
        'status': 'ok'
    }

    vimtype = [vim.Datacenter]
    datacenters = [datacenter.name for datacenter in (get_container_view(vc_connection, vimtype)).view]

    if datacenter_name not in datacenters:
        result['status'] = 'failed'
        result['err_description'] = 'Datacenter name does not exist. Existing datacenters: {0}'.format(datacenters)

    return result


def cluster(vc_connection, cluster_name=''):
    clusters = []
    result = {
        'status': 'ok'
    }

    vimtype = [vim.ClusterComputeResource]
    clusters = [cluster.name for cluster in (get_container_view(vc_connection, vimtype)).view]

    if cluster_name not in clusters:
        result['status'] = 'failed'
        result['err_description'] = 'Cluster name does not exist. Existing clusters: {0}'.format(clusters)

    return result


def get_datastores(vc_connection):
    datastores = []

    # Unneeded
    # result = {
    #     'status': 'ok'
    # }

    vimtype = [vim.Datastore]
    datastores = [
        {
            'name': datastore.info.name,
            'freeSpace': datastore.info.freeSpace
        } for datastore in (get_container_view(vc_connection, vimtype)).view
    ]

    return datastores


def datastore(vc_connection, datastore_name=''):
    datastores = []
    result = {
        'status': 'ok'
    }

    for datastore in get_datastores(vc_connection):
        if datastore_name == datastore.get('name'):
            return result
        datastores.append(datastore.get('name'))

    return {
        'status': 'failed',
        'err_description': 'Datastore name {0} does not exist. Existing datastores: {1}'.format(datastore_name, datastores)
    }


def datastore_space(vc_connection, datastore_name='', datastore_space=''):
    freespace_GB = 0
    result = {
        'status': 'ok'
    }

    for datastore in get_datastores(vc_connection):
        if datastore_name == datastore.get('name'):

            freespace_GB = (((datastore.get('freeSpace') / 1024) / 1024) / 1024)

            if freespace_GB >= float(datastore_space):
                return result
            else:
                break

    return {
        'status': 'failed',
        'err_description': 'Current datastore space is: {0} GB but required is: {1} GB'.format(freespace_GB, datastore_space)
    }


def get_permissions(vc_connection):
    auth_manager = vc_connection.content.authorizationManager

    return [
        {
            'principal': permission.principal,
            'roleId': permission.roleId
        }
        for permission in auth_manager.RetrieveAllPermissions()
    ]


def usergroup(vc_connection, usergroup=''):
    usersgroups = []
    result = {
        'status': 'ok'
    }

    for permission in get_permissions(vc_connection):
        if usergroup == permission.get('principal'):
            return result

        usersgroups.append(permission.get('principal'))

    return {
        'status': 'failed',
        'err_description': 'usergroup name does not exist. Existing usersgroups: {0}'.format(usersgroups)
    }


def get_role(vc_connection, role_id=None):
    auth_manager = vc_connection.content.authorizationManager

    roles = [
        {
            'name': role.name,
            'roleId': role.roleId,
            'priviliges': role.privilege
        } for role in auth_manager.roleList
    ]

    if role_id:
        return next(role for role in roles if role.get('roleId') == role_id)

    return roles


def usergroup_priviliges(vc_connection, usergroup=''):
    ova_priviliges = [
        'VirtualMachine.Inventory.Create',
        'VirtualMachine.Config.AddNewDisk',
        'VirtualMachine.Provisioning.DeployTemplate',
        'Resource.AssignVMToPool',
        'Datastore.AllocateSpace',
        'Network.Assign'
    ]
    result = {
        'status': 'ok'
    }

    description_priviliges = ''

    for permission in get_permissions(vc_connection):
        if usergroup == permission.get('principal'):
            # Check priviliges
            role = get_role(vc_connection, permission.get('roleId'))
            results = [p in role.get('priviliges') for p in ova_priviliges]

            if False in results:
                description_priviliges = '(Current priviliges: {0})'.format(['{0}: {1}'.format(ova_priviliges[i], results[i]) for i in range(0, len(ova_priviliges))])
                break
            else:
                return result

    return {
        'status': 'failed',
        'err_description': description_priviliges
    }


def ova(ova_path=''):
    result = {
        'status': 'ok'
    }

    if os.path.exists(ova_path):
        return result
    else:
        try:
            if requests.head(ova_path, verify=False).status_code == 200:
                return result
        except requests.exceptions.MissingSchema:
            pass

    return {
        'status': 'failed',
        'err_description': 'OVA does not exist in this location: {0}'.format(ova_path)
    }


def run_checks(node):
    check_results = {}

    vc_connection = get_vc_connection(
        node.get('vc'),
        node.get('user'),
        node.get('password'))

    if vc_connection.get('service_instance'):
        check_results['connection'] = {
            'status': 'ok'
        }

        check_results['network'] = network(vc_connection.get('service_instance'), node.get('network'))
        check_results['datacenter'] = datacenter(vc_connection.get('service_instance'), node.get('datacenter'))
        check_results['cluster'] = cluster(vc_connection.get('service_instance'), node.get('cluster'))
        check_results['datastore'] = datastore(vc_connection.get('service_instance'), node.get('datastore'))
        check_results['datastore_space'] = datastore_space(vc_connection.get('service_instance'), node.get('datastore'), node.get('datastore_space'))
        check_results['usergroup'] = usergroup(vc_connection.get('service_instance'), node.get('usergroup'))
        check_results['usergroup_priviliges'] = usergroup_priviliges(vc_connection.get('service_instance'), node.get('usergroup'))
        check_results['ova'] = ova(node.get('ova'))
    else:
        check_results['connection'] = {
            'status': 'failed',
            'err_description': vc_connection.get('error')
        }
    return check_results


def main():
    module = AnsibleModule(
        argument_spec=dict(
            yml_file=dict(required=True, type='str', default=None),
            amr_username=dict(required=True, type='str', default=None),
            amr_password=dict(required=True, type='str', default=None),
            amr_vc_usergroup=dict(required=True, type='str', default=None),
            ed_username=dict(required=True, type='str', default=None),
            ed_password=dict(required=True, type='str', default=None),
            ed_vc_usergroup=dict(required=True, type='str', default=None),
            datastore_space=dict(required=False, type='int', default=274)
        )
    )

    result = {}

    # Get arguments
    yml_file = module.params.get('yml_file')
    amr_username = module.params.get('amr_username')
    amr_password = module.params.get('amr_password')
    amr_vc_usergroup = module.params.get('amr_vc_usergroup')
    ed_username = module.params.get('ed_username')
    ed_password = module.params.get('ed_password')
    ed_vc_usergroup = module.params.get('ed_vc_usergroup')
    datastore_space = module.params.get('datastore_space')

    if pyvmomi_import_failure is True:
        module.fail_json(msg='pyVmomi is required')

    # Load vrops env yml
    env_yml = load_yml(yml_file)

    if not env_yml:
        module.fail_json(msg='env_yml yml file could not be loaded')

    # Get ova path from yml
    ova = '{0}/{1}'.format(env_yml.get('vrops_ova_location'), env_yml.get(
        'vrops_ova_name'))

    amr_vc_usergroup = amr_vc_usergroup.replace('amr\\', 'AMR\\')
    ed_vc_usergroup = ed_vc_usergroup.replace('ed\\', 'ED\\')

    # Run checks
    for key in env_yml.get('vrops_nodes'):
        node = env_yml.get('vrops_nodes').get(key)

        # Get master and data nodes info from yml
        datacenter = env_yml.get('mgmt_vc_datacenter')
        cluster = env_yml.get('mgmt_vc_cluster')
        datastore = env_yml.get('mgmt_datastore')
        network = env_yml.get('mgmt_network')

        user = amr_username
        password = amr_password
        usergroup = amr_vc_usergroup

        vc = node.get('vc')

        # Skip vdp node
        # leaving vdp node role in for legacy compatibility as of US8051
        if 'vdp' in key:
            continue

        if 'collector' in key:

            datacenter = node.get('vc_datacenter')
            cluster = node.get('vc_cluster')
            datastore = node.get('datastore')
            network = node.get('network')

            if 'ED_VCENTER_USERNAME' in node.get('username'):
                user = ed_username
                password = ed_password
                usergroup = ed_vc_usergroup

        node_data = {
            'vc': vc,
            'user': user,
            'password': password,
            'usergroup': usergroup,
            'datacenter': datacenter,
            'cluster': cluster,
            'datastore': datastore,
            'network': network,
            'datastore_space': datastore_space,
            'ova': ova
        }

        result[key] = node_data

    # Add check results
    for key in result:
        checks = run_checks(result[key])
        result[key]['checks'] = checks

    # Summary
    connection_failures = 0
    other_failures = 0
    nodes = 0
    summary = {}
    for node_key in result:
        nodes = nodes + 1
        for check_key in result[node_key]['checks']:
            if result[node_key]['checks'][check_key]['status'] is not 'ok':
                if check_key is 'connection':
                    connection_failures = connection_failures + 1
                else:
                    other_failures = other_failures + 1

    summary = {
        'connection_failures': connection_failures,
        'other_failures': other_failures,
        'nodes': nodes
    }

    module.exit_json(results=result, summary=summary)


if __name__ == "__main__":
    main()
