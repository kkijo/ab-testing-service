from scipy.stats import norm
import math

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import engine, Base, get_db
import hashlib
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="A/B Testing Service")

def _calculate_z_test(
    control_conversions: int,
    control_total: int,
    treatment_conversions: int,
    treatment_total: int,
):
    """Z-тест для двух долей. Возвращает (z_stat, p_value) или (None, None)."""
    if control_total == 0 or treatment_total == 0:
        return None, None

    p1 = control_conversions / control_total
    p2 = treatment_conversions / treatment_total

    p_pool = (control_conversions + treatment_conversions) / (control_total + treatment_total)

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / control_total + 1 / treatment_total))
    if se == 0:
        return None, None

    z = (p2 - p1) / se

    p_value = 2 * (1 - norm.cdf(abs(z)))

    return float(z), float(p_value)


def _get_hash_fraction(user_id: str) -> float:
    hash_bytes = hashlib.md5(user_id.encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:8], byteorder="big")
    return hash_int / (2**64)


def _pick_variant(variants, hash_value: float):
    cumulative = 0.0
    for v in variants:
        cumulative += v.weight
        if hash_value < cumulative:
            return v
    return variants[-1]

@app.get("/")
def root():
    return {"message": "A/B Testing Service is running"}


@app.post(
    "/experiments",
    response_model=schemas.ExperimentResponse,
    status_code=201,
)
def create_experiment(
    experiment: schemas.ExperimentCreate,
    db: Session = Depends(get_db),
):
    db_exp = models.Experiment(
        name=experiment.name,
        description=experiment.description,
    )
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)
    return db_exp


@app.get("/experiments", response_model=list[schemas.ExperimentResponse])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(models.Experiment).all()


@app.get(
    "/experiments/{experiment_id}",
    response_model=schemas.ExperimentResponse,
)
def get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    exp = (
        db.query(models.Experiment)
        .filter(models.Experiment.id == experiment_id)
        .first()
    )
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@app.post(
    "/experiments/{experiment_id}/variants",
    response_model=schemas.VariantResponse,
    status_code=201,
)
def create_variant(
    experiment_id: int,
    variant: schemas.VariantCreate,
    db: Session = Depends(get_db),
):
    exp = (
        db.query(models.Experiment)
        .filter(models.Experiment.id == experiment_id)
        .first()
    )
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    db_variant = models.Variant(
        experiment_id=experiment_id,
        name=variant.name,
        weight=variant.weight,
        is_control=variant.is_control,
    )
    db.add(db_variant)
    db.commit()
    db.refresh(db_variant)
    return db_variant

@app.post("/assign", response_model=schemas.AssignResponse)
def assign_user(
    request: schemas.AssignRequest,
    db: Session = Depends(get_db),
):
    exp = db.query(models.Experiment).filter(
        models.Experiment.id == request.experiment_id
    ).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    existing = db.query(models.Assignment).filter(
        models.Assignment.experiment_id == request.experiment_id,
        models.Assignment.user_id == request.user_id,
    ).first()
    if existing:
        variant = db.query(models.Variant).filter(
            models.Variant.id == existing.variant_id
        ).first()
        return schemas.AssignResponse(
            experiment_id=request.experiment_id,
            user_id=request.user_id,
            variant_id=variant.id,
            variant_name=variant.name,
        )

    variants = db.query(models.Variant).filter(
        models.Variant.experiment_id == request.experiment_id
    ).all()
    if not variants:
        raise HTTPException(status_code=400, detail="Experiment has no variants")

    hash_value = _get_hash_fraction(request.user_id)
    chosen = _pick_variant(variants, hash_value)

    db_assignment = models.Assignment(
        experiment_id=request.experiment_id,
        variant_id=chosen.id,
        user_id=request.user_id,
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)

    return schemas.AssignResponse(
        experiment_id=request.experiment_id,
        user_id=request.user_id,
        variant_id=chosen.id,
        variant_name=chosen.name,
    )


@app.post(
    "/events",
    response_model=schemas.EventResponse,
    status_code=201,
)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
):
    exp = db.query(models.Experiment).filter(
        models.Experiment.id == event.experiment_id
    ).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    assignment = db.query(models.Assignment).filter(
        models.Assignment.experiment_id == event.experiment_id,
        models.Assignment.user_id == event.user_id,
    ).first()
    if assignment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not assigned to this experiment",
        )

    db_event = models.Event(
        experiment_id=event.experiment_id,
        variant_id=assignment.variant_id,
        user_id=event.user_id,
        event_type=event.event_type,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event




@app.get(
    "/experiments/{experiment_id}/stats",
    response_model=schemas.StatsResponse,
)
def get_experiment_stats(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    exp = db.query(models.Experiment).filter(
        models.Experiment.id == experiment_id
    ).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    variants = db.query(models.Variant).filter(
        models.Variant.experiment_id == experiment_id
    ).all()
    if not variants:
        raise HTTPException(status_code=400, detail="Experiment has no variants")

    variant_stats = []
    for v in variants:
        users_count = db.query(models.Assignment).filter(
            models.Assignment.experiment_id == experiment_id,
            models.Assignment.variant_id == v.id,
        ).count()

        conversions = db.query(models.Event.user_id).filter(
            models.Event.experiment_id == experiment_id,
            models.Event.variant_id == v.id,
        ).distinct().count()

        conversion_rate = (conversions / users_count) if users_count > 0 else 0.0

        variant_stats.append(schemas.VariantStats(
            variant_id=v.id,
            variant_name=v.name,
            users_count=users_count,
            conversions=conversions,
            conversion_rate=round(conversion_rate, 4),
        ))

    control = next((v for v in variants if v.is_control), None)
    treatment = next((v for v in variants if not v.is_control), None)

    z_stat = p_value = lift = None
    is_significant = None

    if control and treatment:
        control_stats = next(s for s in variant_stats if s.variant_id == control.id)
        treatment_stats = next(s for s in variant_stats if s.variant_id == treatment.id)

        z_stat, p_value = _calculate_z_test(
            control_conversions=control_stats.conversions,
            control_total=control_stats.users_count,
            treatment_conversions=treatment_stats.conversions,
            treatment_total=treatment_stats.users_count,
        )

        if p_value is not None:
            is_significant = p_value < 0.05
            if control_stats.conversion_rate > 0:
                lift = round(
                    (treatment_stats.conversion_rate - control_stats.conversion_rate)
                    / control_stats.conversion_rate,
                    4,
                )

    return schemas.StatsResponse(
        experiment_id=experiment_id,
        variants=variant_stats,
        z_statistic=round(z_stat, 4) if z_stat is not None else None,
        p_value=round(p_value, 6) if p_value is not None else None,
        is_significant=is_significant,
        lift=lift,
    )