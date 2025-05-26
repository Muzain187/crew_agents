from typing import Optional,List
from pydantic import BaseModel, Field


class RefIdConfigurationRequest(BaseModel):
    reconName: Optional[str] = Field(None)
    sourceName: Optional[str] = Field(None)
    recon_dd_name: Optional[str] = Field(None)
    source_dd_name: Optional[str] = Field(None)
    summary_side: Optional[str] = Field(None)
    sourceNames: Optional[str] = Field(None)
    reconNames: Optional[str] = Field(None)
    summarySide: Optional[str] = Field(None)
    recon_ref_id: Optional[str] = Field(None)
    source_ref_id: Optional[str] = Field(None)
    recon_dd_ref_id: Optional[str] = Field(None)
    matchingRuleName: Optional[str] = Field(None)
    rule_type: Optional[str] = Field(None)
    eventName: Optional[str] = Field(None)