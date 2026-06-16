import asyncio
from typing import Tuple, List
from models import ContractAnalysis, RiskItem
from config import logger
from services.agents.clause_parser import parse_contract
from services.agents.risk_flagger import flag_risks


async def run_analysis_workflow(contract_text: str, contract_id: str) -> Tuple[ContractAnalysis, List[RiskItem]]:
    logger.info(f"Starting analysis workflow for contract: {contract_id}")
    try:
        analysis = await asyncio.to_thread(parse_contract, contract_text, contract_id)
    except Exception as e:
        logger.error(f"Rule-based parsing failed: {e}, falling back")
        analysis = ContractAnalysis(contract_id=contract_id)

    try:
        risks = await asyncio.to_thread(flag_risks, contract_text, contract_id)
    except Exception as e:
        logger.error(f"Risk flagging failed: {e}")
        risks = []

    logger.info(f"Analysis workflow completed for contract: {contract_id}")
    return analysis, risks
