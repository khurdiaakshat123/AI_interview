from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models.models import RoleTopicProfile, TimeWindow, generate_uuid, utc_now
from backend.app.schemas.schemas import RoleTopicProfileCreate, RoleTopicProfileOut
from backend.app.agents.role_profile_agent import RoleProfileAgent
from backend.app.agents.mock_oa_agent import MockOAAgent

router = APIRouter(prefix="/api/role-profiles", tags=["Role Profiles"])

@router.post("", response_model=RoleTopicProfileOut)
def create_role_profile(payload: RoleTopicProfileCreate, db: Session = Depends(get_db)):
    company = payload.company.strip().title()
    role = payload.role.strip().title()

    # Get active window
    window = MockOAAgent.get_or_create_active_window(db, company, role)

    # Check existing profile
    existing = db.query(RoleTopicProfile).filter(
        RoleTopicProfile.company == company,
        RoleTopicProfile.role == role
    ).first()

    if existing:
        return RoleTopicProfileOut(
            id=existing.id,
            company=existing.company,
            role=existing.role,
            job_type=existing.job_type,
            experience_requirement=existing.experience_requirement,
            required_skills=existing.required_skills or [],
            time_window_id=existing.time_window_id,
            subjects=existing.subjects_json or [],
            evidence=existing.evidence_json or [],
            created_at=existing.created_at,
            refreshed_at=existing.refreshed_at
        )

    # Generate via Agent 1
    gen_data = RoleProfileAgent.generate_profile(
        company=company,
        role=role,
        job_type=payload.job_type or "Full-Time",
        experience_requirement=payload.experience_requirement or "1-3 years",
        jd_text=payload.jd_text or ""
    )

    profile = RoleTopicProfile(
        id=generate_uuid(),
        company=company,
        role=role,
        job_type=gen_data["job_type"],
        experience_requirement=gen_data["experience_requirement"],
        required_skills=gen_data["required_skills"],
        time_window_id=window.id,
        subjects_json=gen_data["subjects"],
        evidence_json=gen_data["evidence"],
        created_at=utc_now(),
        refreshed_at=utc_now()
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return RoleTopicProfileOut(
        id=profile.id,
        company=profile.company,
        role=profile.role,
        job_type=profile.job_type,
        experience_requirement=profile.experience_requirement,
        required_skills=profile.required_skills or [],
        time_window_id=profile.time_window_id,
        subjects=profile.subjects_json or [],
        evidence=profile.evidence_json or [],
        created_at=profile.created_at,
        refreshed_at=profile.refreshed_at
    )

@router.get("", response_model=List[RoleTopicProfileOut])
def list_role_profiles(db: Session = Depends(get_db)):
    profiles = db.query(RoleTopicProfile).all()
    results = []
    for p in profiles:
        results.append(RoleTopicProfileOut(
            id=p.id,
            company=p.company,
            role=p.role,
            job_type=p.job_type,
            experience_requirement=p.experience_requirement,
            required_skills=p.required_skills or [],
            time_window_id=p.time_window_id,
            subjects=p.subjects_json or [],
            evidence=p.evidence_json or [],
            created_at=p.created_at,
            refreshed_at=p.refreshed_at
        ))
    return results

@router.get("/{id}", response_model=RoleTopicProfileOut)
def get_role_profile(id: str, db: Session = Depends(get_db)):
    profile = db.query(RoleTopicProfile).filter(RoleTopicProfile.id == id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Role Topic Profile not found")

    return RoleTopicProfileOut(
        id=profile.id,
        company=profile.company,
        role=profile.role,
        job_type=profile.job_type,
        experience_requirement=profile.experience_requirement,
        required_skills=profile.required_skills or [],
        time_window_id=profile.time_window_id,
        subjects=profile.subjects_json or [],
        evidence=profile.evidence_json or [],
        created_at=profile.created_at,
        refreshed_at=profile.refreshed_at
    )
