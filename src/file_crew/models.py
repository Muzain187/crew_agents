from typing import List, Union
from pydantic import BaseModel, HttpUrl


class SourceParameters(BaseModel):
    active: str
    deletedIndex: int
    referenceId: str
    sourceDesc: str
    sourceName: str


class SourceFieldSettingsParameters(BaseModel):
    currency: str
    fileFormat: str
    idField: str
    isManualActions: str
    isManualEditsAllowed: str
    isManualItemsAllowed: str
    isSplitSource: str
    isUpdatesAllowed: str
    isUploadActions: str
    sourceName: str
    sourceRefId: str
    subAccount: str


class SourceConfigurationParameters(BaseModel):
    active: str
    ddIndex: int
    displayName: str
    fieldName: str
    fieldType: str
    nestedFieldName: str
    origin: str
    sourceName: str
    sourceRefId: str


class Entity(BaseModel):
    entity: str
    # only present on some entities
    method: Union[str, None] = None
    parameters: Union[
        SourceParameters,
        SourceFieldSettingsParameters,
        SourceConfigurationParameters
    ]


class EntitiesContainer(BaseModel):
    entities: List[Entity]
