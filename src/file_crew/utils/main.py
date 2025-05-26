from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import uvicorn,logging
from file_crew.utils.reposority.raw_executions import extract_ref_ids
from file_crew.utils.schemas.recon_model import RefIdConfigurationRequest

app = FastAPI()
@app.post("/engine/ref-ids")
def collect_ref_ids(request: RefIdConfigurationRequest):
    logging.info(f"source_name: {request.sourceName}, recon_name: {request.reconName}, "
                f"recon_dd_name: {request.recon_dd_name}, source_dd_name: {request.source_dd_name}, "
                f"summary_side: {request.summary_side}, sourceNames:{request.sourceNames},"
                f"recon_ref_id:{request.recon_ref_id},recon_names:{request.source_ref_id},"
                f"source_ref_id:{request.source_ref_id},recon_dd_ref_id:{request.recon_dd_ref_id},"
                 f"matching_ref_id :{request.matchingRuleName},rule_type:{request.rule_type},event_name :{request.eventName}")
    recon_name = request.reconName
    recon_dd_name = request.recon_dd_name
    source_dd_name = request.source_dd_name
    source_names = request.sourceNames
    side_name = request.summary_side
    source_name = request.sourceName
    recon_names = request.reconNames
    recon_ref_id = request.recon_ref_id
    source_ref_id = request.source_ref_id
    recon_dd_ref_id = request.recon_dd_ref_id
    rule_name = request.matchingRuleName
    rule_type = request.rule_type
    event_name = request.eventName
    ref_id = extract_ref_ids(source_name, recon_name, recon_dd_name, source_dd_name, side_name,source_names,recon_names,recon_ref_id,
                             source_ref_id,recon_dd_ref_id,rule_name,rule_type,event_name)
    return JSONResponse(content=ref_id)

if __name__ == "__main__":
    uvicorn.run(app='main:app', host="127.0.0.1", port=8001, reload=True)