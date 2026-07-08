"""
Cognitive layer — optional advanced agent modules.

All modules are NO-OP when not enabled via env vars.
Activate individually:
    ENABLE_HRM=true
    ENABLE_RLIF=true
    ENABLE_SEAL=true
    ENABLE_SOCIAL_LEARNING=true
"""
from gen_agent.cognitive.hrm import HRMOrchestrator, make_hrm_if_enabled
from gen_agent.cognitive.rlif import RLIFEngine, make_rlif_if_enabled
from gen_agent.cognitive.seal import SEALEnhancer, make_seal_if_enabled
from gen_agent.cognitive.evolutionary import SocialLearner, make_social_learner_if_enabled

__all__ = [
    "HRMOrchestrator", "make_hrm_if_enabled",
    "RLIFEngine", "make_rlif_if_enabled",
    "SEALEnhancer", "make_seal_if_enabled",
    "SocialLearner", "make_social_learner_if_enabled",
]
