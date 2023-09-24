import orthanc
from datetime import datetime, timezone, timedelta
import json
import functools
import requests
import socket
import logging

CONFIGURATION = json.loads(orthanc.GetConfiguration()) # orthanc.json attributes
ORIGIN = socket.gethostname()
ROUTING_CRITERIA = "###ROUTING_CRITERIA###"
WRITER_AET = "###DICOM_AET###"
WRITER_ROOT_URL = f"http://{ORIGIN}"
ROUTER_URL = 'http://router'

requests.packages.urllib3.disable_warnings()
httpClient = requests.Session()
httpClient.auth = ('###ORTHANC_ADMIN###', '###ORTHANC_ADMIN_PASSWORD###')
httpClient.verify = False
httpClient.request = functools.partial(httpClient.request, timeout = 60)

processingStudies = {} # Hold a timestamp for each incoming study
totalTime = datetime.min

def onNewStudy(resourceId):
    study = httpClient.get(f"{WRITER_ROOT_URL}/studies/{resourceId}").json()
    processingStudies[study.get('MainDicomTags').get('StudyInstanceUID')] = datetime.now(timezone.utc)

    logging.info(f"NEW STUDY: {study.get('PatientMainDicomTags').get('PatientName')}")

def onStableStudy(resourceId):
    global totalTime
    study = httpClient.get(f"{WRITER_ROOT_URL}/studies/{resourceId}").json()
    studyInstanceUID = study.get('MainDicomTags').get('StudyInstanceUID')
    studyCreationDate = processingStudies[studyInstanceUID]

    delta = datetime.now(timezone.utc) - studyCreationDate - timedelta(seconds = CONFIGURATION.get('StableAge'))
    totalTime += delta
    processingStudies.pop(studyInstanceUID, None)

    logging.info(f"STABLE - {study.get('PatientMainDicomTags').get('PatientName')} - ELAPSED TIME: {delta}")
    logging.info(f"TOTAL TIME - {totalTime}")

def candidate():
        operator = ROUTING_CRITERIA.split('|')[1]
        value = ROUTING_CRITERIA.split('|')[2]
        body = {
            "aet": WRITER_AET,
            "host": ORIGIN,
            "port": 4242,
            "routingCriteria": {
                "routableAttribute": ROUTING_CRITERIA.split('|')[0],
                "operator": ROUTING_CRITERIA.split('|')[1],
                "value": value.split(',') if operator in ['IN', 'NOT_IN'] else value
            }
        }

        try:
            httpClient.post(f"{ROUTER_URL}/candidates", json = body)
            logging.info(f"CANDIDATE ACCEPTED - {ORIGIN}")
        except Exception as ex:

            # Is it because router couldn't be reached (e.g. offline)?
            # Is it because router declined the candidate?

            logging.error(f"UNABLE TO REGISTER {ORIGIN} WITHIN ROUTER")
            logging.error(f"{ex}")

def onChange(changeType, level, resourceId):
    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        candidate()

    if changeType == orthanc.ChangeType.NEW_STUDY:
        onNewStudy(resourceId)

    if changeType == orthanc.ChangeType.STABLE_STUDY:
        onStableStudy(resourceId)

logging.basicConfig(level = logging.INFO)
orthanc.RegisterOnChangeCallback(onChange)