import sys, time
sys.path.insert(0, 'backend')
from app.orchestrator.evaluation_orchestrator import orchestrator
from app.schemas.evaluation_schemas import SingleEvaluationRequest
from app.database.session import SessionLocal, init_db

init_db()
db = SessionLocal()

req = SingleEvaluationRequest(
    question='Why is the sky blue?',
    ai_response='The sky appears blue due to Rayleigh scattering. When sunlight passes through the atmosphere, shorter blue wavelengths scatter more than longer red wavelengths, making the sky appear blue.',
    reference_answer='Rayleigh scattering causes blue light to scatter more than other wavelengths.',
    source_information='Atmospheric Optics'
)

start = time.time()
result = orchestrator.run_evaluation(db, req)
elapsed = time.time() - start
db.close()
print(f"BEFORE OPTIMIZATION:")
print(f"Total eval time: {elapsed:.3f}s")
print(f"Verdict: {result['verdict']}")
print(f"Score: {result['overall_score']}")
