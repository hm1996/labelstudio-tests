def get_label_studio_app_pod_info(kube_client, release_name, namespace, app_name):
    response = kube_client.list_namespaced_pod(namespace)
    pods_object = { 
        pod.metadata.labels['app.kubernetes.io/name']: pod 
            for pod in response.items 
            if pod.metadata.labels['app.kubernetes.io/instance'] == release_name 
    }

    if not app_name in pods_object:
        raise Exception('Label studio is not running')

    return {
        'name': pods_object[app_name].metadata.name,
        'labels': pods_object[app_name].metadata.labels,
        'ip': pods_object[app_name].status.pod_ip,
        'status': pods_object[app_name].status.phase
    }