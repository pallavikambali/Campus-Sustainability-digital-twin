from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import SimulationResponse
from app.services import (
    Scenario,
    UnsupportedZoneError,
    ZoneNotFoundError,
    reset_zone,
    simulate,
)

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


def _run(
    zone_id: UUID,
    session: Session,
    action: Callable[[Session, UUID], SimulationResponse],
) -> SimulationResponse:
    try:
        with session.begin():
            return action(session, zone_id)
    except ZoneNotFoundError as error:
        raise HTTPException(status_code=404, detail="Zone not found") from error
    except UnsupportedZoneError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _run_scenario(
    zone_id: UUID, scenario: Scenario, session: Session
) -> SimulationResponse:
    return _run(
        zone_id,
        session,
        lambda current_session, current_zone_id: simulate(
            current_session, current_zone_id, scenario
        ),
    )


@router.post("/{zone_id}/energy-spike", response_model=SimulationResponse)
def simulate_energy_spike(
    zone_id: UUID, session: Session = Depends(get_session)
) -> SimulationResponse:
    return _run_scenario(zone_id, "energy-spike", session)


@router.post("/{zone_id}/water-leak", response_model=SimulationResponse)
def simulate_water_leak(
    zone_id: UUID, session: Session = Depends(get_session)
) -> SimulationResponse:
    return _run_scenario(zone_id, "water-leak", session)


@router.post("/{zone_id}/occupancy-surge", response_model=SimulationResponse)
def simulate_occupancy_surge(
    zone_id: UUID, session: Session = Depends(get_session)
) -> SimulationResponse:
    return _run_scenario(zone_id, "occupancy-surge", session)


@router.post("/{zone_id}/reset", response_model=SimulationResponse)
def reset_simulation(
    zone_id: UUID, session: Session = Depends(get_session)
) -> SimulationResponse:
    return _run(zone_id, session, reset_zone)