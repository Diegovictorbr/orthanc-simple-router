from enum import Enum

class RoutableAttribute(Enum):
    INSTITUTION_NAME = "InstitutionName"
    MODALITY = "Modality"

class Operator(Enum):
    EQUAL = "="
    NOT_EQUAL = "!="
    IN = "IN"
    NOT_IN = "NOT_IN"

class RoutingCriteria:
    def __init__(self, routableAttribute: RoutableAttribute, operator: Operator, value) -> None:
        self.routableAttribute = routableAttribute
        self.operator = operator
        self.value = value
    
    def __str__(self):
        return f"{self.routableAttribute}|{self.operator}|{self.value}"

class Candidate:
    def __init__(self, aet, host, port, routingCriteria: RoutingCriteria) -> None:
        self.aet = aet
        self.host = host
        self.port = port
        self.routingCriteria = routingCriteria