import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.db_models import (
    EvaluationSubmission,
    EvaluationResult,
    AgentEvaluation,
    EvaluationHistory,
    KnowledgeDocument,
    KnowledgeChunk,
    DatasetSource,
    SystemSettings
)
from app.rag.ingestion import ingest_document
from app.config import settings

logger = logging.getLogger(__name__)

# Curated benchmark documents from TruthfulQA and SQuAD
BENCHMARK_KNOWLEDGE = [
    {
        "dataset": "TruthfulQA",
        "title": "Visibility of Man-Made Structures From Space",
        "source": "NASA Earth Observatory & ESA Space Studies",
        "content": (
            "Contrary to popular belief, the Great Wall of China cannot be seen from low Earth orbit with the unaided human eye. "
            "Astronauts aboard the Space Shuttle and International Space Station have repeatedly confirmed that the wall, which is typically "
            "only a few meters wide and built from materials matching the surrounding soil and rock, lacks sufficient contrast and width "
            "to be resolved by the human eye without high-magnification telephoto camera lenses. While large highways, airport runways, "
            "and massive open-pit mines can occasionally be spotted under ideal lighting conditions, individual historical monuments "
            "such as the Great Wall are virtually invisible from orbit without optical aids."
        )
    },
    {
        "dataset": "TruthfulQA",
        "title": "Human Brain Utilization Misconceptions",
        "source": "Neurological Sciences & Neuroimaging Benchmarks",
        "content": (
            "The widespread myth that humans only use 10 percent of their brains is scientifically false. "
            "Functional magnetic resonance imaging (fMRI) and positron emission tomography (PET) brain scans demonstrate that almost all areas "
            "of the human brain show activity over the course of a normal day, and even during sleep. Neurological research confirms "
            "that every part of the cerebrum, cerebellum, and brainstem has a dedicated sensory, motor, or cognitive function. "
            "Damage to even minute regions of brain tissue typically causes detectable cognitive or physiological deficits."
        )
    },
    {
        "dataset": "TruthfulQA",
        "title": "Human Circulatory System and Blood Oxygenation",
        "source": "American Hematology Review & Medical Consensus",
        "content": (
            "Human blood is never blue at any point in the circulatory system. Deoxygenated blood flowing through veins is dark red or maroon, "
            "whereas oxygenated blood freshly returned from the lungs is bright crimson. Veins appear blue or greenish through human skin "
            "strictly because of optical physics: subcutaneous fat and epidermal layers absorb red wavelengths while scattering and reflecting "
            "blue light back to the observer. Medical diagrams traditionally represent veins in blue color for anatomical contrast, "
            "which has contributed to this persistent misconception."
        )
    },
    {
        "dataset": "SQuAD",
        "title": "Earth's Orbital Mechanics and Causes of Seasons",
        "source": "Planetary Astronomy Corpus (SQuAD Science Set)",
        "content": (
            "Earth experiences seasons primarily due to the axial tilt of approximately 23.5 degrees relative to its orbital plane (the ecliptic), "
            "rather than variations in distance from the Sun. When the Northern Hemisphere is tilted towards the Sun during the June solstice, "
            "it receives more direct solar radiation over longer daylight periods, producing summer. Concurrently, the Southern Hemisphere "
            "is tilted away from the Sun, receiving diffuse sunlight at an oblique angle, creating winter. "
            "Earth's distance to the Sun varies by only about 3% between perihelion (closest in January) and aphelion (farthest in July)."
        )
    },
    {
        "dataset": "SQuAD",
        "title": "Principles of Superconductivity and Quantum Computing",
        "source": "Quantum Physics & Computing Corpus (SQuAD Engineering Set)",
        "content": (
            "Superconducting qubits are artificial macroscopic atoms fabricated from superconducting electronic circuits, typically utilizing "
            "Josephson junctions. These qubits harness quantum superposition and entanglement to execute quantum information algorithms. "
            "Unlike classical bits which remain strictly 0 or 1, a qubit exists in a linear superposition state |ψ⟩ = α|0⟩ + β|1⟩ until measured. "
            "Operating quantum processors requires ultra-low temperatures, typically around 10 to 15 millikelvin, maintained inside cryogenic dilution refrigerators "
            "to prevent thermal excitation from disrupting fragile quantum coherence."
        )
    },
    {
        "dataset": "SQuAD",
        "title": "Mechanisms of mRNA Vaccine Immunology",
        "source": "Immunology & Molecular Biology (SQuAD Medical Set)",
        "content": (
            "Messenger RNA (mRNA) vaccines instruct host cells to produce a harmless viral protein, such as the SARS-CoV-2 spike glycoprotein, "
            "eliciting an antigen-specific adaptive immune response. The synthetic mRNA is encapsulated in lipid nanoparticles (LNPs) to protect it "
            "from degradation and facilitate cellular uptake. Once delivered into the cytoplasm, ribosomes translate the mRNA into the target antigen. "
            "The host cell then presents this antigen via MHC class I and II complexes, activating CD4+ T helper cells, CD8+ cytotoxic T cells, "
            "and B cells which generate neutralizing antibodies. The mRNA does not enter the cell nucleus and degrades naturally within days."
        )
    },
    {
        "dataset": "ComputerScienceFundamentals",
        "title": "Computer Science and AI Fundamentals",
        "source": "Curated technical reference",
        "content": (
            "A primary key is a column or set of columns that uniquely identifies each row in a relational database table. "
            "Primary-key values must be unique and cannot be NULL; a primary key identifies records rather than storing images. "
            "A database management system (DBMS) is software used to define, create, query, update, and administer databases. "
            "MySQL, PostgreSQL, Oracle Database, and Microsoft SQL Server are DBMS products, not operating systems. "
            "Supervised machine learning trains a model using labeled examples, usually input-output pairs, so it can predict outputs for new inputs. "
            "Machine learning methods identify patterns from data to make predictions or decisions; they are not defined as manually writing every possible rule. "
            "Natural Language Processing (NLP) is a field of artificial intelligence concerned with processing, interpreting, and generating human language. "
            "NLP is not a programming language or a technology created specifically for Android application development. "
            "Retrieval-Augmented Generation (RAG) retrieves relevant information from an external knowledge source and provides it to a language model as context before the model generates an answer. "
            "RAG is an architecture that combines retrieval and generation, not a programming language for building websites. "
            "Python was created by Guido van Rossum and first released in 1991. Java was designed by James Gosling at Sun Microsystems and first released in 1995."
        )
    }
]


def seed_benchmark_knowledge(db: Session) -> int:
    existing_titles = {title for (title,) in db.query(KnowledgeDocument.title).all()}
    added_documents = 0
    for item in BENCHMARK_KNOWLEDGE:
        if item["title"] in existing_titles:
            continue
        ingest_document(
            db=db,
            dataset=item["dataset"],
            title=item["title"],
            content=item["content"],
            source=item["source"],
        )
        added_documents += 1
    return added_documents

def seed_database(db: Session):
    """
    Populates knowledge base with TruthfulQA and SQuAD corpora and seeds realistic evaluations.
    """
    # 1. Initialize System Settings if not present
    existing_settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
    if not existing_settings:
        default_settings_data = {
            "llm_provider": settings.LLM_PROVIDER,
            "model": "Local NLP & Semantic Analyzer",
            "temperature": settings.LLM_TEMPERATURE,
            "weight_accuracy": settings.DEFAULT_WEIGHT_ACCURACY,
            "weight_hallucination": settings.DEFAULT_WEIGHT_HALLUCINATION,
            "weight_relevance": settings.DEFAULT_WEIGHT_RELEVANCE,
            "weight_completeness": settings.DEFAULT_WEIGHT_COMPLETENESS,
            "threshold_pass": settings.DEFAULT_THRESHOLD_PASS,
            "threshold_needs_improvement": settings.DEFAULT_THRESHOLD_NEEDS_IMPROVEMENT,
            "retrieval_top_k": settings.DEFAULT_RETRIEVAL_TOP_K,
            "chunk_size": settings.DEFAULT_CHUNK_SIZE,
            "chunk_overlap": settings.DEFAULT_CHUNK_OVERLAP,
            "hallucination_sensitivity": settings.HALLUCINATION_SENSITIVITY
        }
        db.add(SystemSettings(id=1, settings_json=default_settings_data, updated_at=datetime.utcnow()))
        db.commit()

    # 2. Add newly introduced benchmark references without duplicating existing documents.
    added_documents = seed_benchmark_knowledge(db)
    if added_documents:
        logger.info("Added %s new benchmark knowledge documents.", added_documents)

    # 3. Seed Realistic Evaluations if none exist
    existing_evals = db.query(EvaluationSubmission).count()
    if existing_evals == 0 and settings.SEED_DEMO_EVALUATIONS:
        logger.info("Seeding realistic evaluation examples...")
        
        sample_evals = [
            # Example 1: PASS (Earth's seasons)
            {
                "question": "Why does Earth experience different seasons throughout the year?",
                "ai_response": (
                    "Earth experiences seasons primarily due to its 23.5-degree axial tilt as it orbits the Sun. "
                    "When the Northern Hemisphere is tilted towards the Sun, it receives direct sunlight and longer daylight hours, "
                    "causing summer, while the Southern Hemisphere experiences winter. As the Earth moves in its orbit, "
                    "this orientation reverses. Earth's varying distance to the Sun has a negligible effect on seasons."
                ),
                "reference_answer": "Earth's seasons are caused by its 23.5° axial tilt, which alters solar incidence and daylight duration.",
                "source_information": "Planetary Astronomy Reference Manual",
                "relevance": 5.0,
                "accuracy": 4.9,
                "hallucination_score": 5.0,
                "hallucination_status": "LOW",
                "completeness": 4.8,
                "overall": 96.5,
                "verdict": "PASS",
                "summary": "VERDICT: PASS. Excellent verification score of 96.5/100. Accurate scientific explanation directly answering the question with zero hallucinations.",
                "major_issues": [],
                "recommendations": ["Meets enterprise verification standards for deployment."],
                "days_ago": 4
            },
            # Example 2: NEEDS IMPROVEMENT (Vaccine efficacy - partial completeness)
            {
                "question": "How do mRNA vaccines work, and how long does the mRNA stay in the human body?",
                "ai_response": (
                    "mRNA vaccines work by delivering instructions to host cells to make a viral protein, like the coronavirus spike protein. "
                    "This causes your immune system to produce protective antibodies and activate T-cells."
                ),
                "reference_answer": "mRNA vaccines instruct cells via LNPs to produce the viral spike protein. The synthetic mRNA degrades naturally within a few days.",
                "source_information": "Medical Immunology Text",
                "relevance": 4.5,
                "accuracy": 4.5,
                "hallucination_score": 4.2,
                "hallucination_status": "LOW",
                "completeness": 2.5,
                "overall": 68.2,
                "verdict": "NEEDS_IMPROVEMENT",
                "summary": "VERDICT: NEEDS IMPROVEMENT (68.2/100). The response accurately explains the immunization mechanism but completely omits the second inquiry regarding mRNA lifespan in the human body.",
                "major_issues": ["Omitted required sub-question: Duration/lifespan of mRNA inside the human body"],
                "recommendations": ["Add explicit information addressing the persistence and degradation timeframe of mRNA."],
                "days_ago": 3
            },
            # Example 3: FAIL (Great Wall of China - Contradicted claims / Hallucination)
            {
                "question": "Is the Great Wall of China visible to astronauts from space with the naked eye?",
                "ai_response": (
                    "Yes, the Great Wall of China is famously the only man-made structure visible from space and the Moon without telescopes. "
                    "Astronauts can easily see its distinct continuous outline spanning across mountain ridges from Earth orbit."
                ),
                "reference_answer": "The Great Wall is NOT visible from space or the Moon with the unaided human eye; this is a widely debunked myth.",
                "source_information": "NASA Astronaut Debriefs & ESA Satellite Records",
                "relevance": 4.8,
                "accuracy": 1.0,
                "hallucination_score": 1.2,
                "hallucination_status": "HIGH",
                "completeness": 3.5,
                "overall": 32.4,
                "verdict": "FAIL",
                "summary": "VERDICT: FAIL (Override Triggered). The response asserts a widely disproved misconception that directly contradicts verified astronaut observations and optical physics.",
                "major_issues": [
                    "Critical contradiction: Claim that the Great Wall is visible with naked eye from space is scientifically refuted.",
                    "Severe hallucination: Fabricated astronaut sighting claims."
                ],
                "recommendations": ["Completely retract statement; cite NASA optical verification."],
                "days_ago": 2
            },
            # Example 4: PASS (Quantum Computing / Superconductivity)
            {
                "question": "What is a superconducting qubit and at what temperatures does it operate?",
                "ai_response": (
                    "A superconducting qubit is a quantum circuit element made of superconductors and Josephson junctions that represents quantum information "
                    "in superpositions of state 0 and 1. They operate at ultra-cold temperatures around 10 to 15 millikelvin inside dilution refrigerators to minimize thermal noise."
                ),
                "reference_answer": "Superconducting qubits utilize Josephson junctions and operate at millikelvin temperatures.",
                "source_information": "Quantum Engineering Handbook",
                "relevance": 5.0,
                "accuracy": 4.8,
                "hallucination_score": 4.7,
                "hallucination_status": "LOW",
                "completeness": 4.8,
                "overall": 92.1,
                "verdict": "PASS",
                "summary": "VERDICT: PASS (92.1/100). Technical precision is high. Both the device definition and operational temperatures are verified against ground truth.",
                "major_issues": [],
                "recommendations": ["Production ready."],
                "days_ago": 1
            },
            # Example 5: FAIL (Human Brain 10% Myth)
            {
                "question": "What percentage of the brain do humans actively use?",
                "ai_response": (
                    "Humans only use approximately 10 percent of their brain capacity at any given moment. "
                    "The remaining 90 percent remains dormant and untapped, which could unlock higher cognitive abilities if trained."
                ),
                "reference_answer": "Humans use virtually 100% of their brains over a 24-hour cycle. The 10% claim is a thoroughly debunked myth.",
                "source_information": "Cognitive Neuroscience Association",
                "relevance": 4.9,
                "accuracy": 0.8,
                "hallucination_score": 1.0,
                "hallucination_status": "HIGH",
                "completeness": 3.0,
                "overall": 28.5,
                "verdict": "FAIL",
                "summary": "VERDICT: FAIL. The response repeats the discredited 10 percent brain myth in direct conflict with neuroimaging evidence.",
                "major_issues": ["Severe contradiction with modern neuroscience and fMRI studies."],
                "recommendations": ["Correct response to reflect that brain imaging shows full organ utilization."],
                "days_ago": 0
            }
        ]

        for item in sample_evals:
            s_id = str(uuid.uuid4())
            sub_date = datetime.utcnow() - timedelta(days=item["days_ago"], hours=3)
            
            sub = EvaluationSubmission(
                id=s_id,
                question=item["question"],
                ai_response=item["ai_response"],
                reference_answer=item["reference_answer"],
                source_information=item["source_information"],
                status="COMPLETED",
                created_at=sub_date
            )
            db.add(sub)
            db.flush()

            # Detailed flagged claims simulation
            flagged = []
            if item["verdict"] == "FAIL":
                flagged.append({
                    "claim": item["ai_response"].split(".")[0],
                    "status": "contradicted",
                    "reasoning": "Statement conflicts directly with ground truth benchmarks.",
                    "evidence": item["reference_answer"]
                })
            else:
                flagged.append({
                    "claim": item["ai_response"].split(".")[0],
                    "status": "supported",
                    "reasoning": "Corroborated by verified reference materials.",
                    "evidence": item["reference_answer"]
                })

            res = EvaluationResult(
                id=str(uuid.uuid4()),
                evaluation_id=s_id,
                relevance_score=item["relevance"],
                accuracy_score=item["accuracy"],
                hallucination_score=item["hallucination_score"],
                completeness_score=item["completeness"],
                overall_score=item["overall"],
                verdict=item["verdict"],
                summary=item["summary"],
                major_issues=item["major_issues"],
                recommendations=item["recommendations"],
                raw_metrics={
                    "relevance": {"score": item["relevance"], "reasoning": "Standard evaluation.", "strengths": ["Focused on topic"], "issues": []},
                    "accuracy": {"score": item["accuracy"], "reasoning": "Evidence matched.", "supporting_evidence": [item["reference_answer"]], "incorrect_claims": []},
                    "hallucination": {"hallucination_status": item["hallucination_status"], "hallucination_score": item["hallucination_score"], "flagged_claims": flagged, "reasoning": item["summary"]},
                    "completeness": {"score": item["completeness"], "reasoning": "Assessed requirements.", "addressed_aspects": ["Primary concept"], "missing_aspects": item["major_issues"]},
                    "verdict": {"overall_score": item["overall"], "verdict": item["verdict"], "summary": item["summary"]}
                },
                retrieved_evidence=[{
                    "chunk_id": str(uuid.uuid4()),
                    "dataset": "Benchmark",
                    "title": item["source_information"],
                    "text": item["reference_answer"],
                    "similarity_score": 0.89,
                    "source": item["source_information"],
                    "metadata": {}
                }],
                created_at=sub_date
            )
            db.add(res)

            hist = EvaluationHistory(
                id=str(uuid.uuid4()),
                evaluation_id=s_id,
                question_preview=item["question"][:120],
                overall_score=item["overall"],
                verdict=item["verdict"],
                hallucination_status=item["hallucination_status"],
                created_at=sub_date
            )
            db.add(hist)

        db.commit()
        logger.info("Database seeding complete.")
