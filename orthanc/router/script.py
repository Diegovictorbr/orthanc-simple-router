import orthanc
import classes
import json
import queue
import threading
import time
import functools
import requests
import logging
from datetime import datetime, timezone
from io import BytesIO
from pydicom import dcmread

GLOBAL_LOCK = threading.Lock() # Lock global para as threads
ROUTER_URL = 'http://router'

requests.packages.urllib3.disable_warnings()
httpClient = requests.Session()
httpClient.auth = ('###ORTHANC_ADMIN###', '###ORTHANC_ADMIN_PASSWORD###')
httpClient.verify = False
httpClient.request = functools.partial(httpClient.request, timeout = 60)

candidates = []
instancesQueue = queue.Queue()

def onReceivedInstance(receivedDicom, origin):
    dataset = dcmread(BytesIO(receivedDicom), specific_tags = ['PatientName', 'PatientSex', 'PatientBirthDate', 'InstitutionName', 'Modality'], stop_before_pixels = True)
    patientName = str(dataset.get('PatientName')) or None
    patientSex = str(dataset.get('PatientSex')) or None
    patientBirthDate = str(dataset.get('PatientBirthDate')) or None
    institutionName = str(dataset.get('InstitutionName')) or None
    modality = str(dataset.get('Modality')) or None

    def discardFn(message):
        orthanc.LogError(f"""
        ------------------------------------------------------------------------------------------
        {message}
        Patient: {patientName} - Sex: {patientSex} - Birthdate: {patientBirthDate} - Institution: {institutionName}
        ------------------------------------------------------------------------------------------""")
        return orthanc.ReceivedInstanceAction.DISCARD, None

    if not modality:
        return discardFn('INSTANCE DENIED: unspecified modality.')

    if not institutionName:
        return discardFn('INSTANCE DENIED: unspecified institution name.')

    return orthanc.ReceivedInstanceAction.KEEP_AS_IS, None

def producer():
    current = 0

    while True:
        try:
            changes = httpClient.get(f"{ROUTER_URL}/changes?since={current}&limit=4").json()

            for id in (c['ID'] for c in changes['Changes'] if c['ChangeType'] == 'NewInstance'):
                instance = httpClient.get(f"{ROUTER_URL}/instances/{id}/tags?simplify").json()
                instancesQueue.put({
                    'publicId': id,
                    'studyInstanceUID': instance.get('StudyInstanceUID'),
                    'remoteAET': httpClient.get(f"{ROUTER_URL}/instances/{id}/metadata/RemoteAET").text or 'BROWSER',
                    'Modality': instance.get('Modality'),
                    'InstitutionName': instance.get('InstitutionName')
                })

            current = changes['Last']
            
            if changes['Done']:
                time.sleep(5)
        except requests.exceptions.RequestException as ex:
            orthanc.LogError('ERROR WHILE CHECKING FOR NEW INSTANCES.')
            orthanc.LogError(f"{ex}")
            time.sleep(5)

def routeInstances():
    TIMEOUT = 0.5
    
    while True:
        instances = []
        
        while True:
            try:
                instance = instancesQueue.get(True, TIMEOUT)
                instances.append(instance)
                instancesQueue.task_done()
            except queue.Empty:
                break
        
        candidatesInstances = {}

        def determine(candidate, instance):
            if candidate.aet not in candidatesInstances.keys():
                candidatesInstances[candidate.aet] = [instance]
            else:
                candidatesInstances[candidate.aet].append(instance)

        for instance in instances:
            for candidate in candidates:
                instanceValue = instance.get(candidate.routingCriteria.routableAttribute.value)

                if candidate.routingCriteria.operator == classes.Operator.IN:
                    if instanceValue in candidate.routingCriteria.value:
                        determine(candidate, instance)
                elif candidate.routingCriteria.operator == classes.Operator.NOT_IN:
                    if instanceValue not in candidate.routingCriteria.value:
                        determine(candidate, instance)
                elif candidate.routingCriteria.operator == classes.Operator.EQUAL:
                    if instanceValue == candidate.routingCriteria.value:
                        determine(candidate, instance)
                elif candidate.routingCriteria.operator == classes.Operator.NOT_EQUAL:
                    if instanceValue != candidate.routingCriteria.value:
                        determine(candidate, instance)

        sendThreads = []

        for key in candidatesInstances.keys():
            candidateInstances = candidatesInstances[key]
            sendThreads.append(threading.Thread(None, sendInstances, args = (candidateInstances, key)))
        
        for sendThread in sendThreads:
            sendThread.start()

        for sendThread in sendThreads:
            sendThread.join()



# TODO: check reason instances need to be grouped by AET
def sendInstances(instances, modality):
    groupedInstances = {}

    # 1 - Group instances by remote AET
    for instance in instances:
        if groupedInstances.get(instance.get('remoteAET')):
            groupedInstances.get(instance.get('remoteAET')).append(instance.get('publicId'))
        else:
            groupedInstances[instance.get('remoteAET')] = [instance.get('publicId')]

    for key in groupedInstances.keys():
        # 2 - Send grouped instances all at once
        body = { "Resources": groupedInstances.get(key), "LocalAet": key }

        try:
            httpClient.post(f"{ROUTER_URL}/modalities/{modality}/store", json = body, timeout = None) # No timeout: wait until the writer instance finishes
        except Exception as ex:
            orthanc.LogError(f"ERROR WHILE TRYING TO SEND INSTANCES: {groupedInstances.get(key)}")
            orthanc.LogError(f"{ex}")
        finally:
            try:
                httpClient.post(f"{ROUTER_URL}/tools/bulk-delete", json = body)
            except Exception as ex:
                orthanc.LogError(f"ERROR WHILE TRYING TO DELETE INSTANCES: {groupedInstances.get(key)}")
                orthanc.LogError(f"{ex}")

def postCandidates(output, uri, **request):
    requestBody = json.loads(request['body'])
    routingCriteria = classes.RoutingCriteria(
        classes.RoutableAttribute[requestBody.get('routingCriteria').get('routableAttribute')], 
        classes.Operator[requestBody.get('routingCriteria').get('operator')], 
        requestBody.get('routingCriteria').get('value')
    )
    candidate = classes.Candidate(requestBody.get('aet'), requestBody.get('host'), requestBody.get('port'), routingCriteria)

    httpClient.put(f"{ROUTER_URL}/modalities/{requestBody.get('aet')}", json = {
        "AET": candidate.aet,
        "Host": candidate.host,
        "Port": candidate.port
    })
    candidates.append(candidate)

    logging.info(f"REGISTERED CANDIDATE {candidate.host} at {datetime.now(timezone.utc).isoformat()} UTC")
    output.AnswerBuffer('ok', 'text/plain')

    # TODO: pendingStudies attribute to control logic with incoming studies
    # TODO: determination upon incoming study scenario (block candidate from receiving part of a study)
    # TODO: validate routable attribute, throw ex
    # TODO: validate operator, throw ex
    # TODO: criteria must not be null

def startThreads():
    threading.Thread(target = producer, daemon = True).start()
    threading.Thread(target = routeInstances, daemon = True).start()

def OnChange(changeType, level, resourceId):
    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        startThreads()

logging.basicConfig(level = logging.INFO)
orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback('/candidates', postCandidates)