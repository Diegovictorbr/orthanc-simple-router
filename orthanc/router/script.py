import orthanc
import base64
import queue
import threading
import time
import functools
import requests

GLOBAL_LOCK = threading.Lock() # Lock global para as threads
ORTHANC_ROOT_URL = 'http://nginx/orthanc-router'

requests.packages.urllib3.disable_warnings()
httpClient = requests.Session()
httpClient.auth = ('###ORTHANC_ADMIN###', '###ORTHANC_ADMIN_PASSWORD###')
httpClient.verify = False
httpClient.request = functools.partial(httpClient.request, timeout = 60)

instancesQueue = queue.Queue() # Lista de instâncias a serem enviadas para a modalidade que será alternada

def requestFilter(uri, **request):
    auth = str(base64.b64decode(request['headers']['authorization'].split()[1]), 'utf-8')
    user = auth.split(':')[0]
    password = auth.split(':')[1]
    return user == '###ORTHANC_ADMIN###' and password == '###ORTHANC_ADMIN_PASSWORD###'

def producer():
    current = 0

    while True:
        try:
            changes = httpClient.get(f"{ORTHANC_ROOT_URL}/changes?since={current}&limit=4").json()

            for id in (c['ID'] for c in changes['Changes'] if c['ChangeType'] == 'NewInstance'):
                instance = httpClient.get(f"{ORTHANC_ROOT_URL}/instances/{id}/tags?simplify").json()
                instancesQueue.put({
                    'publicId': id,
                    'studyInstanceUID': instance.get('StudyInstanceUID'),
                    'modality': instance.get('Modality'),
                    'remoteAET': httpClient.get(f"{ORTHANC_ROOT_URL}/instances/{id}/metadata/RemoteAET").text or 'BROWSER'
                })

            current = changes['Last']
            
            if changes['Done']:
                time.sleep(1)
        except requests.exceptions.RequestException as ex:
            orthanc.LogError('ERRO NA VERIFICAÇÃO DE NOVAS INSTÂNCIAS.')
            orthanc.LogError(f"{ex}")
            time.sleep(5)

def routeInstances():
    TIMEOUT = 0.1
    
    while True:
        instances = []
        
        while True:
            try:
                instance = instancesQueue.get(True, TIMEOUT)
                instances.append(instance)
                instancesQueue.task_done()
            except queue.Empty:
                break

        if len(instances) > 0:
            GLOBAL_LOCK.acquire()
            generalInstances = []
            xrayInstances = []
            
            for instance in instances:
                if instance.get('modality') in ['CR', 'DX']:
                    xrayInstances.append(instance)
                else:
                    generalInstances.append(instance)

            # TODO: define routing conditions as configuration inside orthanc.json?
            if len(generalInstances) > 0:
                sendInstances(generalInstances, 'GENERAL')

            # TODO: define routing conditions as configuration inside orthanc.json?
            if len(xrayInstances) > 0:
                sendInstances(xrayInstances, 'XRAY')

            GLOBAL_LOCK.release()

# TODO: run function async
def sendInstances(instances, modality):
    groupedInstances = {}

    # 1 - Group instances by remote AET
    for instance in instances:
        if groupedInstances.get(instance.get('remoteAET')):
            groupedInstances.get(instance.get('remoteAET')).append(instance.get('publicId'))
        else:
            groupedInstances[instance.get('remoteAET')] = [instance.get('publicId')]

    for key in groupedInstances.keys():
        orthanc.LogWarning(f"Sending {len(groupedInstances.get(key))} instances from {key} to modality: {modality}")
        
        # 2 - Send grouped instances all at once
        body = { "Resources": groupedInstances.get(key), "LocalAet": key }

        start = time.time()

        try:
            httpClient.post(f"{ORTHANC_ROOT_URL}/modalities/{modality}/store", json = body, timeout = None) # No timeout: wait until the writer instance finishes
            
            orthanc.LogWarning(f"{len(groupedInstances.get(key))} instances sent in {time.time() - start} seconds")
            orthanc.LogWarning(f"{ORTHANC_ROOT_URL}/modalities/{modality}/store")

        except Exception as ex:
            orthanc.LogError(f"ERROR WHILE TRYING TO SEND INSTANCES: {groupedInstances.get(key)}")
            orthanc.LogError(f"{ex}")

        finally:
            try:
                start = time.time()
                httpClient.post(f"{ORTHANC_ROOT_URL}/tools/bulk-delete", json = body)
                orthanc.LogWarning(f"{len(groupedInstances.get(key))} instances removed in {time.time() - start} seconds")
            except Exception as ex:
                orthanc.LogError(f"ERROR WHILE TRYING TO DELETE INSTANCES: {groupedInstances.get(key)}")
                orthanc.LogError(f"{ex}")

def startThreads():
    producerThread = threading.Thread(None, producer, None)
    producerThread.daemon = True
    producerThread.start()

    consumerThread = threading.Thread(None, routeInstances, None)
    consumerThread.daemon = True
    consumerThread.start()

def OnChange(changeType, level, resourceId):
    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        startThreads()

orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterIncomingHttpRequestFilter(requestFilter)