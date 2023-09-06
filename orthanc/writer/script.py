import orthanc
from datetime import datetime, timezone, timedelta
import base64
import json
import functools
import requests

CONFIGURATION = json.loads(orthanc.GetConfiguration()) # orthanc.json attributes
ORTHANC_ROOT_URL = 'http://###ORIGIN###'

requests.packages.urllib3.disable_warnings()
httpClient = requests.Session()
httpClient.auth = ('###ORTHANC_ADMIN###', '###ORTHANC_ADMIN_PASSWORD###')
httpClient.verify = False
httpClient.request = functools.partial(httpClient.request, timeout = 60)

processingStudies = {} # Hold a timestamp for each incoming study
totalTime = datetime.min

def requestFilter(uri, **request):
    auth = str(base64.b64decode(request['headers']['authorization'].split()[1]), 'utf-8')
    user = auth.split(':')[0]
    password = auth.split(':')[1]
    return user == '###ORTHANC_ADMIN###' and password == '###ORTHANC_ADMIN_PASSWORD###'

def onNewStudy(resourceId):
    study = httpClient.get(f"{ORTHANC_ROOT_URL}/studies/{resourceId}").json()
    processingStudies[study.get('MainDicomTags').get('StudyInstanceUID')] = datetime.now(timezone.utc)
    orthanc.LogWarning(f"NEW STUDY: {study.get('PatientMainDicomTags').get('PatientName')}")

def onStableStudy(resourceId):
    global totalTime
    study = httpClient.get(f"{ORTHANC_ROOT_URL}/studies/{resourceId}").json()
    studyInstanceUID = study.get('MainDicomTags').get('StudyInstanceUID')
    studyCreationDate = processingStudies[studyInstanceUID]

    delta = datetime.now(timezone.utc) - studyCreationDate - timedelta(seconds = CONFIGURATION.get('StableAge'))
    totalTime += delta
    processingStudies.pop(studyInstanceUID, None)

    orthanc.LogWarning(f"STABLE - {study.get('PatientMainDicomTags').get('PatientName')} - ELAPSED TIME: {delta}")
    orthanc.LogWarning(f"TOTAL TIME - {totalTime}")

def onChange(changeType, level, resourceId):
    if changeType == orthanc.ChangeType.NEW_STUDY:
        onNewStudy(resourceId)

    if changeType == orthanc.ChangeType.STABLE_STUDY:
        onStableStudy(resourceId)

orthanc.RegisterOnChangeCallback(onChange)
orthanc.RegisterIncomingHttpRequestFilter(requestFilter)