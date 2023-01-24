#!/usr/bin/env python

import atexit
import ssl
import urllib
from ansible.module_utils.basic import AnsibleModule

try:
    from pyVim import connect
    from pyVmomi import vim
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


def get_clusters_recursive(vsphere_obj, clusters, depth=1):
    max_depth = 16
    if depth > max_depth:
        return
    vimtype = vim.ClusterComputeResource
    entities = []
    if isinstance(vsphere_obj, vim.Folder):
        entities = vsphere_obj.childEntity
    elif isinstance(vsphere_obj, vim.Datacenter):
        entities = vsphere_obj.hostFolder.childEntity
    else:
        # unsupported recursion
        return
    for entity in entities:
        if isinstance(entity, vimtype):
            clusters.append(entity)
        else:
            get_clusters_recursive(entity, clusters, depth=1)
    return clusters


def get_item_path(item):
    # Get the folder path to the datacenter or cluster
    path_array = [item.name]
    parent = item.parent
    while parent:
        if (parent.name != 'Datacenters' and isinstance(item, vim.Datacenter)) or \
           (parent.name != 'Datacenters' and isinstance(item, vim.ClusterComputeResource)):
            path_array.insert(0, parent.name)
        parent = parent.parent
    item_path = "/".join(path_array)
    return item_path


def main():
    module = AnsibleModule(
        argument_spec=dict(
            vc_datacenter=dict(required=True, default=None),
            vc=dict(required=True, default=None),
            vc_cluster=dict(required=True, default=None),
            vc_username=dict(required=True, default=None),
            vc_password=dict(required=True, default=None),
            vc_port=dict(required=False, default=443)
        )
    )

    if pyvmomi_import_failure is True:
        module.fail_json(msg='pyVmomi is required')

    vc = module.params.get('vc')
    vc_cluster = module.params.get('vc_cluster')
    vc_datacenter = module.params.get('vc_datacenter')
    vc_username = module.params.get('vc_username')
    vc_password = module.params.get('vc_password')
    vc_port = module.params.get('vc_port')

    # for extra info in the module output
    extra_log_output = []
    ovf_deploypath = None
    failed_dc_clu_pairs = []

    try:
        # Disable ssl verification
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        # @todo - Need to add error handler for connection timeout?
        service_instance = connect.SmartConnect(host=vc,
                                                user=vc_username,
                                                pwd=vc_password,
                                                port=vc_port,
                                                sslContext=context)

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        # Get the Datacenters for the virtual center
        vimtype = vim.Datacenter
        vc_datacenters = get_obj(content, vimtype)
        vc_datacenter_cluster_hash = {}
        for dc in vc_datacenters:
            # Some virtual centers have the same vC name
            dc_clusters = get_clusters_recursive(dc, clusters=[])
            for clu in dc_clusters:
                if isinstance(clu, vim.ClusterComputeResource):
                    hash_key = "{}{}".format(dc.name.lower(), clu.name.lower())
                    hash_keys = vc_datacenter_cluster_hash.keys()
                    if hash_key in hash_keys:
                        failed_dc_clu_pairs.append("{}:{}".format(dc.name.lower(), clu.name.lower()))
                    else:  # The datacenter hasn't been added to the hash yet
                        clu_path = get_item_path(clu)
                        vc_datacenter_cluster_hash[hash_key] = clu_path

        hash_key = "{}{}".format(vc_datacenter.lower(), (urllib.quote_plus(vc_cluster).lower()))
        ovf_deploypath = vc_datacenter_cluster_hash[hash_key]
    except Exception as e:
        extra_log_output.append("get_ovfdeploy_path.py cluster {} on VC {} for datacenter {} failed: {}".format(vc_cluster, vc, vc_datacenter, e))

    # All finished! Return the results.
    results = {
        'failed_dc_clu_pairs': failed_dc_clu_pairs,
        'ovf_deploypath': ovf_deploypath
    }
    module.exit_json(msg=results, meta=extra_log_output)


if __name__ == "__main__":
    main()
