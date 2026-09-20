from __future__ import annotations
import re
import json
from typing import Dict, Any, List, Optional
from backend.app.engines.scoring_engine import DEFAULT_SECTION_WEIGHTS
from backend.app.llm.client import llm_client
from backend.app.engines.interview_state import InterviewState, Claim, ClaimSource, ClaimStatus


def generate_stable_id(prefix: str, name: str, index: int) -> str:
    """
    Generates deterministic, human-readable, stable IDs for resume items.
    Prevents UUID churn across turns, reruns, and re-parsing.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    slug = cleaned[:24] if cleaned else f"item_{index + 1}"
    return f"{prefix}_{index + 1}_{slug}"


class ResumeParser:
    """
    Stateful Context Preparation Engine for Technical Interviews.
    
    CRITICAL INVARIANTS:
    1. The resume is contextual evidence, NOT an answer key or proof of competence.
    2. Explicit resume claims start strictly as UNEXPLORED in InterviewState.
    3. Resume claims must NEVER be marked as demonstrated or verified without dialogue evidence.
    4. NO fake fallback candidate information: do NOT invent certifications, achievements,
       extracurriculars, sample projects, or artificial metrics. Empty context is preferred.
    5. Work experience ordering: ask ALL work experience first, preserving resume order.
    6. Project ordering: sort projects descending by overall_relevance.
    7. Stable item IDs: deterministic identifiers without random UUIDs.
    """

    @classmethod
    def generate_stable_id(cls, prefix: str, name: str, index: int) -> str:
        return generate_stable_id(prefix, name, index)

    @classmethod
    def parse_resume(
        cls,
        raw_text: str,
        target_company: str = "Tech Corp",
        target_role: str = "Software Engineer"
    ) -> Dict[str, Any]:
        """
        Parses resume into structured contextual sections without fabricating data.
        """
        text = raw_text.strip() if raw_text else ""
        # Normalize Unicode dashes and bullet characters
        text = text.replace("\u2014", " — ").replace("\u2013", " – ").replace("\u2015", " ― ")
        text = re.sub(r"[\u25cf\u2022\u25aa\u25ab]", "•", text)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 1. Extract Name and Email heuristically
        name = "Candidate"
        email = "candidate@example.com"

        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            email = email_match.group(0)

        for line in lines[:5]:
            if line and "@" not in line and len(line) < 50 and not re.search(r'(resume|curriculum|cv|phone|email|\.com)', line, re.I):
                name = line
                break

        # 2. Try Live LLM extraction if resume text has substance
        if len(text) > 80 and (getattr(llm_client, "gemini_key", None) or getattr(llm_client, "groq_key", None) or getattr(llm_client, "openai_key", None)):
            try:
                system_prompt = (
                    "You are a strict, objective technical recruiter and resume parser.\n"
                    "Extract ONLY verifiable technical facts, experience, and projects present in the candidate resume relative to the target role.\n"
                    "CLASSIFICATION GUIDELINES:\n"
                    "- Employment, corporate internships, and company roles belong in 'work_experience'.\n"
                    "- Academic projects, course projects (e.g. DBMS Project, NLP Project), personal systems, and research initiatives belong in 'projects' (even if placed under an 'EXPERIENCE' section).\n"
                    "STRICT NEGATIVE CONSTRAINT: DO NOT hallucinate, assume, or invent fake projects, fake metrics, fake certifications, or fake achievements. "
                    "If a section or field is not explicitly present in the text, return an empty array [] or empty string.\n\n"
                    "Output ONLY valid JSON matching this schema:\n"
                    "{\n"
                    '  "candidate_name": "Candidate Full Name",\n'
                    '  "candidate_email": "candidate email or null",\n'
                    '  "work_experience": [\n'
                    "    {\n"
                    '      "company": "Company Name",\n'
                    '      "role": "Job Title",\n'
                    '      "duration": "Dates or timeline",\n'
                    '      "summary": "Technical summary of responsibilities and architecture",\n'
                    '      "responsibilities": ["Responsibility 1", "Responsibility 2"],\n'
                    '      "technologies": ["Tech1", "Tech2"],\n'
                    '      "components_services": ["Service A", "Database B"],\n'
                    '      "architecture_claims": ["Architectural pattern or design stated"],\n'
                    '      "metrics": ["Throughput, scale, latency, or percentage improvements stated"],\n'
                    '      "ownership_claims": ["Leadership or individual contribution claimed"],\n'
                    '      "achievements": ["Verifiable achievements stated in resume"],\n'
                    '      "overall_relevance": 0.85,\n'
                    '      "key_skills": ["Skill1", "Skill2"]\n'
                    "    }\n"
                    "  ],\n"
                    '  "projects": [\n'
                    "    {\n"
                    '      "title": "Project Title",\n'
                    '      "description": "Technical description of architecture and implementation",\n'
                    '      "technologies": ["Tech1", "Tech2"],\n'
                    '      "components_services": ["Component 1", "Service 2"],\n'
                    '      "architecture_claims": ["Architecture pattern claimed"],\n'
                    '      "metrics": ["Concrete metric claimed"],\n'
                    '      "responsibilities": ["Candidate specific contribution"],\n'
                    '      "overall_relevance": 0.80,\n'
                    '      "relevant_topics": ["Topic1", "Topic2"]\n'
                    "    }\n"
                    "  ],\n"
                    '  "skills": ["Skill1", "Skill2"],\n'
                    '  "education": [\n'
                    "    {\n"
                    '      "degree": "Degree",\n'
                    '      "institution": "University/Institution",\n'
                    '      "grad_year": "Year"\n'
                    "    }\n"
                    "  ],\n"
                    '  "certifications": ["Only actual certs in resume, else []"],\n'
                    '  "achievements": ["Only actual achievements in resume, else []"],\n'
                    '  "extracurricular": ["Only actual extracurriculars in resume, else []"]\n'
                    "}"
                )
                user_prompt = f"Target Company: {target_company}\nTarget Role: {target_role}\n\nCandidate Resume Text:\n{text}"
                completion = llm_client.generate_completion(system_prompt, user_prompt, temperature=0.1)
                if completion:
                    clean = completion.strip()
                    if clean.startswith("```json"): clean = clean[7:]
                    if clean.startswith("```"): clean = clean[3:]
                    if clean.endswith("```"): clean = clean[:-3]
                    parsed_llm = json.loads(clean.strip())

                    if parsed_llm.get("candidate_name") and parsed_llm["candidate_name"].strip() != "Candidate Full Name":
                        name = parsed_llm["candidate_name"].strip()
                    if parsed_llm.get("candidate_email") and "@" in parsed_llm["candidate_email"]:
                        email = parsed_llm["candidate_email"].strip()

                    work_exps = parsed_llm.get("work_experience", [])
                    for idx, exp in enumerate(work_exps):
                        exp["id"] = generate_stable_id("exp", exp.get("company", "work"), idx)
                        rel = exp.get("overall_relevance")
                        if rel is None or not isinstance(rel, (int, float)):
                            exp["overall_relevance"] = cls._calculate_semantic_relevance(
                                text=f"{exp.get('role', '')} {exp.get('summary', '')} {' '.join(exp.get('technologies', []))}",
                                target_role=target_role
                            )
                        else:
                            exp["overall_relevance"] = max(0.1, min(1.0, float(rel)))

                    projects = parsed_llm.get("projects", [])
                    for idx, p in enumerate(projects):
                        p["project_id"] = generate_stable_id("proj", p.get("title", "project"), idx)
                        rel = p.get("overall_relevance")
                        if rel is None or not isinstance(rel, (int, float)):
                            p["overall_relevance"] = cls._calculate_semantic_relevance(
                                text=f"{p.get('title', '')} {p.get('description', '')} {' '.join(p.get('technologies', []))}",
                                target_role=target_role
                            )
                        else:
                            p["overall_relevance"] = max(0.1, min(1.0, float(rel)))
                        p["irrelevant_topics"] = p.get("irrelevant_topics", [])

                    # Sort projects descending by overall_relevance
                    projects.sort(key=lambda p: float(p.get("overall_relevance", 0.5)), reverse=True)
                    for idx, p in enumerate(projects):
                        p["questioning_priority"] = idx + 1

                    return {
                        "candidate_name": name,
                        "candidate_email": email,
                        "raw_text": text,
                        "sections": {
                            "work_experience": work_exps,
                            "projects": projects,
                            "skills": parsed_llm.get("skills", []),
                            "education": parsed_llm.get("education", []),
                            "certifications": parsed_llm.get("certifications", []),
                            "achievements": parsed_llm.get("achievements", []),
                            "extracurricular": parsed_llm.get("extracurricular", [])
                        },
                        "section_weights": DEFAULT_SECTION_WEIGHTS
                    }
            except Exception as e:
                print(f"[ResumeParser] LLM parsing failed or unconfigured: {e}, falling back to deterministic extraction")

        # 3. Deterministic Rule-Based Extraction (NO fake fallback data!)
        work_exps = cls._extract_work_experience(text, target_role)
        projects = cls._extract_projects(text, target_role)
        skills = cls._extract_skills(text)
        education = cls._extract_education(text)
        certifications = cls._extract_certifications(text)
        achievements = cls._extract_achievements(text)
        extracurricular = cls._extract_extracurricular(text)

        # Sort projects descending by overall_relevance
        projects.sort(key=lambda p: float(p.get("overall_relevance", 0.5)), reverse=True)
        for idx, p in enumerate(projects):
            p["questioning_priority"] = idx + 1

        return {
            "candidate_name": name,
            "candidate_email": email,
            "raw_text": text,
            "sections": {
                "work_experience": work_exps,
                "projects": projects,
                "skills": skills,
                "education": education,
                "certifications": certifications,
                "achievements": achievements,
                "extracurricular": extracurricular
            },
            "section_weights": DEFAULT_SECTION_WEIGHTS
        }

    @classmethod
    def populate_interview_state(cls, state: InterviewState, sections: Dict[str, Any]) -> None:
        """
        Registers all extracted work experience items, project items, and contextual resume
        claims into InterviewState.
        
        CRITICAL INVARIANTS:
        1. All resume claims start as ClaimSource.RESUME with ClaimStatus.UNEXPLORED.
        2. Resume claims are NEVER marked as demonstrated or verified.
        3. Work experiences are registered first, followed by projects (sorted descending by relevance).
        """
        if not sections:
            return

        # 1. Register Work Experience Items & Claims
        work_exps = sections.get("work_experience", [])
        for idx, exp in enumerate(work_exps):
            exp_id = exp.get("id") or cls.generate_stable_id("exp", exp.get("company", "work"), idx)
            company_name = exp.get("company", f"Company {idx + 1}")
            role_title = exp.get("role", "Software Engineer")
            title = f"{role_title} at {company_name}"
            summary = exp.get("summary", "") or f"Professional experience at {company_name}."
            relevance = float(exp.get("overall_relevance", 0.75))

            if exp_id not in state.items:
                state.register_item(
                    item_id=exp_id,
                    item_type="WORK_EXPERIENCE",
                    phase="EXPERIENCE_DEFENSE",
                    title=title,
                    details=summary,
                    relevance_weight=relevance
                )

            # Core employment claim
            state.register_resume_claim(
                statement=f"Worked as {role_title} at {company_name}",
                item_id=exp_id,
                entity=company_name,
                attribute="role",
                topics=[role_title, company_name]
            )

            # Responsibilities
            for resp in exp.get("responsibilities", []):
                if resp and len(resp.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Responsible for {resp.strip()} at {company_name}",
                        item_id=exp_id,
                        entity=company_name,
                        attribute="responsibility",
                        topics=[role_title]
                    )

            # Technologies & Key Skills
            techs = list(set(exp.get("technologies", []) + exp.get("key_skills", [])))
            for tech in techs:
                if tech and len(tech.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Used {tech.strip()} at {company_name}",
                        item_id=exp_id,
                        entity=tech.strip(),
                        attribute="technology",
                        topics=[tech.strip()]
                    )

            # Components & Services
            for comp in exp.get("components_services", []):
                if comp and len(comp.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Worked on {comp.strip()} at {company_name}",
                        item_id=exp_id,
                        entity=comp.strip(),
                        attribute="component",
                        topics=[comp.strip()]
                    )

            # Architecture claims
            for arch in exp.get("architecture_claims", []):
                if arch and len(arch.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Architectural claim at {company_name}: {arch.strip()}",
                        item_id=exp_id,
                        entity=company_name,
                        attribute="architecture",
                        topics=[role_title]
                    )

            # Metrics
            for metric in exp.get("metrics", []):
                if metric and len(metric.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Claimed metric at {company_name}: {metric.strip()}",
                        item_id=exp_id,
                        entity=company_name,
                        attribute="metric",
                        topics=[company_name]
                    )

            # Ownership claims
            for own in exp.get("ownership_claims", []):
                if own and len(own.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Claimed ownership at {company_name}: {own.strip()}",
                        item_id=exp_id,
                        entity=company_name,
                        attribute="ownership",
                        topics=[company_name]
                    )

            # Verifiable achievements
            for ach in exp.get("achievements", []):
                if ach and len(ach.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Achievement at {company_name}: {ach.strip()}",
                        item_id=exp_id,
                        entity=company_name,
                        attribute="achievement",
                        topics=[company_name]
                    )

        # 2. Register Project Items & Claims (sorted descending by relevance)
        projects = list(sections.get("projects", []))
        projects.sort(key=lambda p: float(p.get("overall_relevance", 0.5)), reverse=True)

        for idx, proj in enumerate(projects):
            proj_id = proj.get("project_id") or cls.generate_stable_id("proj", proj.get("title", "project"), idx)
            p_title = proj.get("title", f"Project {idx + 1}")
            p_desc = proj.get("description", "")
            relevance = float(proj.get("overall_relevance", 0.70))

            if proj_id not in state.items:
                state.register_item(
                    item_id=proj_id,
                    item_type="PROJECT",
                    phase="PROJECT_DEFENSE",
                    title=p_title,
                    details=p_desc,
                    relevance_weight=relevance
                )

            # Project overview claim
            state.register_resume_claim(
                statement=f"Built project {p_title}: {p_desc}",
                item_id=proj_id,
                entity=p_title,
                attribute="description",
                topics=proj.get("technologies", [])
            )

            # Technologies
            for tech in proj.get("technologies", []):
                if tech and len(tech.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Utilized {tech.strip()} in {p_title}",
                        item_id=proj_id,
                        entity=tech.strip(),
                        attribute="technology",
                        topics=[tech.strip()]
                    )

            # Components & Services
            for comp in proj.get("components_services", []):
                if comp and len(comp.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Engineered component {comp.strip()} in {p_title}",
                        item_id=proj_id,
                        entity=comp.strip(),
                        attribute="component",
                        topics=[comp.strip()]
                    )

            # Architecture claims
            for arch in proj.get("architecture_claims", []):
                if arch and len(arch.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Architectural claim in {p_title}: {arch.strip()}",
                        item_id=proj_id,
                        entity=p_title,
                        attribute="architecture",
                        topics=[p_title]
                    )

            # Metrics
            for metric in proj.get("metrics", []):
                if metric and len(metric.strip()) > 1:
                    state.register_resume_claim(
                        statement=f"Achieved metric in {p_title}: {metric.strip()}",
                        item_id=proj_id,
                        entity=p_title,
                        attribute="metric",
                        topics=[p_title]
                    )

            # Specific contributions / responsibilities
            for resp in proj.get("responsibilities", []):
                if resp and len(resp.strip()) > 3:
                    state.register_resume_claim(
                        statement=f"Contribution in {p_title}: {resp.strip()}",
                        item_id=proj_id,
                        entity=p_title,
                        attribute="responsibility",
                        topics=[p_title]
                    )

    @classmethod
    def _extract_work_experience(cls, text: str, target_role: str) -> List[Dict[str, Any]]:
        """
        Extracts work experience entries without inventing fake companies or metrics.
        Returns [] if no experience entries exist.
        """
        if not text or len(text.strip()) < 20:
            return []

        exp_section_text = cls._extract_section_text(text, ["experience", "work experience", "employment", "professional experience"])
        source_text = exp_section_text if exp_section_text else text

        entries: List[Dict[str, Any]] = []
        lines = [line.strip() for line in source_text.split("\n") if line.strip()]
        current_entry: Optional[Dict[str, Any]] = None

        role_indicators = r"(engineer|developer|architect|lead|manager|intern|consultant|specialist|analyst|sde)"
        date_pattern = r"(20\d\d|19\d\d|present|current|ongoing|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
        project_indicators = r"\b(project|research|capstone|thesis|hackathon)\b"

        for idx, line in enumerate(lines):
            # Skip lines that are explicitly projects/research
            if re.search(project_indicators, line, re.I):
                continue

            has_role = bool(re.search(role_indicators, line, re.I))
            has_delim = bool(re.search(r"(\s+at\s+|\s+@\s+|\s+[|–—―-]\s+)", line))
            has_date_curr = bool(re.search(date_pattern, line, re.I))

            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            has_date_next = bool(re.search(date_pattern, next_line, re.I)) and not bool(re.search(role_indicators, next_line, re.I))

            if has_role and (has_delim or has_date_curr or has_date_next):
                if current_entry:
                    cls._finalize_work_entry(current_entry, target_role, len(entries))
                    entries.append(current_entry)

                comp = "Engineering Team"
                role_title = "Software Engineer"
                duration = "Timeline"

                if " at " in line:
                    parts = re.split(r"\s+at\s+", line, maxsplit=1)
                    role_title = parts[0].strip()
                    comp = re.split(r"[\(|–—―-]", parts[1])[0].strip()
                elif " | " in line:
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        comp = parts[0].strip()
                        role_title = parts[1].strip()
                    if len(parts) >= 3:
                        duration = parts[2].strip()
                elif re.search(r"\s+[–—―-]\s+", line):
                    parts = re.split(r"\s+[–—―-]\s+", line, maxsplit=1)
                    if re.search(role_indicators, parts[0], re.I):
                        role_title = parts[0].strip()
                        comp = parts[1].split("(")[0].strip()
                    else:
                        comp = parts[0].strip()
                        role_title = parts[1].split("(")[0].strip()
                else:
                    role_match = re.search(role_indicators, line, re.I)
                    if role_match:
                        role_title = line[:role_match.end()].strip()
                        comp = line[role_match.end():].strip().lstrip("-–—―|@ ")

                date_match = re.search(r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4}\s*[-–—―]\s*(?:present|current|ongoing|\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*\d{4}))", line, re.I)
                if not date_match and has_date_next:
                    date_match = re.search(r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\s*\d{4}\s*[-–—―]\s*(?:present|current|ongoing|\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*\d{4}))", next_line, re.I)
                    if not date_match:
                        date_match = re.search(r"(\d{4}\s*[-–—―]\s*(?:\d{4}|present|current|ongoing))", next_line, re.I)

                if date_match:
                    duration = date_match.group(1).strip()

                current_entry = {
                    "company": comp or "Company",
                    "role": role_title or "Software Engineer",
                    "duration": duration,
                    "summary_lines": [],
                    "responsibilities": [],
                    "technologies": [],
                    "components_services": [],
                    "architecture_claims": [],
                    "metrics": [],
                    "ownership_claims": [],
                    "achievements": [],
                    "key_skills": []
                }
            elif current_entry:
                # If this line is just the date line that was consumed, skip adding it as a summary bullet
                if re.search(date_pattern, line, re.I) and len(line) < 30 and not re.search(r"[a-z]{5,}", line, re.I):
                    continue
                # Add line to current entry
                cleaned_line = line.lstrip("•*-●▪▫ ").strip()
                if cleaned_line and len(cleaned_line) > 2:
                    current_entry["summary_lines"].append(cleaned_line)
                    cls._extract_line_entities(cleaned_line, current_entry)

        if current_entry:
            cls._finalize_work_entry(current_entry, target_role, len(entries))
            entries.append(current_entry)

        return entries

    @classmethod
    def _finalize_work_entry(cls, entry: Dict[str, Any], target_role: str, index: int) -> None:
        summary_text = " ".join(entry.pop("summary_lines", []))
        entry["summary"] = summary_text if summary_text else f"Experience at {entry['company']}."
        entry["id"] = generate_stable_id("exp", entry["company"], index)

        # Extract technologies present in summary
        found_tech = cls._extract_skills(summary_text)
        entry["technologies"] = list(set(entry["technologies"] + found_tech))
        entry["key_skills"] = list(set(entry["key_skills"] + found_tech[:5]))

        # Calculate semantic relevance
        combined_text = f"{entry['role']} {entry['summary']} {' '.join(entry['technologies'])}"
        entry["overall_relevance"] = cls._calculate_semantic_relevance(combined_text, target_role)

    @classmethod
    def _extract_projects(cls, text: str, target_role: str) -> List[Dict[str, Any]]:
        """
        Extracts projects from resume text without injecting fake sample projects.
        Extracts from:
        1. Explicit 'PROJECTS' section if present.
        2. Items within 'EXPERIENCE' or general text labeled as projects/research or non-employment systems.
        Returns [] if no projects exist in the resume.
        """
        if not text or len(text.strip()) < 20:
            return []

        projects: List[Dict[str, Any]] = []
        seen_titles = set()

        def process_lines_for_projects(lines: List[str]):
            current_proj: Optional[Dict[str, Any]] = None
            date_pattern = r"(20\d\d|19\d\d|present|current|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"

            for idx, line in enumerate(lines):
                is_new_proj = False
                title = ""

                # Pattern 1: Explicit project prefix
                if line.lower().startswith("project:") or line.lower().startswith("project -"):
                    is_new_proj = True
                    title = line.split(":", 1)[-1].split("-", 1)[-1].strip()
                # Pattern 2: Delimited with Project or Research indicator
                elif re.search(r"\s+[–—―-]\s+", line) and re.search(r"\b(project|research|capstone|system|chatbot|pipeline|platform|engine|app)\b", line, re.I):
                    is_new_proj = True
                    title = re.split(r"\s+[–—―-]\s+", line, maxsplit=1)[0].strip()
                # Pattern 3: Delimited with pipe
                elif " | " in line and ("http" not in line) and not re.search(r"(20\d\d|19\d\d)", line):
                    is_new_proj = True
                    parts = line.split(" | ")
                    title = parts[0].strip()
                # Pattern 4: Markdown header or uppercase title
                elif (line.startswith("##") or (line.isupper() and len(line) > 3)) and len(line) < 60 and not re.search(r"(skills|education|certifications|experience|summary|awards|coursework)", line, re.I):
                    is_new_proj = True
                    title = line.lstrip("#").strip()

                if is_new_proj and title and len(title) > 2:
                    clean_title = re.sub(r"^[0-9\.\-\s]+", "", title).strip()
                    title_key = clean_title.lower()
                    if title_key in seen_titles:
                        continue
                    seen_titles.add(title_key)

                    if current_proj:
                        cls._finalize_proj_entry(current_proj, target_role, len(projects))
                        projects.append(current_proj)

                    current_proj = {
                        "title": clean_title,
                        "desc_lines": [],
                        "technologies": [],
                        "components_services": [],
                        "architecture_claims": [],
                        "metrics": [],
                        "ownership_claims": [],
                        "responsibilities": [],
                        "relevant_topics": [],
                        "irrelevant_topics": []
                    }
                elif current_proj:
                    # Skip date-only line
                    if re.search(date_pattern, line, re.I) and len(line) < 30 and not re.search(r"[a-z]{5,}", line, re.I):
                        continue
                    cleaned_line = line.lstrip("•*-●▪▫ ").strip()
                    if cleaned_line and len(cleaned_line) > 2:
                        current_proj["desc_lines"].append(cleaned_line)
                        cls._extract_line_entities(cleaned_line, current_proj)

            if current_proj:
                cls._finalize_proj_entry(current_proj, target_role, len(projects))
                projects.append(current_proj)

        # 1. First extract from dedicated projects section if present
        proj_section_text = cls._extract_section_text(text, ["projects", "personal projects", "technical projects", "academic projects"])
        if proj_section_text:
            lines = [line.strip() for line in proj_section_text.split("\n") if line.strip()]
            process_lines_for_projects(lines)

        # 2. Also scan experience section for project/research items
        exp_section_text = cls._extract_section_text(text, ["experience", "work experience", "employment", "professional experience"])
        source_for_projects = exp_section_text if exp_section_text else text
        exp_lines = [line.strip() for line in source_for_projects.split("\n") if line.strip()]
        process_lines_for_projects(exp_lines)

        return projects

    @classmethod
    def _finalize_proj_entry(cls, proj: Dict[str, Any], target_role: str, index: int) -> None:
        desc_text = " ".join(proj.pop("desc_lines", []))
        proj["description"] = desc_text if desc_text else f"Technical project: {proj['title']}."
        proj["project_id"] = generate_stable_id("proj", proj["title"], index)

        # Extract technologies present in description
        found_tech = cls._extract_skills(desc_text)
        proj["technologies"] = list(set(proj["technologies"] + found_tech))

        # Infer relevant topics
        topics = [proj["title"]]
        if found_tech:
            topics.extend(found_tech[:3])
        proj["relevant_topics"] = list(set(proj["relevant_topics"] + topics))

        # Calculate semantic relevance
        combined_text = f"{proj['title']} {proj['description']} {' '.join(proj['technologies'])}"
        proj["overall_relevance"] = cls._calculate_semantic_relevance(combined_text, target_role)

    @classmethod
    def _extract_line_entities(cls, line: str, target_dict: Dict[str, Any]) -> None:
        """
        Extracts metrics, architectural assertions, and ownership claims from a bullet point.
        """
        target_dict.setdefault("metrics", [])
        target_dict.setdefault("ownership_claims", [])
        target_dict.setdefault("responsibilities", [])
        target_dict.setdefault("architecture_claims", [])
        target_dict.setdefault("components_services", [])

        # Metrics: throughput, latency, numbers, percentages
        metric_matches = re.findall(r"(\d+(?:\.\d+)?\s*(?:k|m|ms|s|req/sec|writes/sec|rps|qps|tps|users|%|percent))", line, re.I)
        for m in metric_matches:
            if m not in target_dict["metrics"]:
                target_dict["metrics"].append(m)

        # Ownership statements
        if re.search(r"\b(architected|designed|spearheaded|led|owned|built|implemented|created)\b", line, re.I):
            target_dict["ownership_claims"].append(line)
            target_dict["responsibilities"].append(line)

        # Architectural assertions
        if re.search(r"\b(microservices?|distributed|caching|raft|paxos|cqrs|event-driven|sharding|replication|partition|pipeline)\b", line, re.I):
            target_dict["architecture_claims"].append(line)

        # Service / component mentions
        service_matches = re.findall(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?\s+(?:Service|API|Cluster|Queue|Database|Store|Pipeline))\b", line)
        for sm in service_matches:
            if sm not in target_dict["components_services"]:
                target_dict["components_services"].append(sm)

    @classmethod
    def _extract_skills(cls, text: str) -> List[str]:
        """
        Extracts only technical skills that literally appear in the resume text.
        Returns [] if no known tech terms exist in the input.
        """
        if not text:
            return []

        standard_skills = [
            "Python", "FastAPI", "Django", "Flask", "Go", "Golang", "Java", "Spring Boot",
            "C++", "C#", ".NET", "Rust", "TypeScript", "JavaScript", "React", "Next.js",
            "Vue", "Angular", "Node.js", "PostgreSQL", "MySQL", "SQLite", "MongoDB",
            "Redis", "Kafka", "RabbitMQ", "Elasticsearch", "Docker", "Kubernetes",
            "AWS", "GCP", "Azure", "Terraform", "GraphQL", "gRPC", "REST API",
            "Microservices", "Git", "Linux", "CI/CD", "Prometheus", "Grafana"
        ]

        text_lower = f" {text.lower()} "
        found = []
        for s in standard_skills:
            # Word boundary check
            pattern = rf"\b{re.escape(s.lower())}\b"
            if re.search(pattern, text_lower):
                found.append(s)
        return found

    @classmethod
    def _extract_education(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extracts education entries if present in text; returns [] otherwise.
        """
        edu_text = cls._extract_section_text(text, ["education", "academic background", "academics", "university"])
        if not edu_text:
            return []

        lines = [line.strip() for line in edu_text.split("\n") if line.strip()]
        edu_list = []
        for line in lines:
            if re.search(r"\b(bachelor|master|phd|b\.tech|m\.tech|b\.s|m\.s|degree|university|college|institute)\b", line, re.I):
                edu_list.append({
                    "degree": line,
                    "institution": "University/Institution",
                    "grad_year": re.search(r"(20\d\d|19\d\d)", line).group(0) if re.search(r"(20\d\d|19\d\d)", line) else ""
                })
        return edu_list

    @classmethod
    def _extract_certifications(cls, text: str) -> List[str]:
        """
        Extracts actual certifications if present in text; returns [] otherwise.
        """
        cert_text = cls._extract_section_text(text, ["certifications", "certificates", "licenses"])
        if not cert_text:
            return []
        lines = [line.lstrip("•*- ").strip() for line in cert_text.split("\n") if line.strip()]
        return [l for l in lines if len(l) > 3 and not re.search(r"(certifications|certificates)", l, re.I)]

    @classmethod
    def _extract_achievements(cls, text: str) -> List[str]:
        """
        Extracts actual achievements if present in text; returns [] otherwise.
        """
        ach_text = cls._extract_section_text(text, ["achievements", "honors", "awards"])
        if not ach_text:
            return []
        lines = [line.lstrip("•*- ").strip() for line in ach_text.split("\n") if line.strip()]
        return [l for l in lines if len(l) > 3 and not re.search(r"(achievements|honors|awards)", l, re.I)]

    @classmethod
    def _extract_extracurricular(cls, text: str) -> List[str]:
        """
        Extracts actual extracurriculars if present in text; returns [] otherwise.
        """
        extra_text = cls._extract_section_text(text, ["extracurricular", "volunteer", "activities", "leadership"])
        if not extra_text:
            return []
        lines = [line.lstrip("•*- ").strip() for line in extra_text.split("\n") if line.strip()]
        return [l for l in lines if len(l) > 3 and not re.search(r"(extracurricular|activities)", l, re.I)]

    KNOWN_SECTION_HEADERS = [
        "summary", "about", "profile", "objective",
        "experience", "work experience", "employment", "professional experience",
        "projects", "personal projects", "technical projects", "academic projects",
        "skills", "technical skills", "core competencies",
        "education", "academic background", "academics",
        "certifications", "certificates", "licenses",
        "achievements", "honors", "awards",
        "extracurricular", "activities", "leadership", "volunteer"
    ]

    @classmethod
    def _extract_section_text(cls, text: str, header_keywords: List[str]) -> Optional[str]:
        """
        Finds the subsection of text following one of the header keywords up to the next major heading.
        """
        pattern = rf"(?:^|\n)\s*(?:#*\s*)?({'|'.join(re.escape(k) for k in header_keywords)})\s*[:\n]"
        match = re.search(pattern, text, re.I)
        if not match:
            return None

        start_idx = match.end()
        # Find next section header from other known sections or end of string
        curr_keywords_lower = [k.lower() for k in header_keywords]
        other_headers = [h for h in cls.KNOWN_SECTION_HEADERS if h.lower() not in curr_keywords_lower]
        next_pattern = rf"(?:^|\n)\s*(?:#*\s*)?(?:{'|'.join(re.escape(h) for h in other_headers)})\s*[:\n]"
        next_match = re.search(next_pattern, text[start_idx:], re.I)
        if next_match:
            return text[start_idx:start_idx + next_match.start()].strip()

        # Fallback to markdown header boundary like `\n## ` or `\n# `
        md_match = re.search(r"(?:^|\n)\s*#{1,3}\s+[A-Z]", text[start_idx:])
        if md_match:
            return text[start_idx:start_idx + md_match.start()].strip()

        return text[start_idx:].strip()

    @classmethod
    def _calculate_semantic_relevance(cls, text: str, target_role: str) -> float:
        """
        Computes actual semantic relevance of an experience/project to the target role.
        Never fabricates arbitrary descending index values.
        """
        if not text or not target_role:
            return 0.70

        text_lower = text.lower()
        role_lower = target_role.lower()

        # Keywords associated with major software domains
        role_keywords = {
            "backend": ["api", "database", "sql", "postgresql", "redis", "kafka", "rest", "grpc", "microservice", "server", "concurrency"],
            "distributed": ["raft", "consensus", "cluster", "replication", "partition", "sharding", "throughput", "latency", "node", "fault"],
            "frontend": ["react", "typescript", "javascript", "ui", "ux", "dom", "css", "state", "redux", "canvas", "rendering"],
            "full stack": ["react", "node", "api", "database", "backend", "frontend", "typescript", "sql"],
            "systems": ["c++", "go", "rust", "memory", "thread", "concurrency", "socket", "network", "linux", "kernel", "buffer"]
        }

        # Identify target domain keywords
        target_words = set(role_lower.split())
        for domain, kw_list in role_keywords.items():
            if domain in role_lower:
                target_words.update(kw_list)

        if not target_words:
            target_words = {"software", "engineer", "code", "architecture", "system", "design", "development"}

        # Count match hits
        hits = sum(1 for w in target_words if w in text_lower)
        overlap_ratio = hits / max(1, min(len(target_words), 8))

        # Scale into realistic relevance band [0.55, 0.96]
        computed = 0.55 + (0.41 * min(1.0, overlap_ratio))
        return round(computed, 2)
