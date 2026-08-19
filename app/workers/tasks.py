from __future__ import annotations

import logging
from typing import Optional

from app.db.base import get_session
from app.dedup.engine import DedupEngine, is_mobile_number
from app.enrichment.service import EnrichmentService
from app.scoring.engine import apply_score
from app.scraper.base import PHASE_1_ICP_QUERIES
from app.scraper.factory import get_provider
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.run_scrape_pipeline", bind=True, max_retries=2)
def run_scrape_pipeline(
    self,
    city: str,
    queries: Optional[list[str]] = None,
    max_results_per_query: int = 60,
    provider: Optional[str] = None,
    area: Optional[str] = None,
) -> dict:
    """
    Full pipeline for one city (optionally narrowed to one area/locality
    within it, e.g. "Bandra West" within "Mumbai"): scrape -> dedup ->
    enrich -> score -> save. Runs as a Celery task so it can be triggered
    from the API or on the nightly beat schedule without blocking a web
    request.
    """
    queries = queries or PHASE_1_ICP_QUERIES
    scraper = get_provider(provider)

    created_count = 0
    updated_count = 0
    total_seen = 0
    newly_created_prospects: list[Prospect] = []

    with get_session() as session:
        dedup = DedupEngine(session)
        enrichment = EnrichmentService()

        try:
            for query in queries:
                try:
                    leads = scraper.search(query, city, max_results_per_query, area=area)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Scrape failed for query=%r city=%r area=%r", query, city, area
                    )
                    continue

                total_seen += len(leads)

                for lead in leads:
                    try:
                        prospect, created = dedup.upsert(lead)
                        if created:
                            created_count += 1
                            newly_created_prospects.append(prospect)
                        else:
                            updated_count += 1

                        try:
                            enrichment.enrich(prospect)
                        except Exception:  # noqa: BLE001
                            logger.exception("Enrichment failed for %s", prospect.business_name)

                        if not prospect.whatsapp and is_mobile_number(prospect.phone):
                            prospect.whatsapp = prospect.phone
                            prospect.whatsapp_source = "inferred"

                        apply_score(prospect)
                        session.commit()
                    except Exception:  # noqa: BLE001
                        session.rollback()
                        logger.exception("Failed to process lead %s, rolled back session", lead.business_name)
        finally:
            enrichment.close()

        # If new prospects were created, append them to the canonical Supabase Storage workbook
        if newly_created_prospects:
            try:
                from app.storage.excel_storage import sync_prospects_to_storage_workbook

                sync_prospects_to_storage_workbook(newly_created_prospects)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to sync newly created prospects to canonical workbook")

    result = {
        "city": city,
        "area": area,
        "queries": queries,
        "total_seen": total_seen,
        "created": created_count,
        "updated": updated_count,
    }
    logger.info("run_scrape_pipeline finished: %s", result)
    return result


@celery_app.task(name="app.workers.tasks.export_prospects_to_excel")
def export_prospects_to_excel() -> dict:
    """
    Sync newly discovered prospects to the canonical caller workbook stored
    in Supabase Storage. Existing rows and caller edits are strictly preserved.
    """
    from app.storage.excel_storage import sync_prospects_to_storage_workbook

    result = sync_prospects_to_storage_workbook()
    logger.info("export_prospects_to_excel completed: %s", result)
    return result


@celery_app.task(name="app.workers.tasks.run_nightly_region_scrape")
def run_nightly_region_scrape(region_key: str) -> dict:
    """
    Automated nightly scheduled batch task. Scrapes all micro-market target
    localities defined for `region_key` ('delhi_ncr', 'mumbai', 'bangalore')
    during the 8:00 PM - 6:00 AM IST window.
    """
    from app.scraper.base import NIGHTLY_SCHEDULE_TARGETS

    targets = NIGHTLY_SCHEDULE_TARGETS.get(region_key, [])
    if not targets:
        logger.warning("No targets found for region_key=%r", region_key)
        return {"region": region_key, "processed": 0}

    total_created = 0
    total_updated = 0

    for target in targets:
        city = target["city"]
        area = target.get("area")
        try:
            res = run_scrape_pipeline(
                city=city,
                area=area,
                max_results_per_query=40,
            )
            total_created += res.get("created", 0)
            total_updated += res.get("updated", 0)
        except Exception:  # noqa: BLE001
            logger.exception("Nightly batch failed for city=%r area=%r", city, area)

    # Incrementally update canonical caller workbook in Supabase Storage
    export_prospects_to_excel()

    result = {
        "region": region_key,
        "targets_count": len(targets),
        "total_created": total_created,
        "total_updated": total_updated,
    }
    logger.info("run_nightly_region_scrape finished: %s", result)
    return result

