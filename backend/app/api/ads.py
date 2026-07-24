"""Ads API — serves data from Supabase."""
from fastapi import APIRouter, Query
from app.core.supabase import get_supabase

router = APIRouter(prefix="/api/ads", tags=["ads"])

PAGE_SIZE = 24

AD_FIELDS = (
    "ad_url, title, price_eur, price_mkd, currency, location, "
    "images, category, condition, source, scraped_at, posted_date, "
    "seller_name, seller_type, specs, delivery_available, description, seller_notes, "
    "is_anomaly, price_zscore, anomaly_reason, cluster_id, cluster_label, ad_type"
)


@router.get("")
def list_ads(
    source: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    q: str | None = None,
    sort: str = "newest",
    anomaly_only: bool = False,
    ad_type: str | None = None,
    page: int = Query(1, ge=1),
):
    sb = get_supabase()
    offset = (page - 1) * PAGE_SIZE

    query = sb.table("ads").select(AD_FIELDS, count="exact")

    if source:
        query = query.eq("source", source)
    if category:
        query = query.eq("category", category)
    if condition:
        query = query.eq("condition", condition)
    if min_price is not None:
        query = query.gte("price_eur", min_price)
    if max_price is not None:
        query = query.lte("price_eur", max_price)
    if q:
        query = query.ilike("title", f"%{q}%")
    if anomaly_only:
        query = query.eq("is_anomaly", True)
    if ad_type:
        query = query.eq("ad_type", ad_type)

    if sort == "price_asc":
        query = query.order("price_eur", desc=False, nulls_first=False)
    elif sort == "price_desc":
        query = query.order("price_eur", desc=True, nulls_first=False)
    else:
        query = query.order("scraped_at", desc=True)

    result = query.range(offset, offset + PAGE_SIZE - 1).execute()

    return {
        "items": result.data,
        "total": result.count or 0,
        "page": page,
        "pages": max(1, ((result.count or 0) + PAGE_SIZE - 1) // PAGE_SIZE),
    }


@router.get("/stats")
def get_stats():
    sb = get_supabase()
    total = sb.table("ads").select("ad_url", count="exact").execute().count or 0
    r5 = sb.table("ads").select("ad_url", count="exact").eq("source", "reklama5").execute().count or 0
    p3 = sb.table("ads").select("ad_url", count="exact").eq("source", "pazar3").execute().count or 0
    dupes = sb.table("duplicates").select("id", count="exact").execute().count or 0
    anomalies = sb.table("ads").select("ad_url", count="exact").eq("is_anomaly", True).execute().count or 0
    services = sb.table("ads").select("ad_url", count="exact").eq("ad_type", "service").execute().count or 0
    wanted = sb.table("ads").select("ad_url", count="exact").eq("ad_type", "wanted").execute().count or 0

    return {
        "total": total,
        "sources": {"reklama5": r5, "pazar3": p3},
        "duplicates": dupes,
        "anomalies": anomalies,
        "ad_types": {"service": services, "wanted": wanted},
    }


@router.get("/similar")
def get_similar(cluster_id: int, exclude_url: str | None = None, limit: int = 6):
    sb = get_supabase()
    q = (
        sb.table("ads")
        .select(AD_FIELDS)
        .eq("cluster_id", cluster_id)
        .eq("ad_type", "product")
        .not_.is_("images", "null")
    )
    if exclude_url:
        q = q.neq("ad_url", exclude_url)
    result = q.order("scraped_at", desc=True).limit(limit).execute()
    return result.data


@router.get("/categories")
def get_categories():
    sb = get_supabase()
    # Fetch in pages and count server-side
    cats: dict[str, int] = {}
    offset = 0
    batch = 1000
    while True:
        rows = (
            sb.table("ads")
            .select("category")
            .not_.is_("category", "null")
            .neq("category", "")
            .range(offset, offset + batch - 1)
            .execute()
            .data
        )
        if not rows:
            break
        for row in rows:
            c = row.get("category") or ""
            if c:
                cats[c] = cats.get(c, 0) + 1
        if len(rows) < batch:
            break
        offset += batch

    return sorted(
        [{"name": k, "count": v} for k, v in cats.items()],
        key=lambda x: -x["count"],
    )[:40]
