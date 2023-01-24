#!/usr/bin/env python

import atexit
import ssl
from ansible.module_utils.basic import AnsibleModule

try:
    from pyVim import connect
    from pyVmomi import vim
    # from pyVmomi import vmodl
    pyvmomi_import_failure = False
except ImportError:
    pyvmomi_import_failure = True


def get_obj(content, vimtype, name=None):
    return [item for item in content.viewManager.CreateContainerView(
        content.rootFolder, [vimtype], recursive=True).view]


def get_value_from_dict_safely(dictionary, value, default_value):
    return_value = False
    try:
        return_value = dictionary[value]
    except:
        return_value = default_value
    return return_value


def esx_host_active(esx_host):
    # Added for US7519 - Do not return hosts that are inactive
    connection_state = esx_host.summary.runtime.connectionState
    power_state = esx_host.summary.runtime.powerState
    in_maint_mode = esx_host.summary.runtime.inMaintenanceMode
    in_standby = esx_host.summary.runtime.standbyMode
    if (connection_state == "connected") and \
       (power_state == "poweredOn") and \
       (not in_maint_mode) and in_standby == 'none':
        return True
    return False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vrops_nodes=dict(required=True, type='dict', default=None),
            default_vc=dict(required=True, default=None),
            default_cluster=dict(required=True, default=None),
            default_username=dict(required=True, default=None),
            default_password=dict(required=True, default=None),
            vcenter_port=dict(required=False, type='int', default=443)
        )
    )

    if pyvmomi_import_failure is True:
        module.fail_json(msg='pyVmomi is required')

    vrops_nodes = module.params.get('vrops_nodes')
    default_vc = module.params.get('default_vc')
    default_cluster = module.params.get('default_cluster')
    default_username = module.params.get('default_username')
    default_password = module.params.get('default_password')
    vcenter_port = module.params.get('vcenter_port')

    # for extra info in the module output
    extra_log_output = []

    # Iterate over all vrops_nodes and gather their VC's and respective clusters
    vc_cluster_targets = []

    # Keep track of the unique VC's we come across (will save some time in the precheck networking step)
    vcenters = []

    for vrops_node_key in vrops_nodes.keys():
        vrops_node = vrops_nodes[vrops_node_key]
        current_vrops_node_vc = get_value_from_dict_safely(vrops_node, 'vc', default_vc)
        current_vrops_node_cluster = get_value_from_dict_safely(vrops_node, 'vc_cluster', default_cluster)
        current_vrops_node_username = get_value_from_dict_safely(vrops_node, 'username', default_username)
        current_vrops_node_password = get_value_from_dict_safely(vrops_node, 'password', default_password)
        if current_vrops_node_vc and current_vrops_node_cluster:
            # Check if the VC has already been added to our list
            vc_already_added = False
            for vc_and_cluster in vc_cluster_targets:
                # Check if there is an object in the vc_cluster_targets list that is for this particular vrops_node's targeted VC
                if vc_and_cluster['vc'] == current_vrops_node_vc:
                    vc_already_added = True
                    # Add the desired cluster to this vc_cluster_targets object
                    if current_vrops_node_cluster not in vc_and_cluster['vc_clusters']:
                        vc_and_cluster['vc_clusters'].append(current_vrops_node_cluster)
            if vc_already_added is False:
                # The target VC is not in our list already, so let's create a new one with the targeted cluster
                vc_cluster_targets.append({
                    'vc': current_vrops_node_vc,
                    'vc_clusters': [current_vrops_node_cluster],
                    'username': current_vrops_node_username,
                    'password': current_vrops_node_password,
                    'nodes': [vrops_node['fqdn']]})
                vcenters.append(current_vrops_node_vc)
        else:
            module.fail_json(msg="get_esx_hosts_from_cluster.py processing of vrops_nodes failed on vrops_node " + vrops_node_key)

    esx_hostname_list = []  # this will contain all of the esx hostnames that belong to the given cluster
    failed_vc_list = []  # this will contain any VC's we fail to connect to in the below steps

    for vc_cluster_target in vc_cluster_targets:
        for cluster in vc_cluster_target['vc_clusters']:
            try:
                # Disable ssl verification
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.verify_mode = ssl.CERT_NONE
                # @todo - Need to add error handler for connection timeout?
                service_instance = connect.SmartConnect(host=vc_cluster_target['vc'],
                                                        user=vc_cluster_target['username'],
                                                        pwd=vc_cluster_target['password'],
                                                        port=vcenter_port,
                                                        sslContext=context)

                atexit.register(connect.Disconnect, service_instance)
                content = service_instance.RetrieveContent()
                for cluster_obj in get_obj(content, vim.ComputeResource, cluster):
                    if cluster_obj.name == cluster:
                        for host in cluster_obj.host:
                            # Added for US7519 - Check that host is active, no need to try to talk to hosts in maint. mode or disconnected
                            host_active = esx_host_active(host)
                            if host_active:
                                if host.name not in esx_hostname_list:
                                    esx_hostname_list.append(host.name)
                            else:
                                extra_log_output.append("get_esx_hosts_from_cluster.py: Host '{}' is not active, it will be ignored".format(host.name))
                if len(esx_hostname_list) == 0:
                    module.fail_json(msg="get_esx_hosts_from_cluster.py: Received 0 ESX hosts from cluster " + cluster + " on VC " + vc_cluster_target['vc'])

            except Exception as e:
                failed_vc_list.append(vc_cluster_target['vc'])
                extra_log_output.append('get_esx_hosts_from_cluster.py cluster ' + cluster + ' on VC ' + vc_cluster_target['vc'] + ': vmodl.MethodFault: ' + str(e))
                # module.fail_json(msg="get_esx_hosts_from_cluster.py cluster " + cluster + " on VC " + vc_cluster_target['vc'] + ": vmodl.MethodFault: " + str(e))
    # All finished! Return the results.
    vcenters_sorted = list(set(vcenters))
    esx_hostname_list_sorted = list(set(esx_hostname_list))
    failed_vc_list_sorted = list(set(failed_vc_list))
    vcenters_sorted.sort()
    esx_hostname_list_sorted.sort()
    failed_vc_list_sorted.sort()
    results = {
        'vcenters': vcenters_sorted,
        'esx_hosts': esx_hostname_list_sorted,
        'failed_vc_list': failed_vc_list_sorted
    }
    module.exit_json(msg=results, meta=extra_log_output)


if __name__ == "__main__":
    main()
